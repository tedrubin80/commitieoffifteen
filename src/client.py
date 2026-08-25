"""NYPL API client with daily 10k request budget (UTC day)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
USAGE_LOG = ROOT / "data" / "api_usage.jsonl"


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

BASE = os.environ.get("NYPL_API_BASE", "https://api.repo.nypl.org").rstrip("/")
TOKEN = os.environ.get("NYPL_API_TOKEN", "")
DAILY_BUDGET = int(os.environ.get("NYPL_API_BUDGET", "10000"))


class QuotaExceeded(RuntimeError):
    pass


def _today_utc() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def calls_used_today() -> int:
    if not USAGE_LOG.exists():
        return 0
    today = _today_utc()
    n = 0
    with USAGE_LOG.open() as f:
        for line in f:
            try:
                ts = json.loads(line).get("ts", "")
            except json.JSONDecodeError:
                continue
            if ts.startswith(today):
                n += 1
    return n


def remaining() -> int:
    return max(0, DAILY_BUDGET - calls_used_today())


def get_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if not TOKEN:
        raise RuntimeError("Set NYPL_API_TOKEN in .env")
    if remaining() <= 0:
        raise QuotaExceeded(f"Daily API budget exhausted ({DAILY_BUDGET}/day UTC)")

    url = f"{BASE}{path}" if path.startswith("/") else f"{BASE}/{path}"
    headers = {"Authorization": f"Token token={TOKEN}"}
    t0 = time.time()
    r = requests.get(url, headers=headers, params=params or {}, timeout=90)
    elapsed = time.time() - t0

    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with USAGE_LOG.open("a") as f:
        f.write(
            json.dumps(
                {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "path": path,
                    "params": params or {},
                    "status": r.status_code,
                    "bytes": len(r.content),
                    "elapsed_s": round(elapsed, 3),
                    "remaining_today_after": DAILY_BUDGET - calls_used_today() - 1,
                }
            )
            + "\n"
        )

    r.raise_for_status()
    return r.json()


def dollar(obj: Any) -> Any:
    """Flatten NYPL {'$': value} nodes."""
    if isinstance(obj, dict):
        if "$" in obj and set(obj.keys()) <= {"$", "description", "type", "authority", "usage", "lang", "script", "encoding", "point", "keyDate", "supplied", "displayLabel", "valueURI", "collection"}:
            return obj["$"]
        return {k: dollar(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [dollar(x) for x in obj]
    return obj
