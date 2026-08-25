"use client";

import Link from "next/link";
import { useState } from "react";
import type { SearchHit } from "@/lib/types";

export default function SearchPage() {
  const [q, setQ] = useState("disorderly");
  const [precinct, setPrecinct] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function runSearch(e?: React.FormEvent) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ q });
    if (precinct) params.set("precinct", precinct);
    try {
      const r = await fetch(`/api/search?${params}`);
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || r.statusText);
      setHits(data.hits || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setHits([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="searchPanel">
      <h1>Search affidavits</h1>
      <p className="muted">
        Full-text search over OCR (when synced). Try: saloon, madam, affidavit, precinct.
      </p>
      <form className="searchForm" onSubmit={runSearch}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search terms…"
        />
        <input
          value={precinct}
          onChange={(e) => setPrecinct(e.target.value)}
          placeholder="Precinct # (optional)"
          style={{ maxWidth: 160 }}
        />
        <button type="submit" className="button" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      <ul className="results">
        {hits.map((h) => (
          <li key={h.uuid}>
            <Link href={`/record/${h.uuid}`}>
              <strong>{h.title}</strong>
            </Link>
            {h.precinct && <span className="muted"> · {h.precinct}</span>}
            {h.snippet && <p className="muted">{h.snippet}</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}
