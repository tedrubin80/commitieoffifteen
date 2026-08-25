# Committee of Fifteen — NYC Vice Investigation Records (~1900)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Dataset: CC BY 4.0](https://img.shields.io/badge/Dataset-CC%20BY%204.0-green.svg)](docs/DATA.md)

Structured data work on a genuinely obscure NYPL primary-source archive: **1,731 digitized affidavits** from the [Committee of Fifteen](https://digitalcollections.nypl.org/collections/216eff30-6f84-0133-9b03-00505686d14e) — an early-1900s NYC investigation into prostitution and organized crime, indexed by **street address** and **police precinct**.

**Live app (planned):** Vercel map + search · **Compute:** Railway workers · **DB:** Vercel Postgres

---

## Dataset (Hugging Face & Kaggle)

Derived tables only — metadata, OCR text, geocodes. **No bulk republication of NYPL scan images** (rights undetermined).

| Platform | Dataset |
|----------|---------|
| Hugging Face | [tedrubin80/committee-of-fifteen-dataset](https://huggingface.co/datasets/tedrubin80/committee-of-fifteen-dataset) *(upload after first export)* |
| Kaggle | [committee-of-fifteen-nyc-vice-records](https://www.kaggle.com/datasets/tedrubin80/committee-of-fifteen-nyc-vice-records) *(upload after first export)* |

Build the export bundle locally:

```bash
pip install pandas pyarrow
python scripts/export_dataset.py
# → exports/records.parquet, exports/ocr.zip, exports/kaggle/
```

See [docs/DATA.md](docs/DATA.md) for licensing, citation, and upload commands.

---

## Corpus snapshot

| Metric | Value |
|--------|------:|
| Items | 1,731 |
| Address-titled affidavits | 1,710 |
| Unique addresses | ~1,708 |
| Police precincts | 36 |
| Date range | 1900–1901 |
| Top precinct | Precinct 15 (233 records) |

Each record links back to NYPL (`item_link`, `nypl_image_url`). Images are fetched from NYPL CDN during crawl; published datasets use URLs, not mirrored JPEGs.

---

## Pipeline

```
NYPL API  →  MODS metadata  →  enrich (precinct/address)
          →  JPEG download  →  Tesseract OCR
          →  geocode (NYC)   →  keyword mining
          →  Vercel Postgres + map/search UI
```

| Step | Script | Output |
|------|--------|--------|
| Crawl | `src/crawl.py` | `data/raw/`, `data/images/` |
| Enrich | `src/enrich.py` | `committee_of_fifteen_enriched.parquet` |
| OCR | `src/ocr.py` | `data/ocr/{uuid}.txt` |
| Export | `scripts/export_dataset.py` | `exports/` for HF/Kaggle |

OCR note: NYPL CDN JPEGs are ~340×760px. Tesseract output is noisy but usable for keyword search. NYPL `plain_text` API usually returns empty.

---

## Quick start (local crawl)

**Requirements:** Python 3.12+, [NYPL API token](https://api.repo.nypl.org/)

```bash
git clone https://github.com/tedrubin80/commitieoffifteen.git
cd commitieoffifteen
cp .env.example .env   # add NYPL_API_TOKEN — never commit .env

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python src/crawl.py      # listing → MODS → JPEGs (resumable)
python src/enrich.py     # precinct + address table
python src/ocr.py        # Tesseract (needs tesseract-ocr system package)
```

Docker (optional):

```bash
docker compose up -d --build
docker compose exec committee-of-fifteen python src/crawl.py
```

---

## Deployment plan

Full architecture: [PLAN.md](PLAN.md)

| Component | Platform |
|-----------|----------|
| Map + search UI | **Vercel** (Next.js) |
| Postgres | **Vercel Postgres** |
| Geocode / OCR / mining workers | **Railway** (Python) |

Build order: geocode → map → text mining → search.

---

## Security (public repo)

This repository is **public**. Never commit:

- `.env` or any API keys (NYPL, Postgres, GeoClient, Mapbox, HF, Kaggle)
- `data/api_usage.jsonl` or crawl logs with tokens
- Raw image corpus (large + NYPL rights)

Use `.env.example` as a template. Set secrets only in Vercel / Railway dashboards or local `.env` (gitignored).

If a token is ever exposed, rotate it immediately at the provider.

---

## License

| Component | License |
|-----------|---------|
| **Source code** in this repo | [MIT](LICENSE) |
| **Derived datasets** (metadata, OCR, geocodes on HF/Kaggle) | [CC BY 4.0](docs/DATA.md) |
| **NYPL original scans** | Not redistributed — [NYPL Digital Collections terms](https://www.nypl.org/legal/terms) apply |

---

## Citation

```bibtex
@misc{committeeoffifteen2026,
  author       = {Rubin, Ted},
  title        = {Committee of Fifteen NYC Vice Investigation Dataset},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/tedrubin80/commitieoffifteen},
  note         = {Derived from NYPL Digital Collections, Committee of Fifteen records}
}
```

---

## Source

- **Collection:** [Committee of Fifteen records](https://digitalcollections.nypl.org/collections/216eff30-6f84-0133-9b03-00505686d14e) — NYPL Manuscripts and Archives Division, MssCol 608
- **Rights:** Many items are UND (copyright undetermined). Research and linking OK; do not republish the image corpus wholesale.
