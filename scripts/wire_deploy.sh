#!/usr/bin/env bash
# One-time wiring helper — run locally after creating Vercel + Railway projects.
# Requires: gh auth login, vercel login (or tokens), railway login (or token)
set -euo pipefail

REPO="tedrubin80/commitieoffifteen"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Committee of Fifteen deploy wiring ==="
echo "Repo: https://github.com/${REPO}"
echo

need_secret() {
  local name="$1"
  local val="$2"
  if [ -z "$val" ]; then
    echo "Skip ${name} (empty)"
    return 1
  fi
  echo "Setting GitHub secret ${name}..."
  printf '%s' "$val" | gh secret set "$name" -R "$REPO"
  return 0
}

echo "--- Vercel IDs (from web/.vercel/project.json after: cd web && vercel link) ---"
if [ -f "$ROOT/web/.vercel/project.json" ]; then
  ORG_ID=$(python3 -c "import json; print(json.load(open('$ROOT/web/.vercel/project.json'))['orgId'])")
  PROJ_ID=$(python3 -c "import json; print(json.load(open('$ROOT/web/.vercel/project.json'))['projectId'])")
  echo "orgId=$ORG_ID"
  echo "projectId=$PROJ_ID"
  need_secret VERCEL_ORG_ID "$ORG_ID" || true
  need_secret VERCEL_PROJECT_ID "$PROJ_ID" || true
else
  echo "Run: cd web && vercel link"
  echo "Then re-run this script, or set VERCEL_ORG_ID / VERCEL_PROJECT_ID manually in GitHub."
fi

echo
echo "--- Tokens (paste when prompted, or export env vars first) ---"
read -rsp "VERCEL_TOKEN (vercel.com/account/tokens): " VERCEL_TOKEN; echo
need_secret VERCEL_TOKEN "${VERCEL_TOKEN:-}" || true

read -rsp "RAILWAY_TOKEN (railway.app/account/tokens): " RAILWAY_TOKEN; echo
need_secret RAILWAY_TOKEN "${RAILWAY_TOKEN:-}" || true

read -rp "RAILWAY_PROJECT_ID: " RAILWAY_PROJECT_ID
need_secret RAILWAY_PROJECT_ID "$RAILWAY_PROJECT_ID" || true

read -rp "RAILWAY_SERVICE_ID (worker service): " RAILWAY_SERVICE_ID
need_secret RAILWAY_SERVICE_ID "$RAILWAY_SERVICE_ID" || true

read -rp "RAILWAY_WORKER_URL (https://....up.railway.app): " WORKER_URL
need_secret RAILWAY_WORKER_URL "$WORKER_URL" || true

read -rsp "WORKER_SECRET (same as Railway env): " WORKER_SECRET; echo
need_secret WORKER_SECRET "$WORKER_SECRET" || true

echo
echo "=== GitHub secrets ==="
gh secret list -R "$REPO"

echo
echo "=== Next steps ==="
echo "1. Vercel: import repo, Root Directory = web, link Postgres storage"
echo "2. psql \"\$POSTGRES_URL_NON_POOLING\" -f db/migrations/001_init.sql"
echo "3. Railway: set POSTGRES_URL (non-pooling), WORKER_SECRET, optional NYC geocoder keys"
echo "4. Push to main → Actions deploys both services"
echo "5. Actions → Run worker pipeline → pipeline (or curl POST /jobs/pipeline)"
