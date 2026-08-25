"""Enrich Committee of Fifteen index from MODS metadata.

Extracts precinct hierarchy, normalizes address titles, and writes an analysis-ready table.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MODS_DIR = DATA / "raw" / "mods"
OUT = DATA / "processed"

STREET_RE = re.compile(
    r"\b("
    r"street|st\.?|avenue|ave\.?|broadway|road|rd\.?|lane|ln\.?|"
    r"place|pl\.?|boulevard|blvd\.?|way|alley|court|ct\.?|"
    r"wharf|slip|square|park|row|terrace|highway|hwy\.?"
    r")\b",
    re.I,
)
NUMBER_RE = re.compile(r"\d")


def _text(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        return val.strip() or None
    if isinstance(val, dict):
        return _text(val.get("$") or val.get("title"))
    return str(val).strip() or None


def _host_chain(related_item) -> list[tuple[str, str | None]]:
    """Walk relatedItem host chain → [(title, uuid), ...] outermost first."""
    chain: list[tuple[str, str | None]] = []
    node = related_item
    while node:
        tinfo = node.get("titleInfo") or {}
        title = _text(tinfo.get("title") if isinstance(tinfo, dict) else tinfo)
        uuid = None
        for ident in node.get("identifier") or []:
            if isinstance(ident, dict) and ident.get("type") == "uuid":
                uuid = ident.get("$")
                break
            if isinstance(ident, str):
                uuid = ident
        if title:
            chain.append((title, uuid))
        node = node.get("relatedItem")
    return chain


def parse_mods(path: Path) -> dict:
    data = json.loads(path.read_text())
    mods = data["nyplAPI"]["response"]["mods"]
    chain = _host_chain(mods.get("relatedItem"))
    precinct = next((t for t, _ in chain if "precinct" in t.lower()), None)
    collection = next((t for t, _ in chain if "committee of fifteen" in t.lower()), None)
    parent = chain[0][0] if chain else None

    titles = mods.get("titleInfo") or []
    if isinstance(titles, dict):
        titles = [titles]
    title = _text(titles[0].get("title")) if titles else None

    genres = mods.get("genre") or []
    if isinstance(genres, dict):
        genres = [genres]
    genre_list = [_text(g.get("$") if isinstance(g, dict) else g) for g in genres]
    genre_list = [g for g in genre_list if g]

    oi = mods.get("originInfo") or {}
    dc = oi.get("dateCreated") or []
    if isinstance(dc, dict):
        dc = [dc]
    dates = [_text(d) for d in dc]
    dates = [d for d in dates if d]

    return {
        "mods_title": title,
        "precinct": precinct,
        "parent_folder": parent,
        "collection": collection,
        "genres": "|".join(genre_list) if genre_list else None,
        "date_start": dates[0] if dates else None,
        "date_end": dates[1] if len(dates) > 1 else None,
        "host_chain": " > ".join(t for t, _ in reversed(chain)) if chain else None,
    }


def classify_title(title: str | None) -> str:
    if not title:
        return "unknown"
    t = title.strip()
    if STREET_RE.search(t) or NUMBER_RE.search(t):
        return "address"
    if t.lower().startswith(("sufferer", "witness", "affiant")):
        return "person"
    return "other"


def normalize_address(title: str | None) -> str | None:
    if not title:
        return None
    t = title.strip().strip('"“”')
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\bstreet\b", "Street", t, flags=re.I)
    t = re.sub(r"\bavenue\b", "Avenue", t, flags=re.I)
    t = re.sub(r"\bbroadway\b", "Broadway", t, flags=re.I)
    return t


def build_enriched_index() -> pd.DataFrame:
    rows = []
    for path in sorted(MODS_DIR.glob("*.json")):
        uuid = path.stem
        try:
            meta = parse_mods(path)
        except Exception as e:
            meta = {"mods_title": None, "precinct": None, "parse_error": str(e)}
        title = meta.get("mods_title")
        meta["uuid"] = uuid
        meta["title_kind"] = classify_title(title)
        meta["address_normalized"] = normalize_address(title) if meta["title_kind"] == "address" else None
        meta["has_image"] = (DATA / "images" / f"{uuid}.jpg").exists()
        meta["has_ocr"] = (DATA / "ocr" / f"{uuid}.txt").exists()
        rows.append(meta)

    df = pd.DataFrame(rows)
    out = OUT
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "committee_of_fifteen_enriched.parquet", index=False)
    df.to_csv(out / "committee_of_fifteen_enriched.csv", index=False)
    return df


def main() -> None:
    df = build_enriched_index()
    print(f"Wrote {len(df)} rows → {OUT}")
    print("\ntitle_kind:")
    print(df["title_kind"].value_counts().to_string())
    print("\nprecinct (top 15):")
    print(df["precinct"].value_counts().head(15).to_string())
    print(f"\naddresses: {(df['title_kind'] == 'address').sum()}")


if __name__ == "__main__":
    main()
