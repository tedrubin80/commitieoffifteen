import type { CofRecord, GeoFeature, PrecinctStat, SearchHit } from "./types";

export function nyplImageUrl(imageId: string | null): string | null {
  if (!imageId) return null;
  return `https://images.nypl.org/index.php?id=${imageId}&t=w`;
}

export async function dbConfigured(): Promise<boolean> {
  return Boolean(process.env.POSTGRES_URL);
}

export async function getPrecinctStats(): Promise<PrecinctStat[]> {
  const { sql } = await import("@vercel/postgres");
  const { rows } = await sql`
    SELECT precinct, precinct_num, COUNT(*)::int AS count
    FROM cof_records
    WHERE precinct IS NOT NULL
    GROUP BY precinct, precinct_num
    ORDER BY count DESC
  `;
  return rows as PrecinctStat[];
}

export async function getMapFeatures(precinctNum?: number): Promise<GeoFeature[]> {
  const { sql } = await import("@vercel/postgres");
  const { rows } = precinctNum
    ? await sql`
        SELECT r.uuid, r.title, r.address_norm, r.precinct, r.precinct_num,
               r.nypl_image_id, r.nypl_item_url, g.lat, g.lng, g.status AS geo_status
        FROM cof_records r
        LEFT JOIN cof_geocodes g ON r.address_norm = g.address_norm
        WHERE r.title_kind = 'address' AND r.precinct_num = ${precinctNum}
          AND g.lat IS NOT NULL AND g.lng IS NOT NULL
      `
    : await sql`
        SELECT r.uuid, r.title, r.address_norm, r.precinct, r.precinct_num,
               r.nypl_image_id, r.nypl_item_url, g.lat, g.lng, g.status AS geo_status
        FROM cof_records r
        LEFT JOIN cof_geocodes g ON r.address_norm = g.address_norm
        WHERE r.title_kind = 'address' AND g.lat IS NOT NULL AND g.lng IS NOT NULL
      `;
  return rows as GeoFeature[];
}

export async function getRecord(uuid: string): Promise<CofRecord | null> {
  const { sql } = await import("@vercel/postgres");
  const { rows } = await sql`
    SELECT r.*, g.lat, g.lng, g.status AS geo_status, g.geo_source,
           d.ocr_text, d.char_count, d.quality AS ocr_quality
    FROM cof_records r
    LEFT JOIN cof_geocodes g ON r.address_norm = g.address_norm
    LEFT JOIN cof_documents d ON r.uuid = d.uuid
    WHERE r.uuid = ${uuid}::uuid
    LIMIT 1
  `;
  return (rows[0] as CofRecord) || null;
}

export async function searchRecords(
  q: string,
  precinctNum?: number,
  limit = 50,
): Promise<SearchHit[]> {
  const { sql } = await import("@vercel/postgres");
  const query = q.trim();
  if (!query) {
    const { rows } = precinctNum
      ? await sql`
          SELECT r.uuid, r.title, r.precinct, r.address_norm,
                 ts_headline('english', coalesce(d.ocr_text, ''), plainto_tsquery('english', 'affidavit')) AS snippet
          FROM cof_records r
          LEFT JOIN cof_documents d ON r.uuid = d.uuid
          WHERE r.precinct_num = ${precinctNum}
          ORDER BY r.title
          LIMIT ${limit}
        `
      : await sql`
          SELECT r.uuid, r.title, r.precinct, r.address_norm,
                 left(coalesce(d.ocr_text, ''), 200) AS snippet
          FROM cof_records r
          LEFT JOIN cof_documents d ON r.uuid = d.uuid
          ORDER BY r.title
          LIMIT ${limit}
        `;
    return rows as SearchHit[];
  }

  const { rows } = precinctNum
    ? await sql`
        SELECT r.uuid, r.title, r.precinct, r.address_norm,
               ts_headline('english', coalesce(d.ocr_text, r.title), plainto_tsquery('english', ${query})) AS snippet,
               ts_rank(to_tsvector('english', coalesce(d.ocr_text, r.title)), plainto_tsquery('english', ${query})) AS rank
        FROM cof_records r
        LEFT JOIN cof_documents d ON r.uuid = d.uuid
        WHERE r.precinct_num = ${precinctNum}
          AND (
            to_tsvector('english', coalesce(d.ocr_text, r.title)) @@ plainto_tsquery('english', ${query})
            OR r.title ILIKE ${"%" + query + "%"}
          )
        ORDER BY rank DESC NULLS LAST, r.title
        LIMIT ${limit}
      `
    : await sql`
        SELECT r.uuid, r.title, r.precinct, r.address_norm,
               ts_headline('english', coalesce(d.ocr_text, r.title), plainto_tsquery('english', ${query})) AS snippet,
               ts_rank(to_tsvector('english', coalesce(d.ocr_text, r.title)), plainto_tsquery('english', ${query})) AS rank
        FROM cof_records r
        LEFT JOIN cof_documents d ON r.uuid = d.uuid
        WHERE to_tsvector('english', coalesce(d.ocr_text, r.title)) @@ plainto_tsquery('english', ${query})
           OR r.title ILIKE ${"%" + query + "%"}
        ORDER BY rank DESC NULLS LAST, r.title
        LIMIT ${limit}
      `;
  return rows as SearchHit[];
}

export async function getStats() {
  const { sql } = await import("@vercel/postgres");
  const { rows } = await sql`
    SELECT
      (SELECT COUNT(*)::int FROM cof_records) AS records,
      (SELECT COUNT(*)::int FROM cof_geocodes WHERE status = 'ok') AS geocoded,
      (SELECT COUNT(*)::int FROM cof_documents WHERE char_count > 0) AS with_ocr,
      (SELECT COUNT(*)::int FROM cof_terms) AS term_rows
  `;
  return rows[0];
}
