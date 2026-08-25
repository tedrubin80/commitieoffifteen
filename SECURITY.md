# Security — public repository

This repo is **public**: https://github.com/tedrubin80/commitieoffifteen

## Never commit

| Item | Location |
|------|----------|
| NYPL API token | `.env` → `NYPL_API_TOKEN` |
| Vercel Postgres URLs | Vercel dashboard only |
| Railway tokens | Railway dashboard / CI secrets |
| NYC GeoClient keys | `NYC_GEOCLIENT_APP_ID`, `NYC_GEOCLIENT_APP_KEY` |
| Mapbox tokens | `MAPBOX_TOKEN`, `NEXT_PUBLIC_MAPBOX_TOKEN` |
| Hugging Face write token | `HF_TOKEN` (local/CI only) |
| Kaggle API key | `~/.kaggle/kaggle.json` (never in repo) |

## Gitignored by default

See `.gitignore` — all of `data/` (raw MODS, images, OCR, logs, API usage) stays local.

Only **derived, publishable tables** in `exports/` (built via `scripts/export_dataset.py`) go to HF/Kaggle — not git.

## Before every push

```bash
python scripts/check_secrets.py
git status   # confirm .env and data/ are not staged
```

If a token was ever committed, rotate it immediately (NYPL, Mapbox, Postgres, etc.) and use `git filter-repo` or GitHub secret scanning follow-up.

## Deploy secrets

- **Vercel:** set env vars in project settings; never in `vercel.json` or source.
- **Railway:** same — dashboard / GitHub Actions secrets only.
- **CI:** GitHub Actions → Repository secrets (`HF_TOKEN`, `KAGGLE_USERNAME`, `KAGGLE_KEY`).

## Dataset publishing

Published HF/Kaggle artifacts contain **metadata + OCR text + geocodes** — not NYPL scan JPEGs (rights UND). Each row links to the official NYPL item URL.
