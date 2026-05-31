"""Load normalized evidence and claim records from local files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


JsonRecord = dict[str, Any]


def load_json_records(path: str | Path) -> list[JsonRecord]:
    """Load a JSON array of objects from ``path``.

    TraceBack's first experiment consumes normalized JSON fixture files.
    This loader intentionally does only basic shape validation so the
    deterministic validators remain responsible for domain decisions.
    """

    source_path = Path(path)
    with source_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        raise ValueError(f"Expected {source_path} to contain a JSON array.")

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"Expected every item in {source_path} to be an object; "
                f"item {index} is {type(item).__name__}."
            )

    return data
