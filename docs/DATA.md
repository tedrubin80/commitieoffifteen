# Data licensing & publishing

## Source

Primary source: [Committee of Fifteen records](https://digitalcollections.nypl.org/collections/216eff30-6f84-0133-9b03-00505686d14e), New York Public Library, Manuscripts and Archives Division.

Most items carry **Rights Statement: In Copyright – Rights Undetermined (UND)**. Do not redistribute NYPL scan images as a standalone corpus. This project links back to NYPL for every record.

## What we publish (HF + Kaggle)

Derived artifacts only — metadata tables, OCR text, geocodes, mined terms:

| Artifact | Description |
|----------|-------------|
| `committee_of_fifteen_enriched.parquet` | UUID, address, precinct, dates, NYPL links |
| `committee_of_fifteen_index.csv` | Capture-level index from NYPL API |
| `ocr/` | Tesseract text per UUID (best-effort, low-res scans) |
| `geocodes.csv` | Address → lat/lng (when geocoding phase completes) |
| `terms.csv` | Keyword mining output (when mining phase completes) |

**License for derived tables:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — attribute NYPL as the underlying source.

Suggested citation:

> Committee of Fifteen NYC Vice Investigation Dataset (derived). Ted Rubin, 2026. Source: New York Public Library Digital Collections, Committee of Fifteen records. https://github.com/tedrubin80/commitieoffifteen

## What stays out of git (and off HF/Kaggle)

- NYPL API tokens, Postgres URLs, geocoder keys (`.env` only)
- Raw JPEG scans (`data/images/`) — use NYPL CDN URLs in published tables instead
- Full MODS JSON dumps (large; re-fetchable via NYPL API with your own token)

## Publishing commands

```bash
# Build export bundle (parquet + csv + ocr zip, no secrets)
python scripts/export_dataset.py

# Hugging Face (requires `huggingface-cli login` locally — token never in repo)
huggingface-cli upload tedrubin80/committee-of-fifteen-dataset ./exports/* --repo-type dataset

# Kaggle (requires ~/.kaggle/kaggle.json locally — never commit)
kaggle datasets create -p ./exports/kaggle -r zip
```

Dataset URLs (update after first upload):

- Hugging Face: `https://huggingface.co/datasets/tedrubin80/committee-of-fifteen-dataset`
- Kaggle: `https://www.kaggle.com/datasets/tedrubin80/committee-of-fifteen-dataset`
