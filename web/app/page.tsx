import Link from "next/link";
import { dbConfigured, getStats } from "@/lib/db";

export default async function HomePage() {
  const configured = await dbConfigured();
  let stats: Record<string, number> | null = null;
  if (configured) {
    try {
      stats = (await getStats()) as Record<string, number>;
    } catch {
      stats = null;
    }
  }

  return (
    <section className="hero">
      <h1>Committee of Fifteen — NYC vice investigation records (~1900)</h1>
      <p className="lead">
        1,731 digitized affidavits from the New York Public Library, indexed by street address
        and police precinct. A data pipeline for geocoding, OCR, and text mining on a primary
        source archive nobody has used for computational work.
      </p>

      {stats ? (
        <div className="stats">
          <div className="statCard">
            <strong>{stats.records ?? 0}</strong>
            <span>Records</span>
          </div>
          <div className="statCard">
            <strong>{stats.geocoded ?? 0}</strong>
            <span>Geocoded addresses</span>
          </div>
          <div className="statCard">
            <strong>{stats.with_ocr ?? 0}</strong>
            <span>With OCR text</span>
          </div>
          <div className="statCard">
            <strong>{stats.term_rows ?? 0}</strong>
            <span>Mined term hits</span>
          </div>
        </div>
      ) : (
        <p className="muted">
          Database not connected yet — deploy to Vercel with Postgres, then run the Railway worker
          pipeline.
        </p>
      )}

      <div className="actions">
        <Link href="/map" className="button">
          Open map
        </Link>
        <Link href="/search" className="button secondary">
          Search affidavits
        </Link>
        <a
          className="button secondary"
          href="https://huggingface.co/datasets/tedrubin80/committee-of-fifteen-dataset"
        >
          Dataset (HF)
        </a>
      </div>
    </section>
  );
}
