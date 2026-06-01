# Browser Activity Evidence Demo

This demo shows TraceBack evaluating database-derived JSON evidence against a separate assertion/assumption file.

## Inputs

- Database artifact: `tests/fixtures/small/browser_activity.synthetic.sqlite`
- Normalized JSON evidence extracted from that database: `tests/fixtures/small/browser_activity_events.synthetic.json`
- Assertion/assumption file: `tests/fixtures/small/browser_activity_claims.synthetic.json`
- Evidence provenance sidecar: `tests/fixtures/small/browser_activity_events.synthetic.metadata.json`

## Run the demo

From the repository root:

```bash
PYTHONPATH=src python3 -m traceback_app.cli --demo browser-activity --json-output reports/browser-activity-demo-report.json
```

What to look for:

- `claim-browser-001` should be `supported`.
- `claim-browser-002` should be `contradicted` because the assertion names a different URL than the matching browser evidence.
- `claim-browser-003` should be `contradicted` because the assertion says `download`, but the evidence shows a `visit`.
- `claim-browser-004` should be `insufficient_evidence` because no matching browser event exists for that account, host, and timestamp.

The JSON report is written to:

```text
reports/browser-activity-demo-report.json
```

The report includes `evidence_provenance` so the validation result stays tied back to the source database artifact and normalized JSON evidence.
