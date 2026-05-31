"""Malformed source-data ingestion tests for defensive TraceBack QA."""

from __future__ import annotations

from pathlib import Path

import pytest

from traceback_app import cli
from traceback_app.evidence.loaders import SourceDataError, load_json_records

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MALFORMED = PROJECT_ROOT / "tests" / "fixtures" / "malformed"
VALID_SMALL = PROJECT_ROOT / "tests" / "fixtures" / "small"


def test_invalid_json_reports_line_column_and_integrity_guidance():
    path = MALFORMED / "invalid-json" / "trailing-comma.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path)

    message = str(error_info.value)
    assert str(path) in message
    assert "Could not parse JSON" in message
    assert "line 3" in message
    assert "column 1" in message
    assert "verify the integrity of the source data" in message


def test_truncated_incomplete_write_reports_probable_incomplete_source_file():
    path = MALFORMED / "invalid-json" / "truncated-incomplete-write.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path)

    message = str(error_info.value)
    assert str(path) in message
    assert "Could not parse JSON" in message
    assert "line" in message
    assert "column" in message
    assert "incomplete" in message.lower()
    assert "verify the integrity of the source data" in message


@pytest.mark.parametrize(
    "fixture_name, expected_detail",
    [
        ("empty.json", "empty"),
        ("whitespace-only.json", "empty"),
    ],
)
def test_empty_or_placeholder_files_report_empty_source_data(fixture_name: str, expected_detail: str):
    path = MALFORMED / "empty-or-placeholder" / fixture_name

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path)

    message = str(error_info.value)
    assert str(path) in message
    assert expected_detail in message.lower()
    assert "verify the integrity of the source data" in message


@pytest.mark.parametrize(
    "fixture_path, expected_type",
    [
        (MALFORMED / "wrong-json-shape" / "object-wrapper.json", "object"),
        (MALFORMED / "wrong-json-shape" / "scalar-string.json", "string"),
    ],
)
def test_wrong_top_level_json_shape_reports_expected_array(fixture_path: Path, expected_type: str):
    with pytest.raises(SourceDataError) as error_info:
        load_json_records(fixture_path)

    message = str(error_info.value)
    assert str(fixture_path) in message
    assert "Expected a JSON array of records" in message
    assert expected_type in message
    assert "verify the integrity of the source data" in message


def test_array_with_non_object_row_reports_record_number():
    path = MALFORMED / "wrong-record-shape" / "array-with-string-item.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path)

    message = str(error_info.value)
    assert str(path) in message
    assert "record 2" in message
    assert "expected an object" in message.lower()
    assert "string" in message
    assert "verify the integrity of the source data" in message


def test_missing_file_reports_source_path_and_integrity_guidance():
    path = MALFORMED / "missing-file.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path)

    message = str(error_info.value)
    assert str(path) in message
    assert "not found" in message.lower()
    assert "verify the integrity of the source data" in message


def test_directory_path_reports_expected_file():
    path = MALFORMED / "invalid-json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path)

    message = str(error_info.value)
    assert str(path) in message
    assert "directory" in message.lower()
    assert "Expected a JSON source-data file" in message
    assert "verify the integrity of the source data" in message


def test_utf8_bom_source_file_is_accepted():
    path = MALFORMED / "encoding-problems" / "utf8-bom-valid.json"

    records = load_json_records(path)

    assert records == [
        {"event_uid": "evt-bom-001", "timestamp_utc": "2026-05-31T12:00:00Z"}
    ]


def test_cli_reports_malformed_events_without_python_traceback(capsys: pytest.CaptureFixture[str]):
    bad_events = MALFORMED / "invalid-json" / "truncated-incomplete-write.json"
    valid_claims = VALID_SMALL / "windows_logon_claims.synthetic.json"

    exit_code = cli.main(
        [
            "--validator",
            "logon",
            "--events",
            str(bad_events),
            "--claims",
            str(valid_claims),
        ]
    )

    captured = capsys.readouterr()
    combined_output = captured.out + captured.err
    assert exit_code == 2
    assert "Could not load source data" in combined_output
    assert str(bad_events) in combined_output
    assert "Could not parse JSON" in combined_output
    assert "verify the integrity of the source data" in combined_output
    assert "Traceback (most recent call last)" not in combined_output
