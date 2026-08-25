import Link from "next/link";
import { notFound } from "next/navigation";
import { dbConfigured, getRecord, nyplImageUrl } from "@/lib/db";

export default async function RecordPage({
  params,
}: {
  params: Promise<{ uuid: string }>;
}) {
  if (!(await dbConfigured())) {
    return (
      <section className="recordPage">
        <p>Database not configured.</p>
      </section>
    );
  }

  const { uuid } = await params;
  let record;
  try {
    record = await getRecord(uuid);
  } catch {
    notFound();
  }
  if (!record) notFound();

  const img = nyplImageUrl(record.nypl_image_id);

  return (
    <section className="recordPage">
      <div>
        <p>
          <Link href="/map">← Map</Link>
        </p>
        <h1>{record.title}</h1>
        <p className="muted">
          {record.precinct}
          {record.date_start ? ` · ${record.date_start}–${record.date_end || "?"}` : ""}
        </p>
        {record.address_norm && <p>{record.address_norm}</p>}
        {record.lat != null && record.lng != null && (
          <p className="muted">
            {record.lat.toFixed(5)}, {record.lng.toFixed(5)} ({record.geo_source || "geocoded"})
          </p>
        )}
        <p>
          <a href={record.nypl_item_url || "#"} target="_blank" rel="noreferrer">
            View on NYPL Digital Collections →
          </a>
        </p>
        {img && (
          <p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={img} alt={record.title} />
          </p>
        )}
      </div>
      <div>
        <h2>OCR text</h2>
        {record.ocr_text ? (
          <div className="ocrBox">{record.ocr_text}</div>
        ) : (
          <p className="muted">No OCR synced yet. Run worker ocr-sync after local OCR completes.</p>
        )}
      </div>
    </section>
  );
}
