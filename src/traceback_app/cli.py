"""Command-line wrapper for TraceBack deterministic validation experiments."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from zoneinfo import available_timezones

from traceback_app.claims.schema import ValidationResult
from traceback_app.evidence.loaders import (
    BROWSER_ACTIVITY_CLAIM_SCHEMA,
    BROWSER_ACTIVITY_EVENT_SCHEMA,
    LOGON_CLAIM_SCHEMA,
    LOGON_EVENT_SCHEMA,
    PREFETCH_PROCESS_CLAIM_SCHEMA,
    PREFETCH_PROCESS_EVENT_SCHEMA,
    RecordSchema,
    SourceDataError,
    load_json_records,
)
from traceback_app.report.json_report import results_to_json
from traceback_app.report.markdown import results_to_markdown
from traceback_app.validators.browser_activity import validate_browser_activity_claims
from traceback_app.validators.logon import validate_logon_claims
from traceback_app.validators.prefetch_process import validate_prefetch_process_claims

ValidatorFn = Callable[[list[dict[str, object]], list[dict[str, object]]], list[ValidationResult]]

ValidatorConfig = tuple[ValidatorFn, str, str, RecordSchema, RecordSchema]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BROWSER_ACTIVITY_DEMO = {
    "validator": "browser-activity",
    "database_artifact": PROJECT_ROOT / "tests/fixtures/small/browser_activity.synthetic.sqlite",
    "events": PROJECT_ROOT / "tests/fixtures/small/browser_activity_events.synthetic.json",
    "claims": PROJECT_ROOT / "tests/fixtures/small/browser_activity_claims.synthetic.json",
    "metadata": PROJECT_ROOT / "tests/fixtures/small/browser_activity_events.synthetic.metadata.json",
}
DEMOS = {"browser-activity": BROWSER_ACTIVITY_DEMO}

VALIDATORS: dict[str, ValidatorConfig] = {
    "logon": (
        validate_logon_claims,
        "TraceBack Windows Logon Validation Summary",
        "traceback_windows_logon_validation",
        LOGON_EVENT_SCHEMA,
        LOGON_CLAIM_SCHEMA,
    ),
    "prefetch-process": (
        validate_prefetch_process_claims,
        "TraceBack Prefetch Process Validation Summary",
        "traceback_windows_prefetch_process_validation",
        PREFETCH_PROCESS_EVENT_SCHEMA,
        PREFETCH_PROCESS_CLAIM_SCHEMA,
    ),
    "browser-activity": (
        validate_browser_activity_claims,
        "TraceBack Browser Activity Validation Summary",
        "traceback_browser_activity_validation",
        BROWSER_ACTIVITY_EVENT_SCHEMA,
        BROWSER_ACTIVITY_CLAIM_SCHEMA,
    ),
}


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Validate synthetic TraceBack claims against normalized evidence."
    )
    parser.add_argument(
        "--validator",
        choices=sorted(VALIDATORS),
        default="logon",
        help="Validation experiment to run. Defaults to logon.",
    )
    parser.add_argument(
        "--demo",
        choices=sorted(DEMOS),
        help=(
            "Run a built-in demo with database-derived JSON evidence and "
            "assertion/assumption claims."
        ),
    )
    parser.add_argument("--events", help="Path to normalized events JSON.")
    parser.add_argument("--claims", help="Path to claims/assertions JSON.")
    parser.add_argument(
        "--metadata",
        help="Optional path to sidecar provenance metadata JSON for the normalized events file.",
    )
    parser.add_argument(
        "--json-output",
        help="Optional path to save a machine-readable JSON validation report.",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Also print the machine-readable JSON validation report.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print the human-readable Markdown validation report preview.",
    )
    parser.add_argument(
        "--list-timezones",
        action="store_true",
        help="Print available IANA timezone names for report/export timestamps, then exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI wrapper. Validation logic stays in core validators."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_timezones:
        _print_available_timezones()
        return 0
    _apply_demo_defaults(args)

    if not args.events or not args.claims:
        parser.error("--events and --claims are required unless --demo is supplied")

    validator, markdown_title, report_type, event_schema, claim_schema = VALIDATORS[
        args.validator
    ]
    try:
        events = load_json_records(args.events, schema=event_schema)
        claims = load_json_records(args.claims, schema=claim_schema)
        provenance_metadata = (
            _load_provenance_metadata(args.metadata) if args.metadata else None
        )
    except SourceDataError as exc:
        print("Could not load source data.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2

    results = validator(claims, events)

    if args.demo:
        _print_demo_inputs(args.demo, args)

    should_print_markdown_preview = args.preview or (
        not args.json_output and not args.print_json
    )
    if should_print_markdown_preview:
        print(
            results_to_markdown(
                results,
                title=markdown_title,
                provenance_metadata=provenance_metadata,
            )
        )

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            results_to_json(
                results,
                report_type=report_type,
                provenance_metadata=provenance_metadata,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"JSON report written to: {output_path}")

    if args.print_json:
        print(
            results_to_json(
                results,
                report_type=report_type,
                provenance_metadata=provenance_metadata,
            )
        )

    return 0


def _print_available_timezones() -> None:
    print("UTC")
    for timezone_name in sorted(name for name in available_timezones() if name != "UTC"):
        print(timezone_name)


def _apply_demo_defaults(args: argparse.Namespace) -> None:
    if not args.demo:
        return

    demo = DEMOS[args.demo]
    args.validator = demo["validator"]
    args.events = args.events or demo["events"]
    args.claims = args.claims or demo["claims"]
    args.metadata = args.metadata or demo["metadata"]


def _print_demo_inputs(demo_name: str, args: argparse.Namespace) -> None:
    demo = DEMOS[demo_name]
    print("TraceBack browser activity demo")
    print("This demo evaluates database-derived JSON evidence against an assertion/assumption file.")
    print(f"- Database artifact: {demo['database_artifact']}")
    print(f"- Normalized JSON evidence: {args.events}")
    print(f"- Assertion/assumption file: {args.claims}")
    print(f"- Evidence provenance metadata: {args.metadata}")
    print("")


def _load_provenance_metadata(path: str | Path) -> dict[str, Any]:
    metadata_path = Path(path)
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise SourceDataError(
            metadata_path,
            "Could not load provenance metadata",
            "The sidecar metadata JSON file was not found.",
            "Check the metadata path or regenerate the normalized records with sidecar metadata.",
        ) from exc
    except IsADirectoryError as exc:
        raise SourceDataError(
            metadata_path,
            "Could not load provenance metadata",
            "Expected a sidecar metadata JSON file, but the supplied path is a directory.",
            "Choose the specific .metadata.json file for the normalized evidence records.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise SourceDataError(
            metadata_path,
            "Could not load provenance metadata",
            f"Could not parse JSON at line {exc.lineno}, column {exc.colno}.",
            "Verify the sidecar metadata file or regenerate it from the source artifact.",
        ) from exc

    if not isinstance(data, dict):
        raise SourceDataError(
            metadata_path,
            "Could not load provenance metadata",
            "Expected a JSON object containing sidecar metadata fields.",
            "Use the .metadata.json file generated alongside the normalized evidence records.",
        )
    return data


if __name__ == "__main__":
    raise SystemExit(main())
