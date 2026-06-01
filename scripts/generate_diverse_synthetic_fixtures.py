"""Generate diversified synthetic validation fixtures for TraceBack tests.

The generated filenames encode expected validation outcomes:
<datatype>_<events|claims>.<size>.<scenario>-<records>-<supported>-<contradicted>-<insufficient>.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "tests" / "fixtures" / "diverse"

ACCOUNTS = [
    "mira_patton",
    "devon_reed",
    "sana_okafor",
    "eli_morales",
    "tessa_nguyen",
    "marco_ishikawa",
    "nora_kapoor",
    "owen_rivers",
    "lena_zhou",
    "mateo_silva",
    "ivana_petrova",
    "jamal_ellis",
    "kiara_bennett",
    "renata_cruz",
    "oscar_lind",
    "hana_mori",
]
HOSTS = [
    "WIN-ATLAS-01",
    "WIN-BIRCH-02",
    "WIN-CEDAR-03",
    "WIN-DELTA-04",
    "WIN-EMBER-05",
    "WIN-FJORD-06",
    "WIN-GROVE-07",
    "WIN-HARBOR-08",
]
TIMEZONES = ["Z", "-05:00", "+01:00", "+09:00", "-07:00", "+10:00"]
BROWSERS = ["Microsoft Edge", "Google Chrome", "Mozilla Firefox", "Chromium"]
URLS = [
    "https://example.net/inventory",
    "https://training.example.org/lab-notes",
    "https://portal.example.com/helpdesk",
    "https://kb.example.edu/reset-guide",
    "https://downloads.example.net/tools/viewer.zip",
    "https://docs.example.org/security-baseline",
]
PROCESSES = [
    "notepad.exe",
    "powershell.exe",
    "winword.exe",
    "teams.exe",
    "chrome.exe",
    "7zFM.exe",
    "calc.exe",
]
LOGON_TYPES = {
    2: "Interactive",
    3: "Network",
    10: "RemoteInteractive",
    11: "CachedInteractive",
}


@dataclass(frozen=True)
class Scenario:
    claim_type: str
    size: str
    label: str
    records: int
    supported: int
    contradicted: int
    insufficient: int

    @property
    def scenario_id(self) -> str:
        return f"{self.claim_type}.{self.size}.{self.label}-{self.records}-{self.supported}-{self.contradicted}-{self.insufficient}"

    @property
    def file_stem(self) -> str:
        return f"{self.claim_type}.{self.size}.{self.label}-{self.records}-{self.supported}-{self.contradicted}-{self.insufficient}"


SCENARIOS = [
    Scenario("windows_logon", "small", "zero-supported", 5, 0, 3, 2),
    Scenario("windows_logon", "large", "zero-insufficient", 24, 9, 15, 0),
    Scenario("windows_prefetch_process_execution", "small", "zero-contradicted", 6, 2, 0, 4),
    Scenario("windows_prefetch_process_execution", "large", "zero-supported", 30, 0, 12, 18),
    Scenario("browser_activity", "small", "mixed", 4, 1, 2, 1),
    Scenario("browser_activity", "large", "zero-insufficient", 40, 16, 24, 0),
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"scenarios": []}
    for scenario_index, scenario in enumerate(SCENARIOS):
        events, claims = build_records(scenario, scenario_index)
        events_file = f"{scenario.claim_type}_events.{scenario.size}.{scenario.label}-{scenario.records}-{scenario.supported}-{scenario.contradicted}-{scenario.insufficient}.json"
        claims_file = f"{scenario.claim_type}_claims.{scenario.size}.{scenario.label}-{scenario.records}-{scenario.supported}-{scenario.contradicted}-{scenario.insufficient}.json"
        write_json(OUTPUT_DIR / events_file, events)
        write_json(OUTPUT_DIR / claims_file, claims)
        manifest["scenarios"].append(
            {
                "scenario_id": scenario.scenario_id,
                "claim_type": scenario.claim_type,
                "size": scenario.size,
                "records_examined": scenario.records,
                "supported": scenario.supported,
                "contradicted": scenario.contradicted,
                "insufficient_evidence": scenario.insufficient,
                "events_file": events_file,
                "claims_file": claims_file,
                "purpose": "Diversify synthetic identities, timestamps, hosts, and result-count patterns for AI-assisted evaluation tests.",
            }
        )
    write_json(OUTPUT_DIR / "manifest.json", manifest)


def build_records(scenario: Scenario, scenario_index: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    outcomes = (
        ["supported"] * scenario.supported
        + ["contradicted"] * scenario.contradicted
        + ["insufficient"] * scenario.insufficient
    )
    events: list[dict[str, object]] = []
    claims: list[dict[str, object]] = []
    for record_index, outcome in enumerate(outcomes, start=1):
        absolute_index = scenario_index * 100 + record_index
        if scenario.claim_type == "windows_logon":
            event, claim = build_logon_pair(scenario, absolute_index, outcome)
        elif scenario.claim_type == "windows_prefetch_process_execution":
            event, claim = build_prefetch_pair(scenario, absolute_index, outcome)
        elif scenario.claim_type == "browser_activity":
            event, claim = build_browser_pair(scenario, absolute_index, outcome)
        else:
            raise ValueError(f"Unsupported scenario type: {scenario.claim_type}")
        events.append(event)
        claims.append(claim)
    return events, claims


def build_logon_pair(scenario: Scenario, index: int, outcome: str) -> tuple[dict[str, object], dict[str, object]]:
    account = account_for(index)
    host = host_for(index)
    timestamp = timestamp_for(index)
    expected_type = [2, 3, 10, 11][index % 4]
    observed_type = expected_type if outcome == "supported" else [3, 10, 11, 2][index % 4]
    expected_action = "logon_success"
    observed_action = expected_action if outcome != "contradicted" else "logon_failure"
    event_account = account if outcome != "insufficient" else account_for(index + 31)
    event_timestamp = timestamp if outcome != "insufficient" else timestamp_for(index + 37)
    event: dict[str, object] = {
        "event_uid": f"diverse-logon-{scenario.size}-{index:04d}",
        "event_type": "windows_logon",
        "host": host,
        "timestamp_utc": event_timestamp,
        "event_id": 4624 if observed_action == "logon_success" else 4625,
        "event_action": observed_action,
        "account": event_account,
        "logon_type": observed_type,
        "logon_type_label": LOGON_TYPES[observed_type],
        "source_timezone": timezone_for(index),
        "source_artifact": f"synthetic/security-{host.lower()}-{index:04d}.evtx",
        "synthetic": True,
    }
    claim: dict[str, object] = {
        "claim_id": f"claim-diverse-logon-{scenario.size}-{index:04d}",
        "claim_type": "windows_logon",
        "claim_text": f"{account} had a {LOGON_TYPES[expected_type]} Windows logon on {host} at {timestamp}.",
        "account": account,
        "host": host,
        "timestamp_utc": timestamp,
        "expected_event_action": expected_action,
        "expected_logon_type": expected_type,
        "expected_logon_type_label": LOGON_TYPES[expected_type],
        "source_timezone": timezone_for(index),
    }
    return event, claim


def build_prefetch_pair(scenario: Scenario, index: int, outcome: str) -> tuple[dict[str, object], dict[str, object]]:
    account = account_for(index)
    host = host_for(index)
    timestamp = timestamp_for(index)
    expected_process = PROCESSES[index % len(PROCESSES)]
    observed_process = expected_process if outcome == "supported" else PROCESSES[(index + 2) % len(PROCESSES)]
    observed_action = "process_executed" if outcome != "contradicted" else "prefetch_absent"
    event_account = account if outcome != "insufficient" else account_for(index + 29)
    event_timestamp = timestamp if outcome != "insufficient" else timestamp_for(index + 41)
    event: dict[str, object] = {
        "event_uid": f"diverse-prefetch-{scenario.size}-{index:04d}",
        "event_type": "windows_prefetch_process_execution",
        "host": host,
        "timestamp_utc": event_timestamp,
        "event_action": observed_action,
        "account": event_account,
        "process_name": observed_process,
        "process_path": f"C:/Program Files/Synthetic/{observed_process}",
        "source_artifact": f"synthetic/prefetch/{observed_process.upper()}-{index:04d}.pf",
        "artifact_type": "windows_prefetch",
        "parser_tool": "traceback_synthetic_prefetch_generator",
        "run_count": (index % 9) + 1,
        "source_timezone": timezone_for(index),
        "synthetic": True,
    }
    claim: dict[str, object] = {
        "claim_id": f"claim-diverse-prefetch-{scenario.size}-{index:04d}",
        "claim_type": "windows_prefetch_process_execution",
        "claim_text": f"{account} executed {expected_process} on {host} at {timestamp}.",
        "account": account,
        "host": host,
        "timestamp_utc": timestamp,
        "expected_event_action": "process_executed",
        "expected_process_name": expected_process,
        "source_timezone": timezone_for(index),
    }
    return event, claim


def build_browser_pair(scenario: Scenario, index: int, outcome: str) -> tuple[dict[str, object], dict[str, object]]:
    account = account_for(index)
    host = host_for(index)
    timestamp = timestamp_for(index)
    expected_url = URLS[index % len(URLS)]
    observed_url = expected_url if outcome == "supported" else URLS[(index + 3) % len(URLS)]
    expected_activity = "visit" if index % 3 else "download"
    observed_activity = expected_activity if outcome == "supported" else ("download" if expected_activity == "visit" else "visit")
    event_account = account if outcome != "insufficient" else account_for(index + 23)
    event_timestamp = timestamp if outcome != "insufficient" else timestamp_for(index + 43)
    event: dict[str, object] = {
        "event_uid": f"diverse-browser-{scenario.size}-{index:04d}",
        "event_type": "browser_activity",
        "artifact_type": "browser_history",
        "evidence_category": "browser_activity",
        "source": "synthetic_browser_history",
        "source_artifact": f"synthetic/browser/{host.lower()}-history-{index:04d}.sqlite",
        "parser_tool": "traceback_synthetic_browser_history_generator",
        "host": host,
        "timestamp_utc": event_timestamp,
        "event_action": "browser_activity_observed",
        "account": event_account,
        "user_context": f"profile:{event_account}",
        "activity_type": observed_activity,
        "browser": BROWSERS[index % len(BROWSERS)],
        "url": observed_url,
        "title": f"Synthetic page {index}",
        "download_name": f"tool-{index}.zip" if observed_activity == "download" else None,
        "source_timezone": timezone_for(index),
        "synthetic": True,
    }
    claim: dict[str, object] = {
        "claim_id": f"claim-diverse-browser-{scenario.size}-{index:04d}",
        "claim_type": "browser_activity",
        "claim_text": f"{account} performed browser activity at {expected_url} on {host} at {timestamp}.",
        "account": account,
        "host": host,
        "timestamp_utc": timestamp,
        "expected_event_action": "browser_activity_observed",
        "expected_activity_type": expected_activity,
        "expected_url": expected_url,
        "source_timezone": timezone_for(index),
    }
    return event, claim


def account_for(index: int) -> str:
    base = ACCOUNTS[index % len(ACCOUNTS)]
    return f"{base}_{index:03d}"


def host_for(index: int) -> str:
    return HOSTS[index % len(HOSTS)]


def timezone_for(index: int) -> str:
    return TIMEZONES[index % len(TIMEZONES)]


def timestamp_for(index: int) -> str:
    day = (index % 23) + 1
    hour = index % 24
    minute = (index * 7) % 60
    second = (index * 11) % 60
    timezone = timezone_for(index)
    if timezone == "Z":
        return f"2026-05-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"
    return f"2026-05-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}{timezone}"


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
