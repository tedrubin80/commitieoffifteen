"""Batch geocode unique addresses → cof_geocodes."""

from __future__ import annotations

import json
import os
import time
from urllib.parse import quote

import requests
from tqdm import tqdm

from db import connect

USER_AGENT = "committee-of-fifteen/1.0 (github.com/tedrubin80/commitieoffifteen)"
SLEEP_S = float(os.environ.get("GEOCODE_SLEEP_S", "1.0"))


def geocode_query(address: str) -> str:
    return f"{address}, Manhattan, New York, NY"


def geocode_nyc_geoclient(query: str) -> dict | None:
    app_id = os.environ.get("NYC_GEOCLIENT_APP_ID")
    app_key = os.environ.get("NYC_GEOCLIENT_APP_KEY")
    if not app_id or not app_key:
        return None
    r = requests.get(
        "https://api.nyc.gov/geoclient/v1/search",
        params={"input": query, "app_id": app_id, "app_key": app_key},
        timeout=30,
    )
    if r.status_code != 200:
        return {"status": "failed", "geo_source": "nyc_geoclient", "raw": {"http": r.status_code}}
    data = r.json()
    results = data.get("results") or []
    if not results:
        return {"status": "failed", "geo_source": "nyc_geoclient", "raw": data}
    hit = results[0]["response"]
    lat = hit.get("latitude")
    lng = hit.get("longitude")
    if lat is None or lng is None:
        return {"status": "failed", "geo_source": "nyc_geoclient", "raw": hit}
    return {
        "lat": float(lat),
        "lng": float(lng),
        "geo_source": "nyc_geoclient",
        "confidence": 0.9,
        "status": "ok",
        "raw": hit,
    }


def geocode_mapbox(query: str) -> dict | None:
    token = os.environ.get("MAPBOX_TOKEN")
    if not token:
        return None
    r = requests.get(
        f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(query)}.json",
        params={
            "access_token": token,
            "limit": 1,
            "bbox": "-74.05,40.68,-73.90,40.82",
            "country": "us",
        },
        timeout=30,
    )
    if r.status_code != 200:
        return {"status": "failed", "geo_source": "mapbox", "raw": {"http": r.status_code}}
    data = r.json()
    features = data.get("features") or []
    if not features:
        return {"status": "failed", "geo_source": "mapbox", "raw": data}
    f0 = features[0]
    lng, lat = f0["center"]
    return {
        "lat": float(lat),
        "lng": float(lng),
        "geo_source": "mapbox",
        "confidence": float(f0.get("relevance", 0.5)),
        "status": "ok" if f0.get("relevance", 0) >= 0.6 else "ambiguous",
        "raw": f0,
    }


def geocode_nominatim(query: str) -> dict:
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 1, "countrycodes": "us"},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    if r.status_code != 200 or not r.json():
        return {"status": "failed", "geo_source": "nominatim", "raw": {"http": r.status_code}}
    hit = r.json()[0]
    return {
        "lat": float(hit["lat"]),
        "lng": float(hit["lon"]),
        "geo_source": "nominatim",
        "confidence": float(hit.get("importance", 0.3)),
        "status": "ok",
        "raw": hit,
    }


def geocode_one(address: str) -> dict:
    query = geocode_query(address)
    for fn in (geocode_nyc_geoclient, geocode_mapbox):
        result = fn(query)
        if result and result.get("status") == "ok":
            result["query"] = query
            return result
    result = geocode_nominatim(query)
    result["query"] = query
    return result


def run(limit: int | None = None) -> dict:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT address_norm
            FROM cof_records
            WHERE title_kind = 'address' AND address_norm IS NOT NULL
            ORDER BY address_norm
            """
        ).fetchall()

    pending = []
    with connect() as conn:
        for row in rows:
            addr = row["address_norm"]
            existing = conn.execute(
                "SELECT status FROM cof_geocodes WHERE address_norm = %s", (addr,)
            ).fetchone()
            if existing and existing["status"] in ("ok", "manual"):
                continue
            pending.append(addr)

    if limit:
        pending = pending[:limit]

    stats = {"ok": 0, "ambiguous": 0, "failed": 0}
    upsert = """
    INSERT INTO cof_geocodes (address_norm, query, lat, lng, geo_source, confidence, status, raw)
    VALUES (%(address_norm)s, %(query)s, %(lat)s, %(lng)s, %(geo_source)s, %(confidence)s, %(status)s, %(raw)s::jsonb)
    ON CONFLICT (address_norm) DO UPDATE SET
      query = EXCLUDED.query, lat = EXCLUDED.lat, lng = EXCLUDED.lng,
      geo_source = EXCLUDED.geo_source, confidence = EXCLUDED.confidence,
      status = EXCLUDED.status, raw = EXCLUDED.raw, geocoded_at = now()
    """

    for addr in tqdm(pending, desc="geocode"):
        result = geocode_one(addr)
        payload = {
            "address_norm": addr,
            "query": result.get("query", geocode_query(addr)),
            "lat": result.get("lat"),
            "lng": result.get("lng"),
            "geo_source": result.get("geo_source"),
            "confidence": result.get("confidence"),
            "status": result.get("status", "failed"),
            "raw": json.dumps(result.get("raw") or {}),
        }
        stats[payload["status"]] = stats.get(payload["status"], 0) + 1
        with connect() as conn:
            conn.execute(upsert, payload)
            conn.commit()
        time.sleep(SLEEP_S)

    print(stats)
    return stats


if __name__ == "__main__":
    import sys

    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run(lim)
