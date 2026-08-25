"""Batch OCR for Committee of Fifteen page scans.

NYPL `plain_text` is usually empty; we OCR locally from CDN JPEGs (~340×760px).
Quality is limited on these thumbnails — treat output as best-effort for search/mining.
"""

from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image, ImageFilter, ImageOps
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "data" / "images"
OCR_DIR = ROOT / "data" / "ocr"
SCALE = 6
TESS_CONFIG = "--psm 4 -c preserve_interword_spaces=1"


def preprocess(img: Image.Image) -> Image.Image:
    gray = img.convert("L")
    w, h = gray.size
    gray = gray.resize((w * SCALE, h * SCALE), Image.Resampling.LANCZOS)
    gray = ImageOps.autocontrast(gray)
    return gray.filter(ImageFilter.SHARPEN)


def ocr_image(path: Path) -> str:
    with Image.open(path) as img:
        proc = preprocess(img)
    return pytesseract.image_to_string(proc, config=TESS_CONFIG)


def run_all(limit: int | None = None) -> None:
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    images = sorted(IMAGES.glob("*.jpg"))
    if limit:
        images = images[:limit]
    done = skipped = empty = 0
    for path in tqdm(images, desc="ocr"):
        uuid = path.stem
        dest = OCR_DIR / f"{uuid}.txt"
        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue
        try:
            text = ocr_image(path)
            dest.write_text(text)
            if text.strip():
                done += 1
            else:
                empty += 1
        except Exception as e:
            (OCR_DIR / f"{uuid}.error").write_text(str(e))
    print(f"ocr written={done} empty={empty} skipped={skipped} → {OCR_DIR}")


if __name__ == "__main__":
    import sys

    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_all(lim)
