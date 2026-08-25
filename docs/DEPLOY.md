# Deploy — Vercel + Railway

**Repo:** https://github.com/tedrubin80/commitieoffifteen (public — secrets only in dashboards)

## 1. Vercel Postgres

1. Vercel → Storage → Postgres → create / link to project
2. `POSTGRES_URL` and `POSTGRES_URL_NON_POOLING` auto-inject into the **web** project

Apply schema (from your machine, once):

```bash
psql "$POSTGRES_URL_NON_POOLING" -f db/migrations/001_init.sql
```

Or trigger via Railway worker: `POST /jobs/migrate`

## 2. Railway worker

1. New project from GitHub repo `tedrubin80/commitieoffifteen`
2. **Root directory:** repo root (uses `railway.toml` + `worker/Dockerfile`)
3. Env (copy from Vercel — use **non-pooling** URL for writes):

| Variable | Source |
|----------|--------|
| `POSTGRES_URL` | Vercel Postgres → non-pooling connection string |
| `NYC_GEOCLIENT_APP_ID` | [NYC API portal](https://api-portal.nyc.gov/) |
| `NYC_GEOCLIENT_APP_KEY` | same |
| `MAPBOX_TOKEN` | optional fallback geocoder |
| `WORKER_SECRET` | random string — protects `/jobs/*` |
| `DATA_DIR` | `/data` if using Railway volume with processed parquet + ocr |

4. Optional volume mounted at `/data`:
   - `processed/committee_of_fifteen_enriched.parquet`
   - `ocr/*.txt`

5. Health check: `GET /health`

### Run pipeline

With volume or after uploading data to the volume:

```bash
curl -X POST "https://YOUR-RAILWAY-APP.up.railway.app/jobs/pipeline" \
  -H "Authorization: Bearer YOUR_WORKER_SECRET"
```

Or step-by-step:

```bash
curl -X POST .../jobs/migrate -H "Authorization: Bearer $WORKER_SECRET"
curl -X POST .../jobs/seed -H "Authorization: Bearer $WORKER_SECRET"
curl -X POST .../jobs/geocode -H "Authorization: Bearer $WORKER_SECRET"
curl -X POST .../jobs/ocr-sync -H "Authorization: Bearer $WORKER_SECRET"
curl -X POST .../jobs/mine -H "Authorization: Bearer $WORKER_SECRET"
```

**Local seed** (no volume — reads `data/processed/` from repo checkout on Hetzner):

```bash
cd worker
pip install -r requirements.txt
POSTGRES_URL="..." python seed.py
POSTGRES_URL="..." python geocode.py 10   # test 10 addresses first
```

Geocode full run ~30 min at 1 req/s for ~1,708 addresses.

## 3. Vercel web

1. Import repo → **Root Directory:** `web`
2. Framework: Next.js (auto)
3. Env: `POSTGRES_URL` from Vercel Postgres integration (pooled URL is fine for reads)
4. Deploy

Routes:

- `/` — stats + links
- `/map` — MapLibre + OSM tiles, precinct filter
- `/search` — Postgres full-text
- `/record/[uuid]` — detail + NYPL image link + OCR

## 4. Hugging Face + Kaggle

After OCR progress:

```bash
python scripts/export_dataset.py
huggingface-cli upload tedrubin80/committee-of-fifteen-dataset ./exports/* --repo-type dataset
kaggle datasets create -p ./exports/kaggle -r zip
```

Never upload `.env`, API tokens, or raw NYPL JPEGs.

## 5. Security checklist

- [ ] `.env` not in git (`python scripts/check_secrets.py` before push)
- [ ] `WORKER_SECRET` set on Railway before exposing worker URL
- [ ] Postgres URL only in Vercel/Railway env — not in README or code
- [ ] Rotate NYPL token if ever exposed (public repo)
