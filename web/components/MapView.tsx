"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { FeatureCollection } from "geojson";

type Props = {
  precinct?: number;
  onSelect?: (uuid: string) => void;
};

export default function MapView({ precinct, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      center: [-73.985, 40.748],
      zoom: 12.2,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const url = precinct ? `/api/map?precinct=${precinct}` : "/api/map";
    fetch(url)
      .then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).error || r.statusText);
        return r.json() as Promise<FeatureCollection>;
      })
      .then((geojson) => {
        setError(null);
        setCount(geojson.features.length);

        if (map.getSource("records")) {
          (map.getSource("records") as maplibregl.GeoJSONSource).setData(geojson);
          return;
        }

        map.addSource("records", { type: "geojson", data: geojson });
        map.addLayer({
          id: "records-dots",
          type: "circle",
          source: "records",
          paint: {
            "circle-radius": 5,
            "circle-color": "#b91c1c",
            "circle-stroke-width": 1,
            "circle-stroke-color": "#fff",
            "circle-opacity": 0.85,
          },
        });

        map.on("click", "records-dots", (e) => {
          const f = e.features?.[0];
          const uuid = f?.properties?.uuid as string | undefined;
          if (uuid && onSelect) onSelect(uuid);
        });
        map.on("mouseenter", "records-dots", () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "records-dots", () => {
          map.getCanvas().style.cursor = "";
        });

        if (geojson.features.length > 0) {
          const bounds = new maplibregl.LngLatBounds();
          geojson.features.forEach((f) => {
            if (f.geometry.type === "Point") {
              bounds.extend(f.geometry.coordinates as [number, number]);
            }
          });
          map.fitBounds(bounds, { padding: 48, maxZoom: 15 });
        }
      })
      .catch((e: Error) => setError(e.message));
  }, [precinct, onSelect]);

  return (
    <div className="mapWrap">
      <div ref={containerRef} className="mapCanvas" />
      <div className="mapMeta">
        {error ? <span className="error">{error}</span> : <span>{count} geocoded points</span>}
      </div>
    </div>
  );
}
