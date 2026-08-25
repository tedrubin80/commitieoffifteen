#!/usr/bin/env python3
"""Build a publishable dataset bundle for Hugging Face / Kaggle (no secrets, no JPEGs)."""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EXPORT = ROOT / "exports"
KAGGLE = EXPORT / "kaggle"


def nypl_image_url(image_id: str | None) -> str | None:
    if not image_id:
        return None
    return f"https://images.nypl.org/index.php?id={image_id}&t=w"


def nypl_item_url(uuid: str) -> str:
    return f"https://digitalcollections.nypl.org/items/{uuid}"


def load_records() -> pd.DataFrame:
    enriched = DATA / "processed" / "committee_of_fifteen_enriched.parquet"
    index = DATA / "processed" / "committee_of_fifteen_index.csv"
    if enriched.exists():
        df = pd.read_parquet(enriched)
    elif index.exists():
        df = pd.read_csv(index)
    else:
        raise SystemExit("Run crawl + enrich first (data/processed/ missing)")

    if "item_link" not in df.columns and "uuid" in df.columns:
        df["item_link"] = df["uuid"].map(nypl_item_url)
    if "image_id" in df.columns:
        df["nypl_image_url"] = df["image_id"].map(nypl_image_url)
    return df


def load_ocr() -> pd.DataFrame:
    ocr_dir = DATA / "ocr"
    rows = []
    for path in sorted(ocr_dir.glob("*.txt")):
        text = path.read_text(errors="replace")
        rows.append({"uuid": path.stem, "ocr_text": text, "ocr_chars": len(text.strip())})
    return pd.DataFrame(rows)


def write_readme(out: Path, n_records: int, n_ocr: int) -> None:
    out.write_text(
        f"""---
license: cc-by-4.0
task_categories:
- text-classification
- token-classification
language:
- en
tags:
- history
- nyc
- nypl
- ocr
- primary-sources
size_categories:
- 1K<n<10K
---

# Committee of Fifteen — derived dataset

Early-1900s NYC vice investigation affidavits from NYPL Digital Collections.

- **Records:** {n_records}
- **OCR files:** {n_ocr}
- **Source:** [NYPL Committee of Fifteen records](https://digitalcollections.nypl.org/collections/216eff30-6f84-0133-9b03-00505686d14e)
- **Code:** https://github.com/tedrubin80/commitieoffifteen

## License

Derived tables: **CC BY 4.0**. Underlying NYPL scans remain under NYPL terms (UND). Image URLs point to NYPL CDN; do not bulk-mirror scans.

## Files

| File | Description |
|------|-------------|
| `records.parquet` | Metadata + precinct + address + NYPL URLs |
| `records.csv` | Same, CSV |
| `ocr.parquet` | UUID + OCR text |
| `ocr.zip` | Per-UUID `.txt` files |

Generated: {datetime.now(UTC).isoformat()}
"""
    )


def main() -> None:
    EXPORT.mkdir(parents=True, exist_ok=True)
    KAGGLE.mkdir(parents=True, exist_ok=True)

    records = load_records()
    ocr = load_ocr()
    merged = records.merge(ocr, on="uuid", how="left") if len(ocr) else records

    records.to_parquet(EXPORT / "records.parquet", index=False)
    records.to_csv(EXPORT / "records.csv", index=False)
    if len(ocr):
        ocr.to_parquet(EXPORT / "ocr.parquet", index=False)
        ocr.to_csv(EXPORT / "ocr.csv", index=False)

    ocr_zip = EXPORT / "ocr.zip"
    with zipfile.ZipFile(ocr_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted((DATA / "ocr").glob("*.txt")):
            zf.write(path, arcname=f"ocr/{path.name}")

    # Kaggle bundle (dataset-metadata.json + files)
    shutil.copy(EXPORT / "records.csv", KAGGLE / "records.csv")
    if (EXPORT / "ocr.csv").exists():
        shutil.copy(EXPORT / "ocr.csv", KAGGLE / "ocr.csv")
    write_readme(EXPORT / "README.md", len(records), len(ocr))
    shutil.copy(EXPORT / "README.md", KAGGLE / "README.md")

    meta = {
        "title": "committee-of-fifteen-nyc-vice-records",
        "id": "tedrubin80/committee-of-fifteen-nyc-vice-records",
        "licenses": [{"name": "CC BY 4.0"}],
        "keywords": ["history", "nyc", "nypl", "ocr", "primary-sources"],
        "description": "Derived metadata and OCR from NYPL Committee of Fifteen records (~1900 NYC).",
    }
    (KAGGLE / "dataset-metadata.json").write_text(json.dumps(meta, indent=2))

    print(f"Exported {len(records)} records, {len(ocr)} OCR → {EXPORT}")


if __name__ == "__main__":
    main()
