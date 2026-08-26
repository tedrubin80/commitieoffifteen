import Link from "next/link";
import { dbConfigured, dbEnvStatus, getStats } from "@/lib/db";

export default async function HomePage() {
  const configured = await dbConfigured();
  const envStatus = dbEnvStatus();
  let stats: Record<string, number> | null = null;
  let dbError: string | null = null;

  if (configured) {
    try {
      stats = (await getStats()) as Record<string, number>;
    } catch (e) {
      dbError = e instanceof Error ? e.message : String(e);
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
        <div className="muted">
          {!configured ? (
            <p>
              No database URL in this deployment. Set{" "}
              <code>DATABASE_URL</code> or <code>POSTGRES_PRISMA_URL</code> on the Vercel project
              (Production), then redeploy.
            </p>
          ) : (
            <p>
              Database URL is set, but the query failed — usually empty schema (run migrate/seed)
              or a connection string mismatch.
            </p>
          )}
          {envStatus.keysPresent.length > 0 && (
            <p>
              Env keys present: <code>{envStatus.keysPresent.join(", ")}</code>
            </p>
          )}
          {dbError && (
            <pre className="ocrBox" style={{ marginTop: "1rem", maxHeight: 200 }}>
              {dbError}
            </pre>
          )}
        </div>
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
