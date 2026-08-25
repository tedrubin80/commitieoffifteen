"""Rule-based keyword mining → cof_terms."""

from __future__ import annotations

from tqdm import tqdm

from db import connect
from lexicon import PATTERNS


def run() -> int:
    with connect() as conn:
        rows = conn.execute(
            "SELECT uuid, ocr_text FROM cof_documents WHERE ocr_text IS NOT NULL"
        ).fetchall()

    upsert = """
    INSERT INTO cof_terms (uuid, term, category, count)
    VALUES (%(uuid)s, %(term)s, %(category)s, %(count)s)
    ON CONFLICT (uuid, term, category) DO UPDATE SET count = EXCLUDED.count
    """
    total = 0
    with connect() as conn:
        conn.execute("DELETE FROM cof_terms")
        for row in tqdm(rows, desc="mine"):
            text = row["ocr_text"] or ""
            for category, term, pat in PATTERNS:
                count = len(pat.findall(text))
                if count:
                    conn.execute(
                        upsert,
                        {"uuid": row["uuid"], "term": term, "category": category, "count": count},
                    )
                    total += 1
        conn.commit()
    print(f"Mined {total} term rows across {len(rows)} documents")
    return total


if __name__ == "__main__":
    run()
