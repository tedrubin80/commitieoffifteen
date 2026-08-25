"""Postgres helpers for Railway worker."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

MIGRATION_CANDIDATES = (
    Path(__file__).resolve().parent / "migrations" / "001_init.sql",
    Path(__file__).resolve().parents[1] / "db" / "migrations" / "001_init.sql",
)


def migration_path() -> Path:
    for path in MIGRATION_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError(f"No migration SQL found in {MIGRATION_CANDIDATES}")


def db_url() -> str:
    url = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Set POSTGRES_URL or DATABASE_URL")
    return url


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(db_url(), row_factory=dict_row) as conn:
        yield conn


def migrate() -> None:
    path = migration_path()
    sql = path.read_text()
    with connect() as conn:
        conn.execute(sql)
        conn.commit()
    print(f"Applied migration → {path}")
