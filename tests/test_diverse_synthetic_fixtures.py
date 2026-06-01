import json
import re
from collections import Counter
from pathlib import Path

from traceback_app.claims.schema import ValidationStatus
from traceback_app.evidence.loaders import (
    BROWSER_ACTIVITY_CLAIM_SCHEMA,
    BROWSER_ACTIVITY_EVENT_SCHEMA,
    LOGON_CLAIM_SCHEMA,
    LOGON_EVENT_SCHEMA,
    PREFETCH_PROCESS_CLAIM_SCHEMA,
    PREFETCH_PROCESS_EVENT_SCHEMA,
    load_json_records,
)
from traceback_app.validators.browser_activity import validate_browser_activity_claims
from traceback_app.validators.logon import validate_logon_claims
from traceback_app.validators.prefetch_process import validate_prefetch_process_claims

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIVERSE_FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "diverse"
COUNT_PATTERN = re.compile(r"-(?P<records>\d+)-(?P<supported>\d+)-(?P<contradicted>\d+)-(?P<insufficient>\d+)\.json$")

VALIDATOR_CONFIGS = {
    "windows_logon": (
        LOGON_EVENT_SCHEMA,
        LOGON_CLAIM_SCHEMA,
        validate_logon_claims,
    ),
    "windows_prefetch_process_execution": (
        PREFETCH_PROCESS_EVENT_SCHEMA,
        PREFETCH_PROCESS_CLAIM_SCHEMA,
        validate_prefetch_process_claims,
    ),
    "browser_activity": (
        BROWSER_ACTIVITY_EVENT_SCHEMA,
        BROWSER_ACTIVITY_CLAIM_SCHEMA,
        validate_browser_activity_claims,
    ),
}

EXPECTED_SCENARIOS = {
    "windows_logon.small.zero-supported-5-0-3-2",
    "windows_logon.large.zero-insufficient-24-9-15-0",
    "windows_prefetch_process_execution.small.zero-contradicted-6-2-0-4",
    "windows_prefetch_process_execution.large.zero-supported-30-0-12-18",
    "browser_activity.small.mixed-4-1-2-1",
    "browser_activity.large.zero-insufficient-40-16-24-0",
}


def test_diverse_fixture_manifest_lists_all_expected_scenarios():
    manifest = json.loads((DIVERSE_FIXTURES / "manifest.json").read_text(encoding="utf-8"))

    scenario_ids = {scenario["scenario_id"] for scenario in manifest["scenarios"]}

    assert scenario_ids == EXPECTED_SCENARIOS
    for scenario in manifest["scenarios"]:
        assert scenario["records_examined"] == (
            scenario["supported"]
            + scenario["contradicted"]
            + scenario["insufficient_evidence"]
        )
        assert "addie_smith" not in json.dumps(scenario).casefold()


def test_diverse_fixture_filenames_encode_expected_validation_counts():
    manifest = json.loads((DIVERSE_FIXTURES / "manifest.json").read_text(encoding="utf-8"))

    for scenario in manifest["scenarios"]:
        events_path = DIVERSE_FIXTURES / scenario["events_file"]
        claims_path = DIVERSE_FIXTURES / scenario["claims_file"]
        event_schema, claim_schema, validator = VALIDATOR_CONFIGS[scenario["claim_type"]]

        expected_from_events_name = _counts_from_filename(events_path)
        expected_from_claims_name = _counts_from_filename(claims_path)
        expected_counts = {
            "records": scenario["records_examined"],
            "supported": scenario["supported"],
            "contradicted": scenario["contradicted"],
            "insufficient": scenario["insufficient_evidence"],
        }

        assert expected_from_events_name == expected_counts
        assert expected_from_claims_name == expected_counts

        events = load_json_records(events_path, schema=event_schema)
        claims = load_json_records(claims_path, schema=claim_schema)
        results = validator(claims, events)
        status_counts = Counter(result.status for result in results)

        assert len(events) == scenario["records_examined"]
        assert len(claims) == scenario["records_examined"]
        assert status_counts[ValidationStatus.SUPPORTED] == scenario["supported"]
        assert status_counts[ValidationStatus.CONTRADICTED] == scenario["contradicted"]
        assert (
            status_counts[ValidationStatus.INSUFFICIENT_EVIDENCE]
            == scenario["insufficient_evidence"]
        )


def test_diverse_fixtures_use_varied_identities_hosts_and_timezones():
    accounts = set()
    hosts = set()
    timezone_offsets = set()

    for path in DIVERSE_FIXTURES.glob("*.json"):
        if path.name == "manifest.json":
            continue
        text = path.read_text(encoding="utf-8")
        assert "addie_smith" not in text.casefold()
        for record in json.loads(text):
            if "account" in record:
                accounts.add(record["account"])
            if "host" in record:
                hosts.add(record["host"])
            timestamp = record.get("timestamp_utc", "")
            if timestamp.endswith("Z"):
                timezone_offsets.add("Z")
            elif len(timestamp) >= 6:
                timezone_offsets.add(timestamp[-6:])

    assert len(accounts) >= 12
    assert len(hosts) >= 6
    assert {"Z", "-05:00", "+01:00", "+09:00"}.issubset(timezone_offsets)


def _counts_from_filename(path: Path) -> dict[str, int]:
    match = COUNT_PATTERN.search(path.name)
    assert match is not None, f"Filename does not end with count suffix: {path.name}"
    return {key: int(value) for key, value in match.groupdict().items()}
