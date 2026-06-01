import hashlib
import json
from pathlib import Path

import pytest

from traceback_app.evidence.browser_sqlite import extract_browser_activity_records, write_browser_activity_json_with_metadata
from traceback_app.evidence.loaders import SourceDataError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMALL_FIXTURE_DATA = PROJECT_ROOT / "tests" / "fixtures" / "small"
LARGE_FIXTURE_DATA = PROJECT_ROOT / "tests" / "fixtures" / "large"
MALFORMED_DB = PROJECT_ROOT / "tests" / "fixtures" / "malformed" / "database-errors"

SMALL_SQLITE_PATH = SMALL_FIXTURE_DATA / "browser_activity.synthetic.sqlite"
LARGE_SQLITE_PATH = LARGE_FIXTURE_DATA / "browser_activity.large.synthetic.sqlite"


def test_extract_small_browser_sqlite_records_matches_normalized_shape():
    records = extract_browser_activity_records(SMALL_SQLITE_PATH, account="addie_smith", host="WIN-FORENSIC-01")

    assert len(records) == 4
    assert records[0]["event_uid"] == "synthetic-browser-activity-0001"
    assert records[0]["event_type"] == "browser_activity"
    assert records[0]["artifact_type"] == "browser_history"
    assert records[0]["url"] == "https://example.org/security-checklist"


def test_extract_large_browser_sqlite_records_contains_base_and_noise_records():
    records = extract_browser_activity_records(LARGE_SQLITE_PATH, account="addie_smith", host="WIN-FORENSIC-01")
    event_uids = {record["event_uid"] for record in records}

    assert len(records) > 100
    assert "synthetic-browser-activity-0001" in event_uids
    assert "synthetic-browser-activity-0002" in event_uids
    assert "synthetic-browser-activity-0003" in event_uids
    assert "synthetic-browser-activity-0004" in event_uids


def test_write_browser_activity_json_also_writes_sidecar_metadata(tmp_path):
    output_path = tmp_path / "browser_activity_events.synthetic.json"

    result = write_browser_activity_json_with_metadata(
        SMALL_SQLITE_PATH,
        output_path,
        account="addie_smith",
        host="WIN-FORENSIC-01",
    )

    metadata_path = tmp_path / "browser_activity_events.synthetic.metadata.json"
    records = json.loads(output_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert result == {"records": output_path, "metadata": metadata_path}
    assert len(records) == 4
    assert metadata["traceback_metadata_version"] == "1.0"
    assert metadata["source_artifact"] == str(SMALL_SQLITE_PATH)
    assert metadata["source_sha256"] == _sha256(SMALL_SQLITE_PATH)
    assert metadata["normalized_file"] == str(output_path)
    assert metadata["normalized_sha256"] == _sha256(output_path)
    assert metadata["artifact_type"] == "browser_history"
    assert metadata["parser_tool"] == "traceback_chromium_history_sqlite_extractor"
    assert metadata["parser_tool_version"] == "0.1.0"
    assert metadata["parser_output"] is None
    assert metadata["parser_output_sha256"] is None
    assert metadata["record_count"] == 4


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("fixture_name", "expected_detail", "expected_action"),
    [
        (
            "empty-sqlite-file.sqlite",
            "not a valid SQLite browser History database",
            "Select a valid Chromium/Edge History SQLite database, copy the source artifact from evidence again, then rerun browser evidence extraction.",
        ),
        (
            "plain-text-saved-as-sqlite.sqlite",
            "not a valid SQLite browser History database",
            "Select a valid Chromium/Edge History SQLite database, copy the source artifact from evidence again, then rerun browser evidence extraction.",
        ),
        (
            "corrupt-header.sqlite",
            "not a valid SQLite browser History database",
            "Select a valid Chromium/Edge History SQLite database, copy the source artifact from evidence again, then rerun browser evidence extraction.",
        ),
        (
            "missing-history-table.sqlite",
            "missing required browser history table",
            "Select a Chromium/Edge History SQLite database with urls and visits tables, or update the extractor if this artifact uses a different browser/schema version.",
        ),
        (
            "wrong-column-shape.sqlite",
            "missing required browser history column",
            "Use a Chromium/Edge History database with the expected columns, or update the extractor for this browser/schema version.",
        ),
    ],
)
def test_malformed_browser_sqlite_reports_clear_source_data_error(fixture_name, expected_detail, expected_action):
    path = MALFORMED_DB / fixture_name

    with pytest.raises(SourceDataError) as error_info:
        extract_browser_activity_records(path, account="addie_smith", host="WIN-FORENSIC-01")

    message = str(error_info.value)
    assert str(path) in message
    assert "Could not load browser history database" in message
    assert expected_detail in message
    assert f"Action: {expected_action}" in message
