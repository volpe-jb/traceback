import importlib.util
from pathlib import Path

from traceback_app.claims.schema import ValidationStatus
from traceback_app.evidence.loaders import load_json_records
from traceback_app.validators.logon import validate_logon_claims
from traceback_app.validators.prefetch_process import validate_prefetch_process_claims

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATA = PROJECT_ROOT / "tests" / "fixtures" / "small"
LARGE_FIXTURE_DATA = PROJECT_ROOT / "tests" / "fixtures" / "large"
GENERATOR_PATH = PROJECT_ROOT / "scripts" / "generate_noisy_synthetic_data.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_noisy_synthetic_data", GENERATOR_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _statuses_by_claim_id(results):
    return {result.claim_id: result.status for result in results}


def test_noisy_fixture_generator_keeps_base_claim_outcomes_inside_larger_files(tmp_path):
    generator = _load_generator()
    generated = generator.generate_all(
        input_dir=SOURCE_DATA,
        output_dir=tmp_path,
        logon_noise_count=75,
        prefetch_noise_count=75,
    )

    _assert_large_fixture_outcomes(
        logon_events_path=generated["logon_events"],
        logon_claims_path=generated["logon_claims"],
        prefetch_events_path=generated["prefetch_events"],
        prefetch_claims_path=generated["prefetch_claims"],
        expected_logon_events=83,
        expected_prefetch_events=79,
    )


def test_committed_large_fixtures_keep_base_claim_outcomes():
    _assert_large_fixture_outcomes(
        logon_events_path=LARGE_FIXTURE_DATA / "windows_logon_events.large.synthetic.json",
        logon_claims_path=LARGE_FIXTURE_DATA / "windows_logon_claims.large.synthetic.json",
        prefetch_events_path=LARGE_FIXTURE_DATA / "windows_prefetch_process_events.large.synthetic.json",
        prefetch_claims_path=LARGE_FIXTURE_DATA / "windows_prefetch_process_claims.large.synthetic.json",
        expected_logon_events=258,
        expected_prefetch_events=254,
    )


def _assert_large_fixture_outcomes(
    *,
    logon_events_path: Path,
    logon_claims_path: Path,
    prefetch_events_path: Path,
    prefetch_claims_path: Path,
    expected_logon_events: int,
    expected_prefetch_events: int,
):
    logon_events = load_json_records(logon_events_path)
    logon_claims = load_json_records(logon_claims_path)
    prefetch_events = load_json_records(prefetch_events_path)
    prefetch_claims = load_json_records(prefetch_claims_path)

    assert len(logon_events) == expected_logon_events
    assert len(logon_claims) == 4
    assert len(prefetch_events) == expected_prefetch_events
    assert len(prefetch_claims) == 4

    logon_event_ids = {event["event_uid"] for event in logon_events}
    prefetch_event_ids = {event["event_uid"] for event in prefetch_events}

    assert "synthetic-logon-0001" in logon_event_ids
    assert "synthetic-logon-0003" in logon_event_ids
    assert "synthetic-logon-0005" in logon_event_ids
    assert "synthetic-prefetch-process-0001" in prefetch_event_ids
    assert "synthetic-prefetch-process-0002" in prefetch_event_ids
    assert "synthetic-prefetch-process-0003" in prefetch_event_ids

    logon_results = validate_logon_claims(logon_claims, logon_events)
    prefetch_results = validate_prefetch_process_claims(prefetch_claims, prefetch_events)

    assert _statuses_by_claim_id(logon_results) == {
        "claim-logon-001": ValidationStatus.SUPPORTED,
        "claim-logon-002": ValidationStatus.CONTRADICTED,
        "claim-logon-003": ValidationStatus.CONTRADICTED,
        "claim-logon-004": ValidationStatus.INSUFFICIENT_EVIDENCE,
    }
    assert _statuses_by_claim_id(prefetch_results) == {
        "claim-process-001": ValidationStatus.SUPPORTED,
        "claim-process-002": ValidationStatus.CONTRADICTED,
        "claim-process-003": ValidationStatus.CONTRADICTED,
        "claim-process-004": ValidationStatus.INSUFFICIENT_EVIDENCE,
    }
