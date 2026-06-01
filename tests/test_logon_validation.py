from pathlib import Path

import pytest

from traceback_app.claims.schema import ValidationStatus
from traceback_app.evidence.loaders import load_json_records
from traceback_app.report.markdown import results_to_markdown
from traceback_app.validators.logon import validate_logon_claims

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATA = PROJECT_ROOT / "tests" / "fixtures" / "small"
EVENTS_PATH = FIXTURE_DATA / "windows_logon_events.synthetic.json"
CLAIMS_PATH = FIXTURE_DATA / "windows_logon_claims.synthetic.json"


def _results_by_claim_id():
    events = load_json_records(EVENTS_PATH)
    claims = load_json_records(CLAIMS_PATH)
    results = validate_logon_claims(claims, events)
    return {result.claim_id: result for result in results}


def test_supported_logon_claim_returns_supported():
    results = _results_by_claim_id()

    result = results["claim-logon-001"]

    assert result.status == ValidationStatus.SUPPORTED
    assert result.evidence_references[0]["event_uid"] == "synthetic-logon-0001"


def test_same_account_host_timestamp_with_wrong_logon_type_returns_contradicted():
    results = _results_by_claim_id()

    result = results["claim-logon-002"]

    assert result.status == ValidationStatus.CONTRADICTED
    assert result.evidence_references[0]["logon_type"] == 3
    assert "Network" in result.explanation


def test_failed_logon_when_success_was_claimed_returns_contradicted():
    results = _results_by_claim_id()

    result = results["claim-logon-003"]

    assert result.status == ValidationStatus.CONTRADICTED
    assert result.evidence_references[0]["event_action"] == "logon_failure"
    assert "logon_failure" in result.explanation


def test_contradicted_results_capture_expected_observed_and_plain_english_reason():
    results = _results_by_claim_id()

    wrong_type = results["claim-logon-002"]
    failed_success = results["claim-logon-003"]

    assert wrong_type.claim_text in wrong_type.explanation
    assert wrong_type.expected_values == {
        "event_action": "logon_success",
        "logon_type": 2,
        "logon_type_label": "Interactive",
    }
    assert wrong_type.observed_values == [
        {
            "event_action": "logon_success",
            "logon_type": 3,
            "logon_type_label": "Network",
        }
    ]
    assert (
        "The claim says this was an Interactive console logon, but the matching "
        "Windows Security event shows a Network logon."
        in wrong_type.contradiction_reason
    )

    assert failed_success.claim_text in failed_success.explanation
    assert failed_success.expected_values["event_action"] == "logon_success"
    assert failed_success.observed_values[0]["event_action"] == "logon_failure"
    assert (
        "The claim says the logon succeeded, but the matching Windows Security "
        "event is a failed logon event."
        in failed_success.contradiction_reason
    )


def test_markdown_report_for_contradictions_shows_claim_expected_evidence_and_reason():
    results = _results_by_claim_id()

    markdown = results_to_markdown([results["claim-logon-003"]])

    assert "Claim checked:" in markdown
    assert "What the claim expected:" in markdown
    assert "| Field | Value |" in markdown
    assert "| expected_event_action | logon_success |" in markdown
    assert "| expected_logon_type | 2 |" in markdown
    assert "| expected_logon_type_label | Interactive |" in markdown
    assert "What the evidence actually shows:" in markdown
    assert "What the evidence shows:" not in markdown
    assert "| event_uid | synthetic-logon-0005 |" in markdown
    assert "| event_id | 4625 |" in markdown
    assert "| event_action | logon_failure |" in markdown
    assert "| logon_type | 2 |" in markdown
    assert "| logon_type_label | Interactive |" in markdown
    assert "Why this contradicts the claim:" in markdown
    assert (
        "The claim says the logon succeeded, but the matching Windows Security "
        "event is a failed logon event."
        in markdown
    )


def test_claim_with_no_matching_event_returns_insufficient_evidence():
    results = _results_by_claim_id()

    result = results["claim-logon-004"]

    assert result.status == ValidationStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence_references == []


def test_explanations_include_useful_evidence_references_when_evidence_exists():
    results = _results_by_claim_id()

    result = results["claim-logon-001"]

    assert "synthetic-logon-0001" in result.explanation
    assert "4624" in result.explanation
    assert "2026-05-20T14:03:22Z" in result.explanation
    assert "addie_smith" in result.explanation
    assert "WIN-FORENSIC-01" in result.explanation
    assert "logon_success" in result.explanation
    assert "Interactive" in result.explanation


def test_loader_can_read_existing_synthetic_logon_json_files():
    events = load_json_records(EVENTS_PATH)
    claims = load_json_records(CLAIMS_PATH)

    assert len(events) == 8
    assert len(claims) == 4
    assert events[0]["event_uid"] == "synthetic-logon-0001"
    assert claims[0]["claim_id"] == "claim-logon-001"
