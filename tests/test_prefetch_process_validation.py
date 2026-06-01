from pathlib import Path

import pytest

from traceback_app.claims.schema import ValidationStatus
from traceback_app.evidence.loaders import load_json_records
from traceback_app.report.markdown import results_to_markdown
from traceback_app.validators.prefetch_process import validate_prefetch_process_claims

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATA = PROJECT_ROOT / "tests" / "fixtures" / "small"
EVENTS_PATH = FIXTURE_DATA / "windows_prefetch_process_events.synthetic.json"
CLAIMS_PATH = FIXTURE_DATA / "windows_prefetch_process_claims.synthetic.json"


def _results_by_claim_id():
    events = load_json_records(EVENTS_PATH)
    claims = load_json_records(CLAIMS_PATH)
    results = validate_prefetch_process_claims(claims, events)
    return {result.claim_id: result for result in results}


def test_supported_prefetch_process_claim_returns_supported():
    results = _results_by_claim_id()

    result = results["claim-process-001"]

    assert result.status == ValidationStatus.SUPPORTED
    assert result.evidence_references[0]["event_uid"] == "synthetic-prefetch-process-0001"
    assert result.evidence_references[0]["process_name"] == "notepad.exe"


def test_same_account_host_timestamp_with_wrong_process_name_returns_contradicted():
    results = _results_by_claim_id()

    result = results["claim-process-002"]

    assert result.status == ValidationStatus.CONTRADICTED
    assert result.evidence_references[0]["process_name"] == "calc.exe"
    assert result.expected_values["process_name"] == "powershell.exe"
    assert "calc.exe" in result.explanation
    assert "powershell.exe" in result.explanation


def test_prefetch_absent_when_execution_was_claimed_returns_contradicted():
    results = _results_by_claim_id()

    result = results["claim-process-003"]

    assert result.status == ValidationStatus.CONTRADICTED
    assert result.evidence_references[0]["event_action"] == "prefetch_absent"
    assert result.expected_values["event_action"] == "process_executed"
    assert "matching normalized Prefetch record exists" in result.contradiction_reason
    assert "contradicted rather than unsupported" in result.contradiction_reason


def test_claim_with_no_matching_prefetch_process_event_returns_insufficient_evidence():
    results = _results_by_claim_id()

    result = results["claim-process-004"]

    assert result.status == ValidationStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence_references == []


def test_prefetch_process_explanations_include_useful_evidence_references_when_evidence_exists():
    results = _results_by_claim_id()

    result = results["claim-process-001"]

    assert "synthetic-prefetch-process-0001" in result.explanation
    assert "2026-05-20T14:08:10Z" in result.explanation
    assert "addie_smith" in result.explanation
    assert "WIN-FORENSIC-01" in result.explanation
    assert "process_executed" in result.explanation
    assert "notepad.exe" in result.explanation
    assert "C:\\Windows\\Prefetch\\NOTEPAD.EXE-12345678.pf" in result.explanation


def test_markdown_report_for_prefetch_process_contradiction_shows_expected_evidence_and_reason():
    results = _results_by_claim_id()

    markdown = results_to_markdown([results["claim-process-002"]], title="TraceBack Prefetch Process Validation Summary")

    assert "TraceBack Prefetch Process Validation Summary" in markdown
    assert "Claim checked:" in markdown
    assert "What the claim expected:" in markdown
    assert "| Field | Value |" in markdown
    assert "| expected_event_action | process_executed |" in markdown
    assert "| expected_process_name | powershell.exe |" in markdown
    assert "What the evidence actually shows:" in markdown
    assert "What the evidence shows:" not in markdown
    assert "| event_uid | synthetic-prefetch-process-0002 |" in markdown
    assert "| event_action | process_executed |" in markdown
    assert "| process_name | calc.exe |" in markdown
    assert "| source_artifact | C:\\Windows\\Prefetch\\CALC.EXE-87654321.pf |" in markdown
    assert "Why this contradicts the claim:" in markdown
    assert "The claim says powershell.exe executed, but the matching Prefetch-style evidence shows calc.exe." in markdown


def test_loader_can_read_existing_synthetic_prefetch_process_json_files():
    events = load_json_records(EVENTS_PATH)
    claims = load_json_records(CLAIMS_PATH)

    assert len(events) == 4
    assert len(claims) == 4
    assert events[0]["event_uid"] == "synthetic-prefetch-process-0001"
    assert events[0]["artifact_type"] == "windows_prefetch"
    assert claims[0]["claim_id"] == "claim-process-001"
