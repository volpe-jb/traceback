import json
from pathlib import Path

from traceback_app import cli

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_cli_browser_activity_demo_writes_json_report_without_markdown_preview_by_default(capsys, tmp_path):
    output_path = tmp_path / "reports" / "browser-activity-demo-report.json"

    exit_code = cli.main(
        [
            "--demo",
            "browser-activity",
            "--json-output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(output_path.read_text(encoding="utf-8"))
    statuses = {result["claim_id"]: result["status"] for result in report["results"]}

    assert exit_code == 0
    assert "TraceBack browser activity demo" in captured.out
    assert "Database artifact:" in captured.out
    assert "Normalized JSON evidence:" in captured.out
    assert "Assertion/assumption file:" in captured.out
    assert "browser_activity.synthetic.sqlite" in captured.out
    assert "browser_activity_events.synthetic.json" in captured.out
    assert "browser_activity_claims.synthetic.json" in captured.out
    assert "JSON report written to:" in captured.out
    assert "## Evidence provenance" not in captured.out
    assert "# TraceBack Browser Activity Validation Summary" not in captured.out
    assert statuses == {
        "claim-browser-001": "supported",
        "claim-browser-002": "contradicted",
        "claim-browser-003": "contradicted",
        "claim-browser-004": "insufficient_evidence",
    }
    assert report["evidence_provenance"]["source_artifact"].endswith(
        "browser_activity.synthetic.sqlite"
    )


def test_cli_preview_flag_prints_markdown_validation_report(capsys, tmp_path):
    output_path = tmp_path / "reports" / "browser-activity-demo-report.json"

    exit_code = cli.main(
        [
            "--demo",
            "browser-activity",
            "--json-output",
            str(output_path),
            "--preview",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# TraceBack Browser Activity Validation Summary" in captured.out
    assert "## Evidence provenance" in captured.out
