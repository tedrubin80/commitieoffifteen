#!/usr/bin/env python3
"""Pre-push guard: fail if secrets or local data paths are staged."""

from __future__ import annotations

import re
import subprocess
import sys

BLOCKED_PATHS = (
    ".env",
    "data/",
    "exports/",
    "kaggle.json",
)

SECRET_PATTERNS = (
    re.compile(r"NYPL_API_TOKEN[ \t]*=[ \t]*[^\s\n#]{8,}"),
    re.compile(r"postgres(?:ql)?://\S+", re.I),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
)


def staged_files() -> list[str]:
    out = subprocess.check_output(["git", "diff", "--cached", "--name-only"], text=True)
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def staged_diff() -> str:
    return subprocess.check_output(["git", "diff", "--cached"], text=True, errors="replace")


def main() -> int:
    files = staged_files()
    errors: list[str] = []

    for path in files:
        if path == ".env.example":
            continue
        if path == ".env":
            errors.append(f"blocked path staged: {path}")
            continue
        for blocked in ("data/", "exports/", "kaggle.json"):
            if path == blocked or path.startswith(blocked):
                errors.append(f"blocked path staged: {path}")

    diff = staged_diff()
    # Ignore this script's own pattern definitions
    diff = re.sub(r"^\+.*check_secrets\.py.*$", "", diff, flags=re.M)
    diff = re.sub(r"^\+.*re\.compile.*$", "", diff, flags=re.M)
    for pat in SECRET_PATTERNS:
        if pat.search(diff):
            errors.append(f"secret pattern matched: {pat.pattern}")

    if errors:
        print("check_secrets.py FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("check_secrets.py OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
