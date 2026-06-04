from __future__ import annotations

import json
from pathlib import Path


def load_seen(path: str | Path) -> set[str]:
    file_path = Path(path)
    if not file_path.exists():
        return set()
    with file_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return set(data)
    if isinstance(data, dict):
        return set(data.get("articles", []))
    return set()


def save_seen(path: str | Path, seen: set[str]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump({"articles": sorted(seen)}, handle, indent=2)
        handle.write("\n")
