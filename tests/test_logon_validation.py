from pathlib import Path

import pytest

from traceback_app.claims.schema import ValidationStatus
from traceback_app.evidence.loaders import load_json_records
from traceback_app.validators.logon import validate_logon_claims

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATA = Path("/mnt/c/Users/Brandi Volpe/Markdown vaults/Find Evil Lab/Data created")
EVENTS_PATH = SOURCE_DATA / "windows_logon_events.synthetic.json"
CLAIMS_PATH = SOURCE_DATA / "windows_logon_claims.synthetic.json"


def _results_by_claim_id():
    events = load_json_records(EVENTS_PATH)
    claims = load_json_records(CLAIMS_PATH)
    results = validate_logon_claims(claims, events)
    return {result.claim_id: result for result in results}


def test_supported_logon_claim_returns_supported():
    results = _results_by_claim_id()

    result = results["claim-logon-supported-001"]

    assert result.status == ValidationStatus.SUPPORTED
    assert result.evidence_references[0]["event_uid"] == "synthetic-logon-0001"


def test_same_account_host_timestamp_with_wrong_logon_type_returns_contradicted():
    results = _results_by_claim_id()

    result = results["claim-logon-contradicted-001"]

    assert result.status == ValidationStatus.CONTRADICTED
    assert result.evidence_references[0]["logon_type"] == 3
    assert "Network" in result.explanation


def test_failed_logon_when_success_was_claimed_returns_contradicted():
    results = _results_by_claim_id()

    result = results["claim-logon-contradicted-002"]

    assert result.status == ValidationStatus.CONTRADICTED
    assert result.evidence_references[0]["event_action"] == "logon_failure"
    assert "logon_failure" in result.explanation


def test_claim_with_no_matching_event_returns_insufficient_evidence():
    results = _results_by_claim_id()

    result = results["claim-logon-insufficient-001"]

    assert result.status == ValidationStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence_references == []


def test_explanations_include_useful_evidence_references_when_evidence_exists():
    results = _results_by_claim_id()

    result = results["claim-logon-supported-001"]

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
    assert claims[0]["claim_id"] == "claim-logon-supported-001"
