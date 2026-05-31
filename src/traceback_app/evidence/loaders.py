"""Load normalized evidence and claim records from local files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Any


JsonRecord = dict[str, Any]
INTEGRITY_GUIDANCE = "Please verify the integrity of the source data and regenerate or re-export it if needed."


@dataclass(frozen=True)
class RecordSchema:
    """Source-data integrity expectations for one TraceBack record family."""

    name: str
    required_fields: dict[str, type | tuple[type, ...]]
    unique_field: str
    expected_type_field: str | None = None
    expected_type_value: str | None = None
    timestamp_fields: tuple[str, ...] = ("timestamp_utc",)
    empty_detail: str = "The file contains no records."
    allow_empty: bool = False
    optional_type_fields: dict[str, type | tuple[type, ...]] = field(default_factory=dict)


LOGON_EVENT_SCHEMA = RecordSchema(
    name="Windows logon source evidence",
    required_fields={
        "event_uid": str,
        "event_type": str,
        "host": str,
        "timestamp_utc": str,
        "event_id": int,
        "event_action": str,
        "account": str,
    },
    unique_field="event_uid",
    expected_type_field="event_type",
    expected_type_value="windows_logon",
    empty_detail="The source evidence file contains no records for validation.",
)

LOGON_CLAIM_SCHEMA = RecordSchema(
    name="Windows logon claims",
    required_fields={
        "claim_id": str,
        "claim_type": str,
        "claim_text": str,
        "account": str,
        "host": str,
        "timestamp_utc": str,
        "expected_event_action": str,
        "expected_logon_type": int,
    },
    unique_field="claim_id",
    expected_type_field="claim_type",
    expected_type_value="windows_logon",
    empty_detail="The claims file contains no records to validate.",
)

PREFETCH_PROCESS_EVENT_SCHEMA = RecordSchema(
    name="Windows Prefetch process source evidence",
    required_fields={
        "event_uid": str,
        "event_type": str,
        "host": str,
        "timestamp_utc": str,
        "event_action": str,
        "account": str,
        "process_name": str,
    },
    unique_field="event_uid",
    expected_type_field="event_type",
    expected_type_value="windows_prefetch_process_execution",
    empty_detail="The source evidence file contains no records for validation.",
)

PREFETCH_PROCESS_CLAIM_SCHEMA = RecordSchema(
    name="Windows Prefetch process claims",
    required_fields={
        "claim_id": str,
        "claim_type": str,
        "claim_text": str,
        "account": str,
        "host": str,
        "timestamp_utc": str,
        "expected_event_action": str,
        "expected_process_name": str,
    },
    unique_field="claim_id",
    expected_type_field="claim_type",
    expected_type_value="windows_prefetch_process_execution",
    empty_detail="The claims file contains no records to validate.",
)


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


def load_json_records(path: str | Path, *, schema: RecordSchema | None = None) -> list[JsonRecord]:
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

    if schema is not None:
        _validate_record_schema(source_path, data, schema)

    return data


def _validate_record_schema(source_path: Path, records: list[JsonRecord], schema: RecordSchema) -> None:
    if not records and not schema.allow_empty:
        raise SourceDataError(source_path, "Could not load source data", schema.empty_detail)

    seen_unique_values: dict[object, int] = {}
    for index, record in enumerate(records, start=1):
        if schema.expected_type_field and schema.expected_type_value and schema.expected_type_field in record:
            _validate_expected_type_field(source_path, record, index, schema)

        for field_name, expected_type in schema.required_fields.items():
            if field_name not in record:
                raise SourceDataError(
                    source_path,
                    "Could not load source data",
                    f"At record {index}, missing required field `{field_name}` for {schema.name}.",
                )
            _validate_field_type(source_path, record, index, field_name, expected_type)

        for field_name, expected_type in schema.optional_type_fields.items():
            if field_name in record and record[field_name] is not None:
                _validate_field_type(source_path, record, index, field_name, expected_type)

        for field_name in schema.timestamp_fields:
            if field_name in record:
                _validate_iso_timestamp(source_path, record, index, field_name)

        unique_value = record.get(schema.unique_field)
        if unique_value in seen_unique_values:
            first_index = seen_unique_values[unique_value]
            raise SourceDataError(
                source_path,
                "Could not load source data",
                (
                    f"Duplicate `{schema.unique_field}` value `{unique_value}` found at "
                    f"records {first_index} and {index}."
                ),
            )
        seen_unique_values[unique_value] = index


def _validate_expected_type_field(
    source_path: Path,
    record: JsonRecord,
    index: int,
    schema: RecordSchema,
) -> None:
    actual_type = record.get(schema.expected_type_field)
    if actual_type == schema.expected_type_value:
        return

    raise SourceDataError(
        source_path,
        "Could not load source data",
        (
            f"At record {index}, field `{schema.expected_type_field}` expected "
            f"`{schema.expected_type_value}` for {schema.name}, but found `{actual_type}`. "
            "This may indicate the selected validator does not match the supplied source-data file."
        ),
    )


def _validate_field_type(
    source_path: Path,
    record: JsonRecord,
    index: int,
    field_name: str,
    expected_type: type | tuple[type, ...],
) -> None:
    value = record[field_name]
    if isinstance(value, expected_type):
        return

    raise SourceDataError(
        source_path,
        "Could not load source data",
        (
            f"At record {index}, field `{field_name}` expected {_type_label(expected_type)} "
            f"but found {_json_type_name(value)}."
        ),
    )


def _validate_iso_timestamp(source_path: Path, record: JsonRecord, index: int, field_name: str) -> None:
    value = record[field_name]
    if not isinstance(value, str):
        return

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceDataError(
            source_path,
            "Could not load source data",
            f"At record {index}, field `{field_name}` must be an ISO 8601 timestamp string, but found `{value}`.",
        ) from exc


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


def _type_label(expected_type: type | tuple[type, ...]) -> str:
    if isinstance(expected_type, tuple):
        return " or ".join(_single_type_label(item) for item in expected_type)
    return _single_type_label(expected_type)


def _single_type_label(expected_type: type) -> str:
    labels = {
        str: "string",
        int: "number",
        float: "number",
        bool: "boolean",
        dict: "object",
        list: "array",
    }
    return labels.get(expected_type, expected_type.__name__)
