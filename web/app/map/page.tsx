"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import MapView from "@/components/MapView";
import type { PrecinctStat } from "@/lib/types";

export default function MapPage() {
  const router = useRouter();
  const [precincts, setPrecincts] = useState<PrecinctStat[]>([]);
  const [selected, setSelected] = useState<number | undefined>(undefined);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/precincts")
      .then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).error || r.statusText);
        return r.json();
      })
      .then((d) => setPrecincts(d.precincts || []))
      .catch((e: Error) => setLoadError(e.message));
  }, []);

  return (
    <div className="pageGrid">
      <aside className="sidebar">
        <h2>Police precinct</h2>
        {loadError && <p className="error">{loadError}</p>}
        <ul>
          <li>
            <button
              type="button"
              className={selected === undefined ? "active" : ""}
              onClick={() => setSelected(undefined)}
            >
              All precincts
            </button>
          </li>
          {precincts.map((p) => (
            <li key={p.precinct}>
              <button
                type="button"
                className={selected === p.precinct_num ? "active" : ""}
                onClick={() => setSelected(p.precinct_num ?? undefined)}
              >
                {p.precinct} ({p.count})
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <MapView
        precinct={selected}
        onSelect={(uuid) => router.push(`/record/${uuid}`)}
      />
    </div>
  );
}
