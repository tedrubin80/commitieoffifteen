"""Vice-investigation period lexicon for keyword mining."""

from __future__ import annotations

import re

LEXICON: dict[str, list[str]] = {
    "vice": [
        "disorderly house",
        "assignation",
        "immoral",
        "parlor house",
        "resort",
        "prostitution",
        "prostitute",
        "inmate",
        "frequenter",
    ],
    "legal": [
        "affidavit",
        "sworn",
        "precinct",
        "captain",
        "arrest",
        "summons",
        "investigator",
        "complaint",
    ],
    "trade": [
        "saloon",
        "hotel",
        "lodging",
        "keeper",
        "proprietor",
        "barroom",
        "restaurant",
    ],
    "person": [
        "madam",
        "witness",
        "affiant",
    ],
}


def compile_patterns() -> list[tuple[str, str, re.Pattern]]:
    out = []
    for category, terms in LEXICON.items():
        for term in terms:
            pat = re.compile(r"\b" + re.escape(term) + r"\b", re.I)
            out.append((category, term.lower(), pat))
    return out


PATTERNS = compile_patterns()
