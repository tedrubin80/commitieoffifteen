"""Upsert local OCR text files into cof_documents."""

from __future__ import annotations

import os
from pathlib import Path

from tqdm import tqdm

from db import connect

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
OCR_DIR = DATA_DIR / "ocr"


def ocr_quality(text: str) -> tuple[int, str]:
    n = len(text.strip())
    if n < 50:
        return n, "empty"
    if n < 200:
        return n, "low"
    return n, "medium"


def run() -> int:
    repo_ocr = Path(__file__).resolve().parents[1] / "data" / "ocr"
    ocr_dir = OCR_DIR if OCR_DIR.exists() else repo_ocr
    if not ocr_dir.exists():
        raise SystemExit(f"No OCR directory at {ocr_dir}")

    files = sorted(ocr_dir.glob("*.txt"))
    sql = """
    INSERT INTO cof_documents (uuid, ocr_text, char_count, quality)
    VALUES (%(uuid)s, %(ocr_text)s, %(char_count)s, %(quality)s)
    ON CONFLICT (uuid) DO UPDATE SET
      ocr_text = EXCLUDED.ocr_text,
      char_count = EXCLUDED.char_count,
      quality = EXCLUDED.quality
    """
    n = 0
    with connect() as conn:
        for path in tqdm(files, desc="ocr-sync"):
            text = path.read_text(errors="replace")
            chars, quality = ocr_quality(text)
            conn.execute(
                sql,
                {"uuid": path.stem, "ocr_text": text, "char_count": chars, "quality": quality},
            )
            n += 1
        conn.commit()
    print(f"Synced {n} OCR documents")
    return n


if __name__ == "__main__":
    run()
