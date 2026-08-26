import { Prisma } from "@prisma/client";
import { databaseEnvKeysPresent, prisma, resolveDatabaseUrl } from "./prisma";
import type { CofRecord, GeoFeature, PrecinctStat, SearchHit } from "./types";

export function nyplImageUrl(imageId: string | null): string | null {
  if (!imageId) return null;
  return `https://images.nypl.org/index.php?id=${imageId}&t=w`;
}

/** True if any known Postgres/Prisma URL env is present. */
export function dbConfigured(): Promise<boolean> {
  return Promise.resolve(Boolean(resolveDatabaseUrl()));
}

export function dbEnvStatus() {
  return {
    configured: Boolean(resolveDatabaseUrl()),
    keysPresent: databaseEnvKeysPresent(),
  };
}

export async function getPrecinctStats(): Promise<PrecinctStat[]> {
  return prisma.$queryRaw<PrecinctStat[]>`
    SELECT precinct, precinct_num, COUNT(*)::int AS count
    FROM cof_records
    WHERE precinct IS NOT NULL
    GROUP BY precinct, precinct_num
    ORDER BY count DESC
  `;
}

export async function getMapFeatures(precinctNum?: number): Promise<GeoFeature[]> {
  const rows = await prisma.$queryRaw<GeoFeature[]>`
    SELECT r.uuid::text, r.title, r.address_norm, r.precinct, r.precinct_num,
           r.nypl_image_id, r.nypl_item_url, g.lat, g.lng, g.status AS geo_status
    FROM cof_records r
    LEFT JOIN cof_geocodes g ON r.address_norm = g.address_norm
    WHERE r.title_kind = 'address'
      AND g.lat IS NOT NULL AND g.lng IS NOT NULL
      ${precinctNum != null ? Prisma.sql`AND r.precinct_num = ${precinctNum}` : Prisma.empty}
  `;
  return rows;
}

export async function getRecord(uuid: string): Promise<CofRecord | null> {
  const rows = await prisma.$queryRaw<CofRecord[]>`
    SELECT r.uuid::text, r.title, r.address_norm, r.title_kind, r.precinct, r.precinct_num,
           r.date_start, r.date_end, r.nypl_image_id, r.nypl_item_url, r.genres, r.host_chain,
           g.lat, g.lng, g.status AS geo_status, g.geo_source,
           d.ocr_text, d.char_count, d.quality AS ocr_quality
    FROM cof_records r
    LEFT JOIN cof_geocodes g ON r.address_norm = g.address_norm
    LEFT JOIN cof_documents d ON r.uuid = d.uuid
    WHERE r.uuid = ${uuid}::uuid
    LIMIT 1
  `;
  return rows[0] || null;
}

export async function searchRecords(
  q: string,
  precinctNum?: number,
  limit = 50,
): Promise<SearchHit[]> {
  const query = q.trim();
  const lim = Math.min(limit, 200);

  if (!query) {
    return prisma.$queryRaw<SearchHit[]>`
      SELECT r.uuid::text, r.title, r.precinct, r.address_norm,
             left(coalesce(d.ocr_text, ''), 200) AS snippet
      FROM cof_records r
      LEFT JOIN cof_documents d ON r.uuid = d.uuid
      WHERE ${precinctNum != null ? Prisma.sql`r.precinct_num = ${precinctNum}` : Prisma.sql`TRUE`}
      ORDER BY r.title
      LIMIT ${lim}
    `;
  }

  const like = `%${query}%`;
  return prisma.$queryRaw<SearchHit[]>`
    SELECT r.uuid::text, r.title, r.precinct, r.address_norm,
           ts_headline('english', coalesce(d.ocr_text, r.title), plainto_tsquery('english', ${query})) AS snippet,
           ts_rank(to_tsvector('english', coalesce(d.ocr_text, r.title)), plainto_tsquery('english', ${query})) AS rank
    FROM cof_records r
    LEFT JOIN cof_documents d ON r.uuid = d.uuid
    WHERE ${precinctNum != null ? Prisma.sql`r.precinct_num = ${precinctNum} AND` : Prisma.empty}
      (
        to_tsvector('english', coalesce(d.ocr_text, r.title)) @@ plainto_tsquery('english', ${query})
        OR r.title ILIKE ${like}
      )
    ORDER BY rank DESC NULLS LAST, r.title
    LIMIT ${lim}
  `;
}

export async function getStats() {
  const [records, geocoded, withOcr, termRows] = await Promise.all([
    prisma.cofRecord.count(),
    prisma.cofGeocode.count({ where: { status: "ok" } }),
    prisma.cofDocument.count({ where: { charCount: { gt: 0 } } }),
    prisma.cofTerm.count(),
  ]);
  return { records, geocoded, with_ocr: withOcr, term_rows: termRows };
}
