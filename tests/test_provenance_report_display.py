import json
from pathlib import Path

from traceback_app import cli
from traceback_app.evidence.loaders import (
    BROWSER_ACTIVITY_CLAIM_SCHEMA,
    BROWSER_ACTIVITY_EVENT_SCHEMA,
    load_json_records,
)
from traceback_app.report.json_report import results_to_dict
from traceback_app.report.markdown import results_to_markdown
from traceback_app.validators.browser_activity import validate_browser_activity_claims

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMALL_FIXTURE_DATA = PROJECT_ROOT / "tests" / "fixtures" / "small"
EVENTS_PATH = SMALL_FIXTURE_DATA / "browser_activity_events.synthetic.json"
CLAIMS_PATH = SMALL_FIXTURE_DATA / "browser_activity_claims.synthetic.json"
METADATA_PATH = SMALL_FIXTURE_DATA / "browser_activity_events.synthetic.metadata.json"


def _browser_results():
    events = load_json_records(EVENTS_PATH, schema=BROWSER_ACTIVITY_EVENT_SCHEMA)
    claims = load_json_records(CLAIMS_PATH, schema=BROWSER_ACTIVITY_CLAIM_SCHEMA)
    return validate_browser_activity_claims(claims, events)


def test_markdown_report_includes_compact_evidence_provenance_when_metadata_is_supplied():
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    markdown = results_to_markdown(
        _browser_results(),
        title="TraceBack Browser Activity Validation Summary",
        provenance_metadata=metadata,
    )

    assert "## Evidence provenance" in markdown
    assert f"- Source artifact: {metadata['source_artifact']}" in markdown
    assert f"- Source SHA-256: {metadata['source_sha256']}" in markdown
    assert f"- Normalized records: {metadata['normalized_file']}" in markdown
    assert f"- Normalized SHA-256: {metadata['normalized_sha256']}" in markdown
    assert (
        f"- Parser/extractor: {metadata['parser_tool']} "
        f"(version {metadata['parser_tool_version']})"
        in markdown
    )
    assert f"- Records validated: {metadata['record_count']}" in markdown


def test_json_report_includes_evidence_provenance_when_metadata_is_supplied():
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    report = results_to_dict(
        _browser_results(),
        report_type="traceback_browser_activity_validation",
        provenance_metadata=metadata,
    )

    assert report["evidence_provenance"] == metadata


def test_cli_can_run_browser_activity_validator_and_print_metadata_provenance(capsys):
    exit_code = cli.main(
        [
            "--validator",
            "browser-activity",
            "--events",
            str(EVENTS_PATH),
            "--claims",
            str(CLAIMS_PATH),
            "--metadata",
            str(METADATA_PATH),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "TraceBack Browser Activity Validation Summary" in captured.out
    assert "## Evidence provenance" in captured.out
    assert "- Source artifact:" in captured.out
    assert "- Normalized records:" in captured.out
    assert "- Parser/extractor: traceback_chromium_history_sqlite_extractor" in captured.out
    assert "claim-browser-001" in captured.out


def test_cli_json_output_includes_metadata_provenance(tmp_path):
    output_path = tmp_path / "browser-report.json"

    exit_code = cli.main(
        [
            "--validator",
            "browser-activity",
            "--events",
            str(EVENTS_PATH),
            "--claims",
            str(CLAIMS_PATH),
            "--metadata",
            str(METADATA_PATH),
            "--json-output",
            str(output_path),
        ]
    )

    report = json.loads(output_path.read_text(encoding="utf-8"))
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert report["report_type"] == "traceback_browser_activity_validation"
    assert report["evidence_provenance"] == metadata
