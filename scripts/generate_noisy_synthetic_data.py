"""Generate larger noisy synthetic TraceBack fixture files.

The generated files keep the four repeatable base claims and their required
matching/contradicting evidence records, then add deterministic background noise
so the validator has to find the correct records in a larger evidence set.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path("/mnt/c/Users/Brandi Volpe/Markdown vaults/Find Evil Lab/Data created")
DEFAULT_SEED = 20260531

LOGON_EVENTS = "windows_logon_events.synthetic.json"
LOGON_CLAIMS = "windows_logon_claims.synthetic.json"
PREFETCH_EVENTS = "windows_prefetch_process_events.synthetic.json"
PREFETCH_CLAIMS = "windows_prefetch_process_claims.synthetic.json"

LARGE_LOGON_EVENTS = "windows_logon_events.large.synthetic.json"
LARGE_LOGON_CLAIMS = "windows_logon_claims.large.synthetic.json"
LARGE_PREFETCH_EVENTS = "windows_prefetch_process_events.large.synthetic.json"
LARGE_PREFETCH_CLAIMS = "windows_prefetch_process_claims.large.synthetic.json"


def generate_all(
    *,
    input_dir: str | Path = DEFAULT_DATA_DIR,
    output_dir: str | Path = DEFAULT_DATA_DIR,
    logon_noise_count: int = 250,
    prefetch_noise_count: int = 250,
    seed: int = DEFAULT_SEED,
) -> dict[str, Path]:
    """Generate noisy large fixtures from the small repeatable base fixtures."""

    source_dir = Path(input_dir)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    logon_events = _load_json(source_dir / LOGON_EVENTS)
    logon_claims = _load_json(source_dir / LOGON_CLAIMS)
    prefetch_events = _load_json(source_dir / PREFETCH_EVENTS)
    prefetch_claims = _load_json(source_dir / PREFETCH_CLAIMS)

    rng = random.Random(seed)
    large_logon_events = [*logon_events, *_generate_logon_noise(logon_claims, logon_noise_count, rng)]
    large_prefetch_events = [
        *prefetch_events,
        *_generate_prefetch_noise(prefetch_claims, prefetch_noise_count, rng),
    ]
    rng.shuffle(large_logon_events)
    rng.shuffle(large_prefetch_events)

    output_paths = {
        "logon_events": target_dir / LARGE_LOGON_EVENTS,
        "logon_claims": target_dir / LARGE_LOGON_CLAIMS,
        "prefetch_events": target_dir / LARGE_PREFETCH_EVENTS,
        "prefetch_claims": target_dir / LARGE_PREFETCH_CLAIMS,
    }

    _write_json(output_paths["logon_events"], large_logon_events)
    _write_json(output_paths["logon_claims"], logon_claims)
    _write_json(output_paths["prefetch_events"], large_prefetch_events)
    _write_json(output_paths["prefetch_claims"], prefetch_claims)

    return output_paths


def _generate_logon_noise(
    claims: list[dict[str, Any]], count: int, rng: random.Random
) -> list[dict[str, Any]]:
    protected = _protected_claim_keys(claims)
    accounts = [
        "addie_smith",
        "brandon_admin",
        "LOCAL SERVICE",
        "NETWORK SERVICE",
        "svc_backup",
        "svc_update",
        "case_reviewer",
        "helpdesk_temp",
    ]
    hosts = ["WIN-FORENSIC-01", "WIN-FORENSIC-02", "LAB-DC-01", "EVIDENCE-WS-03"]
    event_shapes = [
        (4624, "logon_success", 2, "Interactive"),
        (4624, "logon_success", 3, "Network"),
        (4624, "logon_success", 5, "Service"),
        (4624, "logon_success", 10, "RemoteInteractive"),
        (4625, "logon_failure", 2, "Interactive"),
        (4625, "logon_failure", 3, "Network"),
        (4634, "logoff_success", 3, "Network"),
        (4672, "special_privileges_assigned", None, None),
    ]
    start = datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc)

    records: list[dict[str, Any]] = []
    attempts = 0
    while len(records) < count:
        attempts += 1
        if attempts > count * 20:
            raise RuntimeError("Could not generate enough safe logon noise records.")

        timestamp = _timestamp(start, rng.randrange(0, 5 * 24 * 60), rng.randrange(0, 60))
        account = rng.choice(accounts)
        host = rng.choice(hosts)
        if (account, host, timestamp) in protected:
            continue

        event_id, event_action, logon_type, logon_type_label = rng.choice(event_shapes)
        index = len(records) + 1
        records.append(
            {
                "event_uid": f"synthetic-logon-noise-{index:04d}",
                "event_type": "windows_logon",
                "source": "synthetic_windows_security_log_noise",
                "source_file": "SYNTHETIC-Security-noisy.evtx",
                "host": host,
                "timestamp_utc": timestamp,
                "event_id": event_id,
                "event_action": event_action,
                "account": account,
                "domain": "WIN-FORENSIC-01" if account not in {"LOCAL SERVICE", "NETWORK SERVICE"} else "NT AUTHORITY",
                "sid": None,
                "logon_type": logon_type,
                "logon_type_label": logon_type_label,
                "authentication_package": rng.choice(["Negotiate", "NTLM", "Kerberos", None]),
                "logon_process": rng.choice(["User32", "NtLmSsp", "Advapi", None]),
                "source_ip": rng.choice([None, "192.0.2.25", "198.51.100.42", "203.0.113.77"]),
                "workstation_name": rng.choice([host, "FORENSIC-LAB-PC", "LAPTOP-ADDIE", None]),
                "record_id": 200000 + index,
                "synthetic": True,
                "noise_record": True,
                "notes": "Deterministic noisy background event for large fixture testing.",
            }
        )
    return records


def _generate_prefetch_noise(
    claims: list[dict[str, Any]], count: int, rng: random.Random
) -> list[dict[str, Any]]:
    protected = _protected_claim_keys(claims)
    accounts = [
        "addie_smith",
        "brandon_admin",
        "svc_backup",
        "svc_update",
        "case_reviewer",
        "helpdesk_temp",
    ]
    hosts = ["WIN-FORENSIC-01", "WIN-FORENSIC-02", "LAB-DC-01", "EVIDENCE-WS-03"]
    processes = [
        ("explorer.exe", "C:\\Windows\\explorer.exe"),
        ("svchost.exe", "C:\\Windows\\System32\\svchost.exe"),
        ("conhost.exe", "C:\\Windows\\System32\\conhost.exe"),
        ("cmd.exe", "C:\\Windows\\System32\\cmd.exe"),
        ("notepad.exe", "C:\\Windows\\System32\\notepad.exe"),
        ("calc.exe", "C:\\Windows\\System32\\calc.exe"),
        ("powershell.exe", "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"),
        ("powershell_ise.exe", "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell_ise.exe"),
        ("pwsh.exe", "C:\\Program Files\\PowerShell\\7\\pwsh.exe"),
        ("mmc.exe", "C:\\Windows\\System32\\mmc.exe"),
        ("msedge.exe", "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"),
        ("msedgewebview2.exe", "C:\\Program Files (x86)\\Microsoft\\EdgeWebView\\Application\\msedgewebview2.exe"),
    ]
    start = datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc)

    records: list[dict[str, Any]] = []
    attempts = 0
    while len(records) < count:
        attempts += 1
        if attempts > count * 20:
            raise RuntimeError("Could not generate enough safe Prefetch noise records.")

        timestamp = _timestamp(start, rng.randrange(0, 5 * 24 * 60), rng.randrange(0, 60))
        account = rng.choice(accounts)
        host = rng.choice(hosts)
        if (account, host, timestamp) in protected:
            continue

        process_name, process_path = rng.choice(processes)
        index = len(records) + 1
        prefetch_stem = process_name.upper().replace(".", "")[:18]
        records.append(
            {
                "event_uid": f"synthetic-prefetch-process-noise-{index:04d}",
                "event_type": "windows_prefetch_process_execution",
                "artifact_type": "windows_prefetch",
                "evidence_category": "process_execution",
                "source": "synthetic_windows_prefetch_noise",
                "source_artifact": f"C:\\Windows\\Prefetch\\{prefetch_stem}-{rng.randrange(0x10000000, 0xFFFFFFFF):08X}.pf",
                "parser_tool": "synthetic_normalized_prefetch",
                "host": host,
                "timestamp_utc": timestamp,
                "event_action": rng.choice(["process_executed", "process_executed", "process_executed", "prefetch_absent"]),
                "account": account,
                "user_context": f"inferred:{account}",
                "process_name": process_name,
                "process_path": process_path,
                "run_count": rng.randrange(0, 9),
                "synthetic": True,
                "noise_record": True,
                "notes": "Deterministic noisy background Prefetch-style event for large fixture testing.",
            }
        )
    return records


def _protected_claim_keys(claims: list[dict[str, Any]]) -> set[tuple[Any, Any, Any]]:
    return {(claim.get("account"), claim.get("host"), claim.get("timestamp_utc")) for claim in claims}


def _timestamp(start: datetime, minutes: int, seconds: int) -> str:
    return (start + timedelta(minutes=minutes, seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError(f"Expected {path} to contain a JSON array of objects.")
    return data


def _write_json(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate noisy synthetic TraceBack fixture files.")
    parser.add_argument("--input-dir", default=str(DEFAULT_DATA_DIR), help="Directory containing small base fixture files.")
    parser.add_argument("--output-dir", default=str(DEFAULT_DATA_DIR), help="Directory to write large noisy fixture files.")
    parser.add_argument("--logon-noise-count", type=int, default=250, help="Number of logon noise records to add.")
    parser.add_argument("--prefetch-noise-count", type=int, default=250, help="Number of Prefetch process noise records to add.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Deterministic random seed.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    generated = generate_all(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        logon_noise_count=args.logon_noise_count,
        prefetch_noise_count=args.prefetch_noise_count,
        seed=args.seed,
    )
    for label, path in generated.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
