"""Real-world malformed source-data cases for TraceBack ingestion QA."""

from __future__ import annotations

from pathlib import Path

import pytest

from traceback_app.evidence.loaders import LOGON_EVENT_SCHEMA, SourceDataError, load_json_records

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MALFORMED = PROJECT_ROOT / "tests" / "fixtures" / "malformed"
SCHEMA_ERRORS = MALFORMED / "schema-errors"


def test_utf16_json_reports_encoding_problem_with_reexport_guidance():
    path = MALFORMED / "encoding-problems" / "utf16-le-valid-json.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path)

    message = str(error_info.value)
    assert str(path) in message
    assert "Could not decode source data" in message
    assert "UTF-8" in message
    assert "re-export" in message


def test_invalid_byte_sequence_reports_encoding_problem():
    path = MALFORMED / "encoding-problems" / "invalid-byte-sequence.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path)

    message = str(error_info.value)
    assert str(path) in message
    assert "Could not decode source data" in message
    assert "not valid UTF-8" in message


def test_html_saved_as_json_reports_wrong_file_content_hint():
    path = MALFORMED / "wrong-file-content" / "html-saved-as-json.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path)

    message = str(error_info.value)
    assert str(path) in message
    assert "Could not parse JSON" in message
    assert "HTML" in message
    assert "wrong file" in message.lower()


def test_plain_text_saved_as_json_reports_wrong_file_content_hint():
    path = MALFORMED / "wrong-file-content" / "plain-text-saved-as-json.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path)

    message = str(error_info.value)
    assert str(path) in message
    assert "Could not parse JSON" in message
    assert "plain text" in message.lower()
    assert "wrong file" in message.lower()


def test_api_error_payload_saved_as_json_is_identified_as_error_payload():
    path = MALFORMED / "wrong-json-shape" / "api-error-payload.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path)

    message = str(error_info.value)
    assert str(path) in message
    assert "Expected a JSON array of records" in message
    assert "error payload" in message.lower()
    assert "not evidence records" in message.lower()


def test_mixed_schema_file_reports_record_where_schema_changes():
    path = SCHEMA_ERRORS / "mixed-logon-and-prefetch-events.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path, schema=LOGON_EVENT_SCHEMA)

    message = str(error_info.value)
    assert str(path) in message
    assert "record 2" in message
    assert "event_type" in message
    assert "windows_logon" in message
    assert "windows_prefetch_process_execution" in message


def test_partially_malformed_large_file_reports_bad_record_number_and_field():
    path = SCHEMA_ERRORS / "partially-malformed-large-file.json"

    with pytest.raises(SourceDataError) as error_info:
        load_json_records(path, schema=LOGON_EVENT_SCHEMA)

    message = str(error_info.value)
    assert str(path) in message
    assert "record 3" in message
    assert "timestamp_utc" in message
    assert "expected string" in message.lower()
    assert "found object" in message.lower()
