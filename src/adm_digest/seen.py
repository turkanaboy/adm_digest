from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path


def load_seen(path: str | Path) -> set[str]:
    file_path = Path(path)
    if not file_path.exists():
        return set()
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (JSONDecodeError, OSError):
        # A prior workflow run can leave this file partially written or manually
        # edited into invalid JSON. Treat it as an empty cache so the digest can
        # still run; save_seen will replace it with valid JSON after generation.
        return set()
    if isinstance(data, list):
        return set(data)
    if isinstance(data, dict):
        return set(data.get("articles", []))
    return set()


def save_seen(path: str | Path, seen: set[str]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump({"articles": sorted(seen)}, handle, indent=2)
        handle.write("\n")
    tmp_path.replace(file_path)
