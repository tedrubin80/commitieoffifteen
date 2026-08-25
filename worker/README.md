# Worker — Railway only

**Do not deploy this folder to Vercel.** Vercel is for the Next.js app in `../web/` only.

This service is a **Python FastAPI** batch worker:

- `railway_app.py` — HTTP API (`/health`, `/jobs/*`)
- `seed.py`, `geocode.py`, `ocr_sync.py`, `mine.py` — pipeline scripts
- `Dockerfile` — built from **repo root** (see `../railway.toml`)

## Railway setup

1. [railway.app/new](https://railway.app/new) → **Deploy from GitHub** → `tedrubin80/commitieoffifteen`
2. **Root Directory:** leave **empty** (repo root) — not `web`, not `worker`
3. Builder: **Dockerfile** (`railway.toml` → `worker/Dockerfile`)
4. **Public networking:** generate a domain (for `/health` and `/jobs/*`)
5. **Variables:**

| Variable | Value |
|----------|--------|
| `POSTGRES_URL` | Vercel Postgres **non-pooling** URL |
| `WORKER_SECRET` | random string |
| `NYC_GEOCLIENT_APP_ID` | optional |
| `NYC_GEOCLIENT_APP_KEY` | optional |
| `DATA_DIR` | `/data` if using a volume with parquet + ocr |

6. Health check path: `/health`

## Run pipeline

```bash
curl -X POST "https://YOUR-SERVICE.up.railway.app/jobs/pipeline" \
  -H "Authorization: Bearer YOUR_WORKER_SECRET"
```

## Local (with Postgres URL)

```bash
cd worker
pip install -r requirements.txt
POSTGRES_URL="..." python -c "from db import migrate; migrate()"
POSTGRES_URL="..." python seed.py
POSTGRES_URL="..." python geocode.py 20
```
