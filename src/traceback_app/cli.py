"""Command-line wrapper for TraceBack deterministic validation experiments."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from traceback_app.claims.schema import ValidationResult
from traceback_app.evidence.loaders import load_json_records
from traceback_app.report.json_report import results_to_json
from traceback_app.report.markdown import results_to_markdown
from traceback_app.validators.logon import validate_logon_claims
from traceback_app.validators.prefetch_process import validate_prefetch_process_claims

ValidatorFn = Callable[[list[dict[str, object]], list[dict[str, object]]], list[ValidationResult]]

VALIDATORS: dict[str, tuple[ValidatorFn, str, str]] = {
    "logon": (
        validate_logon_claims,
        "TraceBack Windows Logon Validation Summary",
        "traceback_windows_logon_validation",
    ),
    "prefetch-process": (
        validate_prefetch_process_claims,
        "TraceBack Prefetch Process Validation Summary",
        "traceback_windows_prefetch_process_validation",
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
    parser.add_argument("--events", required=True, help="Path to normalized events JSON.")
    parser.add_argument("--claims", required=True, help="Path to claims JSON.")
    parser.add_argument(
        "--json-output",
        help="Optional path to save a machine-readable JSON validation report.",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Also print the machine-readable JSON validation report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI wrapper. Validation logic stays in core validators."""

    parser = build_parser()
    args = parser.parse_args(argv)

    validator, markdown_title, report_type = VALIDATORS[args.validator]
    events = load_json_records(args.events)
    claims = load_json_records(args.claims)
    results = validator(claims, events)

    print(results_to_markdown(results, title=markdown_title))

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.write_text(results_to_json(results, report_type=report_type) + "\n", encoding="utf-8")
        print(f"JSON report written to: {output_path}")

    if args.print_json:
        print(results_to_json(results, report_type=report_type))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
