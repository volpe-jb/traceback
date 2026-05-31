"""Schema-level source-data integrity tests for TraceBack."""

from __future__ import annotations

from pathlib import Path

import pytest

from traceback_app import cli
from traceback_app.evidence.loaders import (
    LOGON_CLAIM_SCHEMA,
    LOGON_EVENT_SCHEMA,
    SourceDataError,
    load_json_records,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ERRORS = PROJECT_ROOT / "tests" / "fixtures" / "malformed" / "schema-errors"
VALID_SMALL = PROJECT_ROOT / "tests" / "fixtures" / "small"


def test_missing_required_field_reports_record_number_and_field_name():
    path = SCHEMA_ERRORS / "logon-event-missing-event-uid.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path, schema=LOGON_EVENT_SCHEMA)

    message = str(error_info.value)
    assert str(path) in message
    assert "record 1" in message
    assert "missing required field" in message.lower()
    assert "event_uid" in message
    assert "verify the integrity of the source data" in message


def test_wrong_field_type_reports_record_number_field_name_and_expected_type():
    path = SCHEMA_ERRORS / "logon-event-wrong-event-uid-type.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path, schema=LOGON_EVENT_SCHEMA)

    message = str(error_info.value)
    assert str(path) in message
    assert "record 1" in message
    assert "event_uid" in message
    assert "expected string" in message.lower()
    assert "found number" in message.lower()


def test_invalid_timestamp_reports_record_number_and_field_name():
    path = SCHEMA_ERRORS / "logon-event-invalid-timestamp.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path, schema=LOGON_EVENT_SCHEMA)

    message = str(error_info.value)
    assert str(path) in message
    assert "record 1" in message
    assert "timestamp_utc" in message
    assert "ISO 8601" in message


def test_duplicate_evidence_id_reports_duplicate_value_and_records():
    path = SCHEMA_ERRORS / "duplicate-event-uid.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path, schema=LOGON_EVENT_SCHEMA)

    message = str(error_info.value)
    assert str(path) in message
    assert "duplicate" in message.lower()
    assert "event_uid" in message
    assert "synthetic-logon-0001" in message
    assert "records 1 and 2" in message


def test_duplicate_claim_id_reports_duplicate_value_and_records():
    path = SCHEMA_ERRORS / "duplicate-claim-id.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path, schema=LOGON_CLAIM_SCHEMA)

    message = str(error_info.value)
    assert str(path) in message
    assert "duplicate" in message.lower()
    assert "claim_id" in message
    assert "claim-logon-001" in message
    assert "records 1 and 2" in message


def test_empty_claims_array_reports_no_claims_to_validate():
    path = SCHEMA_ERRORS / "empty-claims-array.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path, schema=LOGON_CLAIM_SCHEMA)

    message = str(error_info.value)
    assert str(path) in message
    assert "no records" in message.lower()
    assert "claims" in message.lower()


def test_empty_events_array_reports_no_source_evidence_available():
    path = SCHEMA_ERRORS / "empty-events-array.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path, schema=LOGON_EVENT_SCHEMA)

    message = str(error_info.value)
    assert str(path) in message
    assert "no records" in message.lower()
    assert "source evidence" in message.lower()


def test_wrong_validator_file_pairing_reports_expected_event_type():
    path = SCHEMA_ERRORS / "prefetch-events-passed-to-logon-validator.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path, schema=LOGON_EVENT_SCHEMA)

    message = str(error_info.value)
    assert str(path) in message
    assert "record 1" in message
    assert "event_type" in message
    assert "windows_logon" in message
    assert "windows_prefetch_process_execution" in message


def test_cli_reports_schema_integrity_error_without_traceback(capsys: pytest.CaptureFixture[str]):
    bad_events = SCHEMA_ERRORS / "logon-event-missing-event-uid.json"
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
    assert "record 1" in combined_output
    assert "event_uid" in combined_output
    assert "Traceback (most recent call last)" not in combined_output
