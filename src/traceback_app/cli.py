"""Command-line wrapper for the first TraceBack logon validation experiment."""

from __future__ import annotations

import argparse
from pathlib import Path

from traceback_app.evidence.loaders import load_json_records
from traceback_app.report.json_report import results_to_json
from traceback_app.report.markdown import results_to_markdown
from traceback_app.validators.logon import validate_logon_claims


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Validate synthetic Windows logon claims against normalized logon events."
    )
    parser.add_argument("--events", required=True, help="Path to normalized Windows logon events JSON.")
    parser.add_argument("--claims", required=True, help="Path to Windows logon claims JSON.")
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
    """Run the CLI wrapper. Validation logic stays in the core validator."""

    parser = build_parser()
    args = parser.parse_args(argv)

    events = load_json_records(args.events)
    claims = load_json_records(args.claims)
    results = validate_logon_claims(claims, events)

    print(results_to_markdown(results))

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.write_text(results_to_json(results) + "\n", encoding="utf-8")
        print(f"JSON report written to: {output_path}")

    if args.print_json:
        print(results_to_json(results))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
