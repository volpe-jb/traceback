from pathlib import Path

from traceback_app.claims.schema import ValidationStatus
from traceback_app.evidence.loaders import BROWSER_ACTIVITY_EVENT_SCHEMA, load_json_records
from traceback_app.validators.browser_activity import validate_browser_activity_claims

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMALL_FIXTURE_DATA = PROJECT_ROOT / "tests" / "fixtures" / "small"
LARGE_FIXTURE_DATA = PROJECT_ROOT / "tests" / "fixtures" / "large"

SMALL_EVENTS_PATH = SMALL_FIXTURE_DATA / "browser_activity_events.synthetic.json"
SMALL_CLAIMS_PATH = SMALL_FIXTURE_DATA / "browser_activity_claims.synthetic.json"
LARGE_EVENTS_PATH = LARGE_FIXTURE_DATA / "browser_activity_events.large.synthetic.json"
LARGE_CLAIMS_PATH = LARGE_FIXTURE_DATA / "browser_activity_claims.large.synthetic.json"


def _results_by_claim_id(events_path=SMALL_EVENTS_PATH, claims_path=SMALL_CLAIMS_PATH):
    events = load_json_records(events_path, schema=BROWSER_ACTIVITY_EVENT_SCHEMA)
    claims = load_json_records(claims_path)
    results = validate_browser_activity_claims(claims, events)
    return {result.claim_id: result for result in results}


def _assert_expected_browser_outcomes(results):
    supported = results["claim-browser-001"]
    wrong_url = results["claim-browser-002"]
    wrong_action = results["claim-browser-003"]
    missing = results["claim-browser-004"]

    assert supported.status == ValidationStatus.SUPPORTED
    assert supported.evidence_references[0]["event_uid"] == "synthetic-browser-activity-0001"
    assert supported.evidence_references[0]["url"] == "https://example.org/security-checklist"

    assert wrong_url.status == ValidationStatus.CONTRADICTED
    assert wrong_url.evidence_references[0]["url"] == "https://example.org/benign-search"
    assert wrong_url.expected_values["url"] == "https://example.org/suspicious-download"
    assert wrong_url.explanation.startswith(
        "Contradicted by normalized browser activity evidence for the same account, host, and timestamp."
    )
    assert "Claim checked:" not in wrong_url.explanation
    assert "suspicious-download" in wrong_url.explanation
    assert "benign-search" in wrong_url.explanation

    assert wrong_action.status == ValidationStatus.CONTRADICTED
    assert wrong_action.evidence_references[0]["activity_type"] == "visit"
    assert wrong_action.expected_values["activity_type"] == "download"
    assert "Why this contradicts the claim:" not in wrong_action.explanation
    assert "download" in wrong_action.contradiction_reason
    assert "visit" in wrong_action.contradiction_reason

    assert missing.status == ValidationStatus.INSUFFICIENT_EVIDENCE
    assert missing.evidence_references == []
    assert missing.expected_values == {
        "account": "addie_smith",
        "host": "WIN-FORENSIC-01",
        "timestamp_utc": "2026-05-20T16:30:00Z",
    }


def test_small_browser_activity_claims_return_expected_outcomes():
    results = _results_by_claim_id()

    _assert_expected_browser_outcomes(results)


def test_large_browser_activity_claims_return_same_expected_outcomes_as_small_fixture():
    results = _results_by_claim_id(LARGE_EVENTS_PATH, LARGE_CLAIMS_PATH)

    _assert_expected_browser_outcomes(results)


def test_loader_can_read_existing_synthetic_browser_activity_json_files():
    events = load_json_records(SMALL_EVENTS_PATH, schema=BROWSER_ACTIVITY_EVENT_SCHEMA)
    claims = load_json_records(SMALL_CLAIMS_PATH)

    assert len(events) == 4
    assert len(claims) == 4
    assert events[0]["event_uid"] == "synthetic-browser-activity-0001"
    assert events[0]["artifact_type"] == "browser_history"
    assert claims[0]["claim_id"] == "claim-browser-001"
