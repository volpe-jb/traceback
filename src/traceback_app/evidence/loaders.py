"""Load normalized evidence and claim records from local files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any


JsonRecord = dict[str, Any]
INTEGRITY_GUIDANCE = "Please verify the integrity of the source data and regenerate or re-export it if needed."


@dataclass(frozen=True)
class SourceDataError(ValueError):
    """User-facing source-data ingestion failure with recovery guidance."""

    file_path: Path
    message: str
    detail: str | None = None
    suggested_action: str = INTEGRITY_GUIDANCE

    def __str__(self) -> str:
        parts = [f"{self.message}: {self.file_path}"]
        if self.detail:
            parts.append(f"Reason: {self.detail}")
        parts.append(f"Action: {self.suggested_action}")
        return "\n".join(parts)


def load_json_records(path: str | Path) -> list[JsonRecord]:
    """Load a JSON array of objects from ``path``.

    TraceBack's first experiment consumes normalized JSON fixture files.
    This loader does defensive source-data integrity checks before domain
    validators run so malformed inputs are reported as ingestion failures, not
    as unsupported forensic claims.
    """

    source_path = Path(path)
    text = _read_source_text(source_path)

    if not text.strip():
        raise SourceDataError(
            source_path,
            "Could not load source data",
            "The source-data file is empty or contains only whitespace.",
        )

    try:
        data = json.loads(text)
    except JSONDecodeError as exc:
        detail = f"Could not parse JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}."
        if _looks_incomplete_json_error(exc):
            detail += " The file appears incomplete, as if an export/copy operation did not finish writing."
        raise SourceDataError(source_path, "Could not parse JSON", detail) from exc

    if not isinstance(data, list):
        raise SourceDataError(
            source_path,
            "Could not load source data",
            f"Expected a JSON array of records, but found {_json_type_name(data)}.",
        )

    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise SourceDataError(
                source_path,
                "Could not load source data",
                f"At record {index}, expected an object but found {_json_type_name(item)}.",
            )

    return data


def _read_source_text(source_path: Path) -> str:
    if not source_path.exists():
        raise SourceDataError(
            source_path,
            "Could not load source data",
            "The source-data file was not found.",
        )

    if source_path.is_dir():
        raise SourceDataError(
            source_path,
            "Could not load source data",
            "Expected a JSON source-data file, but the supplied path is a directory.",
        )

    try:
        return source_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceDataError(
            source_path,
            "Could not decode source data",
            f"The file is not valid UTF-8 JSON text: {exc}.",
        ) from exc
    except PermissionError as exc:
        raise SourceDataError(
            source_path,
            "Could not read source data",
            "Permission denied while reading the source-data file.",
        ) from exc
    except OSError as exc:
        raise SourceDataError(
            source_path,
            "Could not read source data",
            str(exc),
        ) from exc


def _looks_incomplete_json_error(exc: JSONDecodeError) -> bool:
    incomplete_markers = (
        "expecting value",
        "expecting property name enclosed in double quotes",
        "unterminated string",
        "expecting ',' delimiter",
    )
    return exc.msg.lower() in incomplete_markers


def _json_type_name(value: object) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__
