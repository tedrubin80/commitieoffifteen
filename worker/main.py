"""Railway worker API — health + job triggers."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="Committee of Fifteen Worker", version="0.1.0")

WORKER_SECRET = os.environ.get("WORKER_SECRET", "")


def check_auth(authorization: str | None) -> None:
    if not WORKER_SECRET:
        return
    if authorization != f"Bearer {WORKER_SECRET}":
        raise HTTPException(401, "Unauthorized")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs/migrate")
def job_migrate(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    check_auth(authorization)
    from db import migrate

    migrate()
    return {"ok": True, "job": "migrate"}


@app.post("/jobs/seed")
def job_seed(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    check_auth(authorization)
    import seed

    n = seed.run(migrate_first=False)
    return {"ok": True, "job": "seed", "records": n}


@app.post("/jobs/geocode")
def job_geocode(
    limit: int | None = None,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    check_auth(authorization)
    import geocode

    stats = geocode.run(limit=limit)
    return {"ok": True, "job": "geocode", "stats": stats}


@app.post("/jobs/ocr-sync")
def job_ocr_sync(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    check_auth(authorization)
    import ocr_sync

    n = ocr_sync.run()
    return {"ok": True, "job": "ocr-sync", "documents": n}


@app.post("/jobs/mine")
def job_mine(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    check_auth(authorization)
    import mine

    n = mine.run()
    return {"ok": True, "job": "mine", "terms": n}


@app.post("/jobs/pipeline")
def job_pipeline(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """migrate → seed → geocode → ocr-sync → mine"""
    check_auth(authorization)
    from db import migrate
    import geocode
    import mine
    import ocr_sync
    import seed

    migrate()
    records = seed.run(migrate_first=False)
    geo = geocode.run()
    docs = ocr_sync.run()
    terms = mine.run()
    return {
        "ok": True,
        "job": "pipeline",
        "records": records,
        "geocode": geo,
        "documents": docs,
        "terms": terms,
    }
