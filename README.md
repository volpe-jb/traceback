# TraceBack: Evidence Validation for AI-Assisted DFIR

TraceBack is a local-first Python CLI experiment for checking AI-style forensic claims against normalized evidence records.

The goal is simple: if an AI assistant says something happened, TraceBack checks whether the evidence supports it, contradicts it, or does not contain enough information to prove it.

This CLI version focuses on deterministic validation that can run without API keys, cloud services, or an LLM. Agent/LLM workflows can be added around it later, but the validation core should remain independently testable.

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

## What TraceBack outputs

For each claim, TraceBack returns one of three validation statuses:

- `supported` — matching evidence supports the claim
- `contradicted` — matching evidence exists, but it conflicts with the claim
- `insufficient_evidence` — no matching evidence was found for the claim

The CLI prints a Markdown report by default and can also print a JSON report with `--print-json`.

## Repository layout

```text
src/traceback_app/          Core app package
src/traceback_app/cli.py    CLI entry point
src/traceback_app/validators/
                            Evidence-type validators
tests/                      Automated tests
tests/fixtures/             Small, large, malformed, and diverse fixtures
scripts/                    Deterministic fixture-generation scripts
```

## Requirements

- Python 3.10+
- `uv` for the test commands shown below

The project has no runtime package dependencies at the moment. Tests use `pytest` through `uv`.

## Run the tests

From the repo root:

```bash
UV_LINK_MODE=copy uv run --with pytest pytest -q
```

Expected current result:

```text
63 passed
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

## Future scope

Planned future work includes:

- Firefox history support through a `places.sqlite` extractor
- registry / removable-device evidence, likely using RegRipper output
- stronger provenance reporting from raw artifact to parser output to normalized record
- a formal evidence-package wrapper that can carry metadata and records together
- optional agent/LLM workflow around the deterministic validation core

## Current status

This repo contains the CLI validation core, deterministic fixtures, fixture generators, and automated tests for the current MVP validation path.

No API keys are required for the core tests or CLI validation examples.
