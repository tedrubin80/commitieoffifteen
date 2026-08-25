"""Load enriched parquet/CSV into Vercel Postgres."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

from db import connect, migrate

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
ENRICHED = DATA_DIR / "processed" / "committee_of_fifteen_enriched.parquet"
INDEX = DATA_DIR / "processed" / "committee_of_fifteen_index.csv"


def precinct_num(precinct: str | None) -> int | None:
    if not precinct:
        return None
    m = re.search(r"(\d+)", precinct)
    return int(m.group(1)) if m else None


def nypl_item_url(uuid: str) -> str:
    return f"https://digitalcollections.nypl.org/items/{uuid}"


def load_frame() -> pd.DataFrame:
    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        ENRICHED,
        repo_root / "data" / "processed" / "committee_of_fifteen_enriched.parquet",
        repo_root / "data" / "processed" / "committee_of_fifteen_enriched.csv",
        INDEX,
        repo_root / "data" / "processed" / "committee_of_fifteen_index.csv",
    ]
    for path in candidates:
        if path.exists():
            if path.suffix == ".parquet":
                return pd.read_parquet(path)
            return pd.read_csv(path)
    raise SystemExit(
        "No enriched data found. Mount DATA_DIR with processed parquet or run locally from repo root."
    )


def row_to_record(row) -> dict:
    uuid = str(row["uuid"])
    title = row.get("mods_title") or row.get("title") or uuid
    genres = row.get("genres")
    if isinstance(genres, str) and genres:
        genres_list = genres.split("|")
    elif isinstance(genres, list):
        genres_list = genres
    else:
        genres_list = None

    precinct = row.get("precinct")
    image_id = row.get("image_id")
    return {
        "uuid": uuid,
        "title": str(title),
        "address_norm": row.get("address_normalized") or row.get("address_norm"),
        "title_kind": row.get("title_kind"),
        "precinct": precinct,
        "precinct_num": precinct_num(precinct),
        "date_start": int(row["date_start"]) if pd.notna(row.get("date_start")) else None,
        "date_end": int(row["date_end"]) if pd.notna(row.get("date_end")) else None,
        "nypl_image_id": str(image_id) if pd.notna(image_id) else None,
        "nypl_item_url": row.get("item_link") or nypl_item_url(uuid),
        "genres": genres_list,
        "host_chain": row.get("host_chain"),
    }


def run(migrate_first: bool = True) -> int:
    if migrate_first:
        migrate()

    df = load_frame()
    records = [row_to_record(r) for _, r in df.iterrows()]

    sql = """
    INSERT INTO cof_records (
      uuid, title, address_norm, title_kind, precinct, precinct_num,
      date_start, date_end, nypl_image_id, nypl_item_url, genres, host_chain
    ) VALUES (
      %(uuid)s, %(title)s, %(address_norm)s, %(title_kind)s, %(precinct)s, %(precinct_num)s,
      %(date_start)s, %(date_end)s, %(nypl_image_id)s, %(nypl_item_url)s, %(genres)s, %(host_chain)s
    )
    ON CONFLICT (uuid) DO UPDATE SET
      title = EXCLUDED.title,
      address_norm = EXCLUDED.address_norm,
      title_kind = EXCLUDED.title_kind,
      precinct = EXCLUDED.precinct,
      precinct_num = EXCLUDED.precinct_num,
      date_start = EXCLUDED.date_start,
      date_end = EXCLUDED.date_end,
      nypl_image_id = EXCLUDED.nypl_image_id,
      nypl_item_url = EXCLUDED.nypl_item_url,
      genres = EXCLUDED.genres,
      host_chain = EXCLUDED.host_chain
    """

    with connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
        conn.commit()

    print(f"Seeded {len(records)} records")
    return len(records)


if __name__ == "__main__":
    run()
