"""Extract normalized browser activity records from Chromium-style SQLite History databases."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from traceback_app import __version__
from traceback_app.evidence.loaders import SourceDataError

CHROMIUM_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)
REQUIRED_TABLES = {"urls", "visits"}
REQUIRED_COLUMNS = {
    "urls": {"id", "url", "title"},
    "visits": {"id", "url", "visit_time"},
}


def extract_browser_activity_records(path: str | Path, *, account: str, host: str) -> list[dict[str, Any]]:
    """Extract normalized browser visit records from a Chromium/Edge History SQLite database."""

    source_path = Path(path)
    _ensure_readable_sqlite_file(source_path)

    try:
        with sqlite3.connect(f"file:{source_path}?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            _validate_browser_history_schema(connection, source_path)
            rows = connection.execute(
                """
                SELECT
                    visits.id AS visit_id,
                    urls.url AS url,
                    urls.title AS title,
                    visits.visit_time AS visit_time
                FROM visits
                JOIN urls ON urls.id = visits.url
                ORDER BY visits.visit_time, visits.id
                """
            ).fetchall()
    except SourceDataError:
        raise
    except sqlite3.DatabaseError as exc:
        raise _invalid_sqlite_error(source_path, str(exc)) from exc
    except OSError as exc:
        raise SourceDataError(
            source_path,
            "Could not load browser history database",
            str(exc),
            "Verify the browser History database path and copy the database to a readable evidence location before extraction.",
        ) from exc

    return [_row_to_record(row, source_path, account=account, host=host) for row in rows]


def write_browser_activity_json_with_metadata(
    path: str | Path,
    output_path: str | Path,
    *,
    account: str,
    host: str,
) -> dict[str, Path]:
    """Write normalized Chromium/Edge browser activity JSON plus sidecar provenance metadata."""

    source_path = Path(path)
    normalized_path = Path(output_path)
    metadata_path = normalized_path.with_suffix(".metadata.json")

    records = extract_browser_activity_records(source_path, account=account, host=host)
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    metadata = {
        "traceback_metadata_version": "1.0",
        "source_artifact": str(source_path),
        "source_sha256": _sha256(source_path),
        "normalized_file": str(normalized_path),
        "normalized_sha256": _sha256(normalized_path),
        "artifact_type": "browser_history",
        "parser_tool": "traceback_chromium_history_sqlite_extractor",
        "parser_tool_version": __version__,
        "parser_output": None,
        "parser_output_sha256": None,
        "record_count": len(records),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    return {"records": normalized_path, "metadata": metadata_path}


def _ensure_readable_sqlite_file(source_path: Path) -> None:
    if not source_path.exists():
        raise SourceDataError(
            source_path,
            "Could not load browser history database",
            "The browser History SQLite file was not found.",
            "Check the evidence path or copy the browser History database into the fixture/evidence folder before extraction.",
        )
    if source_path.is_dir():
        raise SourceDataError(
            source_path,
            "Could not load browser history database",
            "Expected a browser History SQLite file, but the supplied path is a directory.",
            "Choose the specific browser History database file instead of a folder.",
        )
    if source_path.stat().st_size == 0:
        raise _invalid_sqlite_error(source_path, "The file is empty.")


def _validate_browser_history_schema(connection: sqlite3.Connection, source_path: Path) -> None:
    table_rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    table_names = {row["name"] for row in table_rows}
    missing_tables = sorted(REQUIRED_TABLES - table_names)
    if missing_tables:
        raise SourceDataError(
            source_path,
            "Could not load browser history database",
            f"The database is missing required browser history table(s): {', '.join(missing_tables)}.",
            "Select a Chromium/Edge History SQLite database with urls and visits tables, or update the extractor if this artifact uses a different browser/schema version.",
        )

    for table_name, required_columns in REQUIRED_COLUMNS.items():
        column_rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        column_names = {row["name"] for row in column_rows}
        missing_columns = sorted(required_columns - column_names)
        if missing_columns:
            raise SourceDataError(
                source_path,
                "Could not load browser history database",
                f"Table `{table_name}` is missing required browser history column(s): {', '.join(missing_columns)}.",
                "Use a Chromium/Edge History database with the expected columns, or update the extractor for this browser/schema version.",
            )


def _row_to_record(row: sqlite3.Row, source_path: Path, *, account: str, host: str) -> dict[str, Any]:
    visit_id = int(row["visit_id"])
    return {
        "event_uid": f"synthetic-browser-activity-{visit_id:04d}",
        "event_type": "browser_activity",
        "artifact_type": "browser_history",
        "evidence_category": "browser_activity",
        "source": "synthetic_edge_history_sqlite",
        "source_artifact": str(source_path),
        "parser_tool": "traceback_browser_sqlite_extractor",
        "host": host,
        "timestamp_utc": _chromium_time_to_iso(int(row["visit_time"])),
        "event_action": "browser_activity_observed",
        "account": account,
        "user_context": f"profile:{account}",
        "activity_type": "visit",
        "browser": "Microsoft Edge",
        "url": row["url"],
        "title": row["title"],
        "download_name": None,
        "synthetic": True,
    }


def _chromium_time_to_iso(value: int) -> str:
    timestamp = CHROMIUM_EPOCH + timedelta(microseconds=value)
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _invalid_sqlite_error(source_path: Path, detail: str) -> SourceDataError:
    return SourceDataError(
        source_path,
        "Could not load browser history database",
        f"The file is not a valid SQLite browser History database. {detail}",
        "Select a valid Chromium/Edge History SQLite database, copy the source artifact from evidence again, then rerun browser evidence extraction.",
    )
