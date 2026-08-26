# Deploy — Vercel + Railway

**Repo:** https://github.com/tedrubin80/commitieoffifteen (public — secrets only in dashboards)

## Which platform for what

| Component | Platform | Root directory |
|-----------|----------|----------------|
| **Web** (Next.js + Prisma) | **Vercel** | `web` |
| **Worker** (FastAPI) | **Railway** | `worker` or repo root — **not Vercel** |
| **Database** | Vercel Postgres / Neon via **Prisma** | shared by both |

FastAPI / “no Next.js” errors on the **worker** mean it was pointed at **Vercel** by mistake. Use [worker/README.md](../worker/README.md).

## 1. Prisma + Vercel Postgres

You already have Prisma connected on Vercel and wired into Railway. Map env vars:

| App | Env var | Value |
|-----|---------|--------|
| **Vercel `web/`** | `DATABASE_URL` | Prisma / Neon **pooled** URL (Prisma Client) |
| **Railway worker** | `POSTGRES_URL` or `DATABASE_URL` | Same DB — prefer **non-pooling / direct** URL for writes |

If Vercel injects `POSTGRES_PRISMA_URL`, either rename/copy it to `DATABASE_URL` in project settings, or set:

```
DATABASE_URL=$POSTGRES_PRISMA_URL
```

Apply schema once (SQL matches Prisma models in `web/prisma/schema.prisma`):

```bash
# from web/ with DATABASE_URL set (or use non-pooling URL):
cd web && npx prisma db push

# or via worker:
psql "$POSTGRES_URL_NON_POOLING" -f db/migrations/001_init.sql
# or Railway: POST /jobs/migrate
```

## 2. Railway worker

1. New project from GitHub repo `tedrubin80/commitieoffifteen`
2. **Root Directory:** **empty** (repo root) — not `web`, not `worker`
3. Builder: Dockerfile via `railway.toml` → `worker/Dockerfile`
5. Env (copy from Vercel — use **non-pooling** URL for writes):

| Variable | Source |
|----------|--------|
| `POSTGRES_URL` or `DATABASE_URL` | Same Prisma DB — **non-pooling / DIRECT_URL** preferred |
| `NYC_GEOCLIENT_APP_ID` | [NYC API portal](https://api-portal.nyc.gov/) |
| `NYC_GEOCLIENT_APP_KEY` | same |
| `MAPBOX_TOKEN` | optional fallback geocoder |
| `WORKER_SECRET` | random string — protects `/jobs/*` |
| `DATA_DIR` | `/data` if using Railway volume with processed parquet + ocr |

6. Optional volume mounted at `/data`:
   - `processed/committee_of_fifteen_enriched.parquet`
   - `ocr/*.txt`

7. Health check: `GET /health`

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
3. Env: `DATABASE_URL` = Prisma pooled URL (required for `@prisma/client`)
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

## 5. GitHub Actions (recommended)

Workflows in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `deploy.yml` | push to `main` | Vercel web + Railway worker |
| `pipeline.yml` | manual | POST `/jobs/pipeline` on worker |

### GitHub secrets (repo → Settings → Secrets → Actions)

| Secret | Source |
|--------|--------|
| `VERCEL_TOKEN` | [vercel.com/account/tokens](https://vercel.com/account/tokens) |
| `VERCEL_ORG_ID` | `cd web && vercel link` → `.vercel/project.json` → `orgId` |
| `VERCEL_PROJECT_ID` | same file → `projectId` |
| `RAILWAY_TOKEN` | [railway.app/account/tokens](https://railway.app/account/tokens) |
| `RAILWAY_PROJECT_ID` | Railway project → Settings |
| `RAILWAY_SERVICE_ID` | Worker service → Settings |
| `RAILWAY_WORKER_URL` | Worker public URL (for pipeline workflow) |
| `WORKER_SECRET` | Same as Railway `WORKER_SECRET` env |

Helper script (run locally after `vercel link`):

```bash
bash scripts/wire_deploy.sh
```

### Vercel project settings

- **Root Directory:** `web` (exactly — lowercase, no leading `/`)
- **Framework Preset:** Next.js
- `package.json` with `"next"` lives at `web/package.json`
- If Root Directory is blank, repo-root `vercel.json` + `package.json` build `web/` as fallback
- Worker FastAPI is `worker/railway_app.py` (Railway only)

## 6. Security checklist

- [ ] `.env` not in git (`python scripts/check_secrets.py` before push)
- [ ] `WORKER_SECRET` set on Railway before exposing worker URL
- [ ] Postgres URL only in Vercel/Railway env — not in README or code
- [ ] Rotate NYPL token if ever exposed (public repo)
