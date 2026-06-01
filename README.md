# TraceBack: Evidence Validation for AI-Assisted DFIR

TraceBack is a local-first Python experiment for checking AI-style forensic claims against normalized evidence records.

The goal is simple: if an AI assistant says something happened, TraceBack checks whether the evidence supports it, contradicts it, or does not contain enough information to prove it.

The current app keeps deterministic validation at the center. The CLI is the reproducible workflow door, and the optional Streamlit GUI is a thin review/demo door over the same local validation path. Agent/LLM workflows can be added around it later, but the validation core should remain independently testable and runnable without API keys.

The current validation path runs locally and does not require API keys.

## Current MVP scope

TraceBack currently validates claims across three evidence types:

1. Windows logon activity
2. Windows Prefetch process execution
3. Browser activity from Chromium-family history data

Current browser support is intentionally limited to Chromium-family normalized browser activity records, such as:

- Microsoft Edge
- Google Chrome
- Chromium

Firefox is not currently supported in the CLI fixture generator or browser extractor path. Firefox support is future scope and should be added only after TraceBack has a matching `places.sqlite` parser/extractor path that normalizes Firefox history into the existing browser activity record shape.

## Validation status meanings

TraceBack uses three deterministic validation statuses:

- `supported`: Matching evidence exists and agrees with the claim.
- `contradicted`: Matching evidence exists, but one or more fields conflict with the claim.
- `insufficient_evidence`: No matching evidence was found for the claim. In the GUI, this is shown as `unsupported / insufficient evidence` for plainer review wording.

Important distinction: a claim is not `insufficient_evidence` just because the evidence says an expected event was absent. If TraceBack finds a matching normalized evidence record for the same key fields, and that record says the expected event did not occur, the claim is `contradicted`.

Example:

A claim says:

```text
addie_smith executed powershell.exe on WIN-FORENSIC-01 at 2026-05-20T14:18:42Z
```

The matching normalized Prefetch record says:

```text
event_action=prefetch_absent
```

TraceBack marks this as `contradicted` because matching evidence exists and conflicts with the claim. This is contradicted rather than unsupported.

## What TraceBack outputs

For each claim, TraceBack returns one of three validation statuses:

- `supported` — matching evidence supports the claim
- `contradicted` — matching evidence exists, but it conflicts with the claim
- `insufficient_evidence` — no matching evidence was found for the claim

The CLI prints a Markdown report when no output option is supplied, can save JSON with `--json-output`, can print JSON with `--print-json`, and can show the human-readable Markdown preview explicitly with `--preview`. The Streamlit GUI can view or download the same kind of validation report for the bundled demo case.

## Repository layout

```text
src/traceback_app/          Core app package
src/traceback_app/cli.py    CLI entry point
src/traceback_app/gui/      Thin Streamlit GUI adapter layer
src/traceback_app/validators/
                            Evidence-type validators
tests/                      Automated tests
tests/fixtures/             Small, large, malformed, and diverse fixtures
scripts/                    Deterministic fixture-generation scripts
streamlit_app.py            Streamlit review/demo GUI entry point
```

## Requirements

- Python 3.10+
- `uv` for the test commands shown below

Runtime dependencies are managed in `pyproject.toml`. The optional review/demo GUI uses Streamlit. Tests use `pytest` through `uv`.

## Run the tests

From the repo root:

```bash
UV_LINK_MODE=copy uv run --with pytest pytest -q
```

Expected current result:

```text
87 passed
```

To run only the diverse synthetic fixture tests:

```bash
UV_LINK_MODE=copy uv run --with pytest pytest tests/test_diverse_synthetic_fixtures.py -q
```

## Run a validation from the CLI

Use `PYTHONPATH=src` when running the package directly from the source tree.

Example: browser activity validation with the small diverse fixture set:

```bash
PYTHONPATH=src python3 -m traceback_app.cli \
  --validator browser-activity \
  --events tests/fixtures/diverse/browser_activity_events.small.mixed-4-1-2-1.json \
  --claims tests/fixtures/diverse/browser_activity_claims.small.mixed-4-1-2-1.json \
  --print-json
```

Validator choices:

```text
logon
prefetch-process
browser-activity
```

## Run the Streamlit review GUI

The Streamlit GUI is a judge-friendly review/demo interface, not a replacement for the deterministic CLI or validation core.

From the repo root:

```bash
UV_LINK_MODE=copy uv run streamlit run streamlit_app.py
```

Then open the local URL Streamlit prints. It usually looks like:

```text
Local URL: http://localhost:8501
Network URL: http://<wsl-or-host-ip>:8501
```

Use the `Local URL` when you are opening the GUI from the same machine where Streamlit is running. In WSL, this usually works from the Windows browser too:

```text
http://localhost:8501
```

Use the `Network URL` when you need to open the GUI from another device or from a browser that cannot reach `localhost`. Replace `<wsl-or-host-ip>` with the IP address Streamlit prints, for example:

```text
http://172.18.59.78:8501
```

If the browser cannot connect, stop Streamlit with `Ctrl+C`, restart it, and use the fresh URL shown in the terminal.

## Demo workflow for judges

1. Start the Streamlit review GUI.
2. Select one of the bundled demo dataset pairs.
3. Run deterministic validation.
4. Review the validation summary and result callouts for supported, contradicted, and unsupported / insufficient evidence claims.
5. Review the expected-vs-observed evidence details for contradicted claims.
6. Download the Markdown or JSON report, or use Print / Save as PDF for a browser-generated PDF copy.
7. Return to the top of the UI and pick another dataset to evaluate.

GUI v0 currently lets you:

- select an evidence type:
  - Logon evidence
  - Process execution evidence
  - Browser activity evidence
- select a specific evidence file with its paired claims/assertions file
- choose small synthetic, large noisy synthetic, and generated diverse fixture pairs where available
- view the selected claim/assertion set
- run deterministic validation
- review evidence checks grouped by type
- view `supported`, `contradicted`, and plain-language `unsupported / insufficient evidence` labels
- see a status explainer that distinguishes contradicted from unsupported results
- see colored result callouts:
  - green for supported
  - red for contradicted
  - blue/info for unsupported / insufficient evidence
- review compact evidence provenance when sidecar metadata is available
- expand the full sidecar metadata JSON
- view compact, print-friendly evidence references
- view the full validation report preview only when needed
- download Markdown and JSON validation reports
- use fixed-size report controls for Markdown, JSON, and browser Print / Save as PDF

The GUI does not call an LLM, does not require an API key, and does not implement the future AI reviewer loop.

The Streamlit GUI is intentionally concise for demo and judging use. It emphasizes status callouts, expected-vs-observed evidence details, compact provenance, and exportable reports rather than exposing every internal validation detail by default.

## Report outputs

TraceBack can produce:

- Markdown validation reports
- JSON validation reports
- browser-generated PDF output from the Streamlit print view

The PDF path uses the browser print dialog rather than a separate PDF-generation dependency.

## Diverse synthetic fixtures

The `tests/fixtures/diverse/` folder contains generated fixture pairs for the three current validators.

Each filename encodes the expected validation counts:

```text
<claim_type>_<events|claims>.<size>.<scenario>-<records>-<supported>-<contradicted>-<insufficient>.json
```

Example:

```text
browser_activity_events.small.mixed-4-1-2-1.json
```

This means TraceBack should examine 4 browser activity claims and produce:

```text
1 supported
2 contradicted
1 insufficient_evidence
```

Regenerate the diverse fixtures with:

```bash
python3 scripts/generate_diverse_synthetic_fixtures.py
```

Then verify them with:

```bash
UV_LINK_MODE=copy uv run --with pytest pytest tests/test_diverse_synthetic_fixtures.py -q
```

## Evidence model

TraceBack separates forensic source artifacts from normalized validation records.

The intended flow is:

```text
raw/source artifact
        -> extractor or parser
        -> normalized JSON records
        -> TraceBack validator
        -> supported / contradicted / insufficient_evidence result
```

Normalized JSON is the working validation format. It is not a replacement for the original forensic artifact.

For browser activity, the current source-artifact path is Chromium/Edge-style History SQLite data with `urls` and `visits` tables. Other browser formats should be handled by browser-specific extractors later.

## Evidence provenance and sidecar metadata

When a converter/parser creates normalized TraceBack JSON, it can also create a sidecar `.metadata.json` file beside the normalized records. This keeps the plain JSON records simple while preserving traceability back to the source artifact.

Current browser demo example:

```text
tests/fixtures/small/browser_activity.synthetic.sqlite
tests/fixtures/small/browser_activity_events.synthetic.json
tests/fixtures/small/browser_activity_events.synthetic.metadata.json
```

The sidecar metadata records fields such as:

```text
source_artifact
source_sha256
normalized_file
normalized_sha256
artifact_type
parser_tool
parser_tool_version
parser_output
parser_output_sha256
record_count
```

Important: `source_sha256` and `normalized_sha256` are expected to be different because the source artifact and normalized JSON are different files. The point is not to prove the files are identical; the point is to document the chain:

```text
source artifact hash
        -> parser/extractor details
        -> normalized JSON hash
        -> validation report
```

Report behavior:

- Markdown reports include an `Evidence provenance` section when sidecar metadata is supplied.
- JSON reports include an `evidence_provenance` object when sidecar metadata is supplied.
- The Streamlit GUI shows compact provenance for evidence groups that have sidecar metadata and provides an expandable full metadata JSON view.

## Future scope

Planned future work includes:

- Firefox history support through a `places.sqlite` extractor
- registry / removable-device evidence, likely using RegRipper output
- broader provenance reporting across all evidence types, from raw artifact to parser output to normalized record
- a formal evidence-package wrapper that can carry metadata and records together
- optional agent/LLM workflow around the deterministic validation core

## Current status

This repo contains the CLI validation core, optional Streamlit review GUI, deterministic fixtures, fixture generators, and automated tests for the current MVP validation path.

No API keys are required for the core tests or CLI validation examples.
