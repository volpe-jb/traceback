# TraceBack: Evidence Validation for AI-Assisted DFIR

TraceBack is a local-first Python experiment for checking AI-style forensic claims against normalized evidence records.

The goal is simple: if an AI assistant says something happened, TraceBack checks whether the evidence supports it, contradicts it, or does not contain enough information to prove it.

The current app keeps deterministic validation at the center. The CLI is the reproducible workflow door, and the optional Streamlit GUI is a thin review/demo door over the same local validation path. Agent/LLM workflows can be added around it later, but the validation core should remain independently testable and runnable without API keys.

The current validation path runs locally and does not require API keys.

New to GitHub? Start here: [Newcomers: download and try TraceBack](#newcomers-download-and-try-traceback)

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

## Bundled fixtures and custom data

TraceBack v0.1 ships with bundled fixture data under:

```text
tests/fixtures/
```

Useful fixture folders include:

```text
tests/fixtures/small/
tests/fixtures/large/
tests/fixtures/diverse/
tests/fixtures/malformed/
```

- `small/` contains compact synthetic examples that are easier to read.
- `large/` contains noisy synthetic examples that test whether TraceBack can find the right evidence inside larger data.
- `diverse/` contains generated examples with different mixes of supported, contradicted, and insufficient-evidence results.
- `malformed/` contains intentionally broken examples used to test error handling and user-facing error messages.

The Streamlit GUI currently uses bundled fixture pairs only. It does not currently provide a file picker for arbitrary custom evidence and claims files.

The CLI can run custom files with:

```bash
PYTHONPATH=src python3 -m traceback_app.cli \
  --validator <validator-name> \
  --events path/to/your_events.json \
  --claims path/to/your_claims.json
```

Custom files must already be normalized JSON records matching the selected validator schema. TraceBack does not currently accept most raw forensic artifacts directly through the GUI.

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

To list available IANA timezone names for future report/export timestamp selection, run:

```bash
PYTHONPATH=src python3 -m traceback_app.cli --list-timezones
```

This prints names such as `UTC`, `America/Chicago`, `Europe/London`, `Asia/Tokyo`, and `Australia/Sydney`. The timezone list is for report/export timestamp metadata only; evidence timestamps and evidence data are not changed.

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

GUI v0.1 currently lets you:

- select an evidence type:
  - Logon evidence
  - Process execution evidence
  - Browser activity evidence
- select a specific evidence file with its paired claims/assertions file
- choose small synthetic, large noisy synthetic, and generated diverse fixture pairs where available
- choose a report/export timestamp timezone from a drop-down of IANA timezone names
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

The GUI timezone drop-down is for report/export timestamps only, including generated filenames and browser Print / Save as PDF title hints. It does not alter, convert, normalize, or reinterpret evidence timestamps or evidence data.

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

## Newcomers: download and try TraceBack

This section is for people who are new to GitHub, command-line tools, or Python projects.

TraceBack can be tested without a GitHub account and without API keys. You can download the code as a ZIP file, unzip it, open a command line in the project folder, and run the built-in demo data.

### 1. Download the code from GitHub

1. Open the TraceBack GitHub repository page in your browser.
2. Click the green `Code` button.
3. Click `Download ZIP`.
4. Save the ZIP file somewhere easy to find, such as your Downloads folder.

You do not need to use `git clone` for this first test.

### 2. Unzip the project

After the ZIP file downloads:

1. Find the downloaded ZIP file.
2. Right-click it.
3. Choose `Extract All...` or your system's unzip option.
4. Open the extracted folder.

The extracted folder may have a name like:

```text
traceback-main
```

or:

```text
TraceBack-main
```

The exact folder name may vary depending on how GitHub packaged the download.

### 3. Open a command line in the project folder

Run the commands from inside the main TraceBack project folder.

That folder should contain files and folders such as:

```text
README.md
pyproject.toml
streamlit_app.py
src/
tests/
```

#### On Windows

One beginner-friendly way:

1. Open the extracted TraceBack folder in File Explorer.
2. Click the address bar at the top of File Explorer.
3. Type:

```text
cmd
```

4. Press Enter.

This opens Command Prompt already inside that folder.

Another option is PowerShell:

1. Open the extracted TraceBack folder.
2. Hold Shift and right-click inside the folder.
3. Choose `Open PowerShell window here` or `Open in Terminal`.

#### On macOS, Linux, or WSL

Open Terminal, then use `cd` to move into the extracted folder.

Example:

```bash
cd Downloads/TraceBack-main
```

If your folder has a different name, use that name instead.

### 4. Make sure Python and uv are available

TraceBack expects:

- Python 3.10 or newer
- `uv`, a Python project runner/package tool

Check Python:

```bash
python --version
```

or:

```bash
python3 --version
```

Check uv:

```bash
uv --version
```

If `uv` is not installed, install it from the official instructions:

```text
https://docs.astral.sh/uv/getting-started/installation/
```

### 5. What does "normalized JSON" mean?

TraceBack does not currently read most raw forensic artifacts directly in the CLI examples.

Instead, TraceBack expects evidence to be in normalized JSON format.

In plain language, normalized JSON means:

- the data is saved as a `.json` file
- the records use the field names TraceBack expects
- the records have already been converted from a raw source, such as a browser history database, Windows logon artifact, or parser output
- the data is shaped so the selected validator knows what to compare

For example, a raw browser history database might start as a SQLite file like:

```text
browser_activity.synthetic.sqlite
```

A parser/extractor converts that into normalized JSON records like:

```text
browser_activity_events.synthetic.json
```

TraceBack then compares those normalized evidence records against a claims/assertions file like:

```text
browser_activity_claims.synthetic.json
```

So the flow is:

```text
raw forensic artifact or parser output
        -> normalized JSON evidence records
        -> TraceBack validation
        -> supported / contradicted / insufficient_evidence result
```

The Streamlit UI currently uses bundled normalized JSON fixture pairs only.

The CLI can test your own files, but those files must already be normalized JSON records that match one of TraceBack's supported validator types.

### 6. Try the basic CLI validation

The CLI means "command-line interface." It lets you run TraceBack from the terminal.

Use this command from the project folder on macOS, Linux, or WSL:

```bash
PYTHONPATH=src python3 -m traceback_app.cli \
  --validator logon \
  --events tests/fixtures/small/windows_logon_events.synthetic.json \
  --claims tests/fixtures/small/windows_logon_claims.synthetic.json
```

On Windows Command Prompt, use this one-line version instead:

```bat
set PYTHONPATH=src && python -m traceback_app.cli --validator logon --events tests/fixtures/small/windows_logon_events.synthetic.json --claims tests/fixtures/small/windows_logon_claims.synthetic.json
```

On Windows PowerShell, use this one-line version instead:

```powershell
$env:PYTHONPATH="src"; python -m traceback_app.cli --validator logon --events tests/fixtures/small/windows_logon_events.synthetic.json --claims tests/fixtures/small/windows_logon_claims.synthetic.json
```

You should see a human-readable validation report.

### 7. Try the different evidence types

TraceBack v0.1 currently supports three validator types:

```text
logon
prefetch-process
browser-activity
```

#### Windows logon activity

macOS, Linux, or WSL:

```bash
PYTHONPATH=src python3 -m traceback_app.cli \
  --validator logon \
  --events tests/fixtures/small/windows_logon_events.synthetic.json \
  --claims tests/fixtures/small/windows_logon_claims.synthetic.json
```

Windows Command Prompt:

```bat
set PYTHONPATH=src && python -m traceback_app.cli --validator logon --events tests/fixtures/small/windows_logon_events.synthetic.json --claims tests/fixtures/small/windows_logon_claims.synthetic.json
```

Windows PowerShell:

```powershell
$env:PYTHONPATH="src"; python -m traceback_app.cli --validator logon --events tests/fixtures/small/windows_logon_events.synthetic.json --claims tests/fixtures/small/windows_logon_claims.synthetic.json
```

#### Windows Prefetch process execution

macOS, Linux, or WSL:

```bash
PYTHONPATH=src python3 -m traceback_app.cli \
  --validator prefetch-process \
  --events tests/fixtures/small/windows_prefetch_process_events.synthetic.json \
  --claims tests/fixtures/small/windows_prefetch_process_claims.synthetic.json
```

Windows Command Prompt:

```bat
set PYTHONPATH=src && python -m traceback_app.cli --validator prefetch-process --events tests/fixtures/small/windows_prefetch_process_events.synthetic.json --claims tests/fixtures/small/windows_prefetch_process_claims.synthetic.json
```

Windows PowerShell:

```powershell
$env:PYTHONPATH="src"; python -m traceback_app.cli --validator prefetch-process --events tests/fixtures/small/windows_prefetch_process_events.synthetic.json --claims tests/fixtures/small/windows_prefetch_process_claims.synthetic.json
```

#### Browser activity

macOS, Linux, or WSL:

```bash
PYTHONPATH=src python3 -m traceback_app.cli \
  --validator browser-activity \
  --events tests/fixtures/small/browser_activity_events.synthetic.json \
  --claims tests/fixtures/small/browser_activity_claims.synthetic.json \
  --metadata tests/fixtures/small/browser_activity_events.synthetic.metadata.json
```

Windows Command Prompt:

```bat
set PYTHONPATH=src && python -m traceback_app.cli --validator browser-activity --events tests/fixtures/small/browser_activity_events.synthetic.json --claims tests/fixtures/small/browser_activity_claims.synthetic.json --metadata tests/fixtures/small/browser_activity_events.synthetic.metadata.json
```

Windows PowerShell:

```powershell
$env:PYTHONPATH="src"; python -m traceback_app.cli --validator browser-activity --events tests/fixtures/small/browser_activity_events.synthetic.json --claims tests/fixtures/small/browser_activity_claims.synthetic.json --metadata tests/fixtures/small/browser_activity_events.synthetic.metadata.json
```

Browser activity currently supports Chromium-family normalized browser history data, such as Chrome, Edge, and Chromium. Firefox support is future scope.

### 8. Where to find more demo/test data

TraceBack includes more built-in test data in this folder:

```text
tests/fixtures/
```

Inside that folder:

- `small/` has simple examples.
- `large/` has noisy examples with extra background records.
- `diverse/` has generated examples with different result mixes.
- `malformed/` has intentionally broken examples used to test error messages.

The Streamlit UI currently lets you choose from bundled demo fixture pairs only. It does not currently let you upload or browse for your own files.

If you want to try your own data, use the CLI instead. Your files need to be normalized JSON records that match one of the current validator types.

The `malformed/` folder is mainly for testing how TraceBack explains bad input. It is normal for those files to produce error messages.

### 9. Force the CLI to print JSON

By default, the CLI prints a human-readable Markdown-style report.

To force machine-readable JSON output, add:

```text
--print-json
```

Example for macOS, Linux, or WSL:

```bash
PYTHONPATH=src python3 -m traceback_app.cli \
  --validator browser-activity \
  --events tests/fixtures/small/browser_activity_events.synthetic.json \
  --claims tests/fixtures/small/browser_activity_claims.synthetic.json \
  --metadata tests/fixtures/small/browser_activity_events.synthetic.metadata.json \
  --print-json
```

Windows Command Prompt:

```bat
set PYTHONPATH=src && python -m traceback_app.cli --validator browser-activity --events tests/fixtures/small/browser_activity_events.synthetic.json --claims tests/fixtures/small/browser_activity_claims.synthetic.json --metadata tests/fixtures/small/browser_activity_events.synthetic.metadata.json --print-json
```

Windows PowerShell:

```powershell
$env:PYTHONPATH="src"; python -m traceback_app.cli --validator browser-activity --events tests/fixtures/small/browser_activity_events.synthetic.json --claims tests/fixtures/small/browser_activity_claims.synthetic.json --metadata tests/fixtures/small/browser_activity_events.synthetic.metadata.json --print-json
```

JSON is useful if you want another tool or script to read the validation results.

### 10. Save JSON to a file

To save the JSON report to a file, use:

```text
--json-output filename.json
```

Example for macOS, Linux, or WSL:

```bash
PYTHONPATH=src python3 -m traceback_app.cli \
  --validator logon \
  --events tests/fixtures/small/windows_logon_events.synthetic.json \
  --claims tests/fixtures/small/windows_logon_claims.synthetic.json \
  --json-output traceback-logon-report.json
```

Windows Command Prompt:

```bat
set PYTHONPATH=src && python -m traceback_app.cli --validator logon --events tests/fixtures/small/windows_logon_events.synthetic.json --claims tests/fixtures/small/windows_logon_claims.synthetic.json --json-output traceback-logon-report.json
```

Windows PowerShell:

```powershell
$env:PYTHONPATH="src"; python -m traceback_app.cli --validator logon --events tests/fixtures/small/windows_logon_events.synthetic.json --claims tests/fixtures/small/windows_logon_claims.synthetic.json --json-output traceback-logon-report.json
```

This creates a file named:

```text
traceback-logon-report.json
```

in the current folder.

### 11. Show the Markdown preview explicitly

The CLI can show a human-readable Markdown preview with:

```text
--preview
```

Example for macOS, Linux, or WSL:

```bash
PYTHONPATH=src python3 -m traceback_app.cli \
  --validator prefetch-process \
  --events tests/fixtures/small/windows_prefetch_process_events.synthetic.json \
  --claims tests/fixtures/small/windows_prefetch_process_claims.synthetic.json \
  --preview
```

Windows Command Prompt:

```bat
set PYTHONPATH=src && python -m traceback_app.cli --validator prefetch-process --events tests/fixtures/small/windows_prefetch_process_events.synthetic.json --claims tests/fixtures/small/windows_prefetch_process_claims.synthetic.json --preview
```

Windows PowerShell:

```powershell
$env:PYTHONPATH="src"; python -m traceback_app.cli --validator prefetch-process --events tests/fixtures/small/windows_prefetch_process_events.synthetic.json --claims tests/fixtures/small/windows_prefetch_process_claims.synthetic.json --preview
```

### 12. Try the Streamlit review UI

TraceBack also includes a Streamlit review/demo interface.

From the project folder, run:

```bash
UV_LINK_MODE=copy uv run streamlit run streamlit_app.py
```

Streamlit will print a local URL that usually looks like:

```text
Local URL: http://localhost:8501
```

Open that URL in your browser.

In the Streamlit UI, you can:

- select an evidence type
- select a specific evidence file with its paired claims/assertions file
- run deterministic validation
- review supported, contradicted, and unsupported / insufficient evidence results
- download Markdown and JSON reports
- use browser Print / Save as PDF

If the browser does not open automatically, copy the `Local URL` from the terminal and paste it into your browser.

To stop Streamlit, go back to the terminal and press:

```text
Ctrl+C
```

### 13. What results should you expect?

The built-in demo fixtures are designed to show a mix of outcomes:

```text
supported
contradicted
insufficient_evidence
```

These statuses mean:

- `supported`: matching evidence agrees with the claim
- `contradicted`: matching evidence exists, but it conflicts with the claim
- `insufficient_evidence`: TraceBack did not find enough matching evidence to prove the claim

This is intentional. TraceBack is not trying to mark everything as true. It is checking whether the available evidence supports, contradicts, or cannot prove each claim.

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
