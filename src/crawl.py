"""Crawl Committee of Fifteen captures: listing → MODS → JPEG downloads.

Collection: https://digitalcollections.nypl.org/collections/216eff30-6f84-0133-9b03-00505686d14e
~1,731 digitized items (early-1900s NYC vice investigation affidavits/reports).

Rights on many items are UND (undetermined) — keep for local research; don't republish wholesale.
API plain_text often missing ("No Mets Alto") — we OCR locally from JPEGs later.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from tqdm import tqdm

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import QuotaExceeded, dollar, get_json, remaining  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
IMAGES = DATA / "images"
COLLECTION_UUID = "216eff30-6f84-0133-9b03-00505686d14e"
# Affidavits container returns the full 1731 capture list
LIST_UUID = "748ed170-6f84-0133-edde-00505686d14e"
PER_PAGE = 500


def list_all_captures() -> list[dict]:
    out_path = RAW / "captures.jsonl"
    RAW.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and out_path.stat().st_size > 0:
        rows = [json.loads(l) for l in out_path.open() if l.strip()]
        print(f"Reusing {len(rows)} captures from {out_path}")
        return rows

    page = 1
    rows: list[dict] = []
    while True:
        print(f"list page {page} remaining≈{remaining()}")
        data = get_json(
            f"/api/v2/items/collection/{LIST_UUID}",
            {"per_page": PER_PAGE, "page": page},
        )
        resp = (data.get("nyplAPI") or data.get("nyplAPI") or {}).get("response") or {}
        caps = resp.get("capture") or []
        if isinstance(caps, dict):
            caps = [caps]
        # normalize common field aliases
        for c in caps:
            if "imageID" not in c and "imageId" in c:
                c["imageID"] = c["imageId"]
            if "itemLink" not in c and "itemLink" in c:
                pass
        if not caps:
            break
        rows.extend(caps)
        total = int(resp.get("numResults") or 0)
        print(f"  got {len(caps)} (total so far {len(rows)}/{total})")
        if len(rows) >= total or len(caps) < PER_PAGE:
            break
        page += 1
        time.sleep(0.2)

    with out_path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"Wrote {len(rows)} → {out_path}")
    return rows


def fetch_mods(captures: list[dict]) -> None:
    out_dir = RAW / "mods"
    out_dir.mkdir(parents=True, exist_ok=True)
    for cap in tqdm(captures, desc="mods"):
        uuid = cap["uuid"]
        dest = out_dir / f"{uuid}.json"
        if dest.exists() and dest.stat().st_size > 100:
            continue
        try:
            data = get_json(f"/api/v2/items/mods/{uuid}")
            dest.write_text(json.dumps(dollar(data), indent=2))
        except QuotaExceeded:
            print("Quota hit — stop mods fetch; resume tomorrow")
            return
        except Exception as e:
            (out_dir / f"{uuid}.error").write_text(str(e))
        time.sleep(0.05)


def download_images(captures: list[dict], size: str = "w") -> None:
    """Download JPEGs via images.nypl.org (does NOT count against API quota)."""
    IMAGES.mkdir(parents=True, exist_ok=True)
    for cap in tqdm(captures, desc="images"):
        image_id = cap.get("imageID")
        uuid = cap["uuid"]
        if not image_id:
            continue
        dest = IMAGES / f"{uuid}.jpg"
        if dest.exists() and dest.stat().st_size > 1000:
            continue
        url = f"https://images.nypl.org/index.php?id={image_id}&t={size}"
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                dest.write_bytes(r.content)
            else:
                (IMAGES / f"{uuid}.fail").write_text(f"{r.status_code} {r.headers.get('content-type')}")
        except Exception as e:
            (IMAGES / f"{uuid}.fail").write_text(str(e))
        time.sleep(0.05)


def build_index(captures: list[dict]) -> None:
    import pandas as pd

    rows = []
    mods_dir = RAW / "mods"
    for cap in captures:
        uuid = cap["uuid"]
        row = {
            "uuid": uuid,
            "title": cap.get("title"),
            "image_id": cap.get("imageID"),
            "item_link": cap.get("itemLink"),
            "type_of_resource": cap.get("typeOfResource"),
            "date_digitized": cap.get("dateDigitized"),
            "rights_uri": cap.get("rightsStatementURI") or cap.get("rightsStatementURI"),
            "has_image": (IMAGES / f"{uuid}.jpg").exists(),
            "has_mods": (mods_dir / f"{uuid}.json").exists(),
        }
        mods_path = mods_dir / f"{uuid}.json"
        if mods_path.exists():
            try:
                mods = json.loads(mods_path.read_text())["nyplAPI"]["response"].get("mods") or {}
                titles = mods.get("titleInfo") or []
                if isinstance(titles, dict):
                    titles = [titles]
                if titles:
                    t0 = titles[0].get("title")
                    row["mods_title"] = t0 if isinstance(t0, str) else None
                genre = mods.get("genre")
                if isinstance(genre, dict):
                    row["genre"] = genre.get("$") or genre
                elif isinstance(genre, list) and genre:
                    g0 = genre[0]
                    row["genre"] = g0.get("$") if isinstance(g0, dict) else g0
                oi = mods.get("originInfo") or {}
                dc = oi.get("dateCreated")
                if isinstance(dc, list):
                    row["date_start"] = dc[0] if isinstance(dc[0], str) else (dc[0] or {}).get("$")
                    if len(dc) > 1:
                        row["date_end"] = dc[1] if isinstance(dc[1], str) else (dc[1] or {}).get("$")
                elif isinstance(dc, str):
                    row["date_start"] = dc
            except Exception:
                pass
        rows.append(row)

    out = DATA / "processed"
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_parquet(out / "committee_of_fifteen_index.parquet", index=False)
    df.to_csv(out / "committee_of_fifteen_index.csv", index=False)
    print(df["has_image"].value_counts())
    print(f"Wrote {len(df)} rows → {out}")


def main() -> None:
    print(f"API remaining today ≈ {remaining()}")
    captures = list_all_captures()
    fetch_mods(captures)
    download_images(captures)
    build_index(captures)
    print(f"Done. API remaining ≈ {remaining()}")


if __name__ == "__main__":
    main()
