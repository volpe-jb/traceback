# TraceBack test fixtures

This folder makes the TraceBack app repository self-contained for automated tests.

## Folders

```text
small/
large/
```

`small/` contains the repeatable, human-readable synthetic fixtures used by focused unit tests.

`large/` contains deterministic noisy synthetic fixtures with the same four base claims and required evidence anchors, plus background noise. These are used to prove the validators can find the correct evidence reference inside a larger evidence set.

The Find Evil Lab Obsidian vault remains the documented demo/data source:

```text
/mnt/c/Users/Brandi Volpe/Markdown vaults/Find Evil Lab/Data created
```

The app repo keeps copies here so a clone of the code repo can run:

```bash
UV_LINK_MODE=copy uv run --with pytest pytest -q
```

without depending on that local Obsidian vault path.

## Regenerating large fixtures

From the TraceBack code repo root:

```bash
UV_LINK_MODE=copy uv run python scripts/generate_noisy_synthetic_data.py --input-dir tests/fixtures/small --output-dir tests/fixtures/large --logon-noise-count 250 --prefetch-noise-count 250
```

To regenerate the demo copies in the Find Evil Lab vault, pass that vault path as `--output-dir` instead.

## Source artifacts, normalized records, and sidecar metadata

TraceBack keeps the original forensic source artifact separate from the normalized records used by the validation core.

For browser activity, the current source artifact is a Chromium/Edge-style History SQLite database. The extractor reads the relevant `urls` and `visits` rows, writes normalized browser activity records as JSON, and writes a sidecar metadata file beside that JSON.

Example current browser fixture set:

```text
browser_activity.synthetic.sqlite
browser_activity_events.synthetic.json
browser_activity_events.synthetic.metadata.json
browser_activity_claims.synthetic.json
```

The metadata filename replaces the normalized JSON suffix with `.metadata.json`:

```text
browser_activity_events.synthetic.json -> browser_activity_events.synthetic.metadata.json
```

The sidecar metadata records provenance for the normalized JSON file:

```text
traceback_metadata_version
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

The source artifact hash and normalized JSON hash are expected to be different because they are hashes of different files. TraceBack does not use those hashes to prove that SQLite and JSON are identical. Instead, the metadata links:

```text
source artifact -> extractor/parser -> normalized JSON -> validation results
```

Normalized JSON is the working validation format, not a replacement for primary forensic evidence. Raw/source artifacts and parser-native outputs should be preserved locally where practical so a reviewer can trace validation records back to the source evidence.

Current browser support is intentionally narrow: Chromium/Edge History SQLite databases with `urls` and `visits` tables. Firefox, Safari, and other browser formats should be handled later by browser-specific extractors that emit the same normalized browser activity record shape.

## Diverse synthetic validation fixtures

`diverse/` contains deterministic generated fixture pairs for all three current validators:

```text
windows_logon
windows_prefetch_process_execution
browser_activity
```

Each diverse fixture filename encodes the expected validation counts:

```text
<claim_type>_<events|claims>.<size>.<scenario>-<records>-<supported>-<contradicted>-<insufficient>.json
```

For example:

```text
browser_activity_events.small.mixed-4-1-2-1.json
```

means the app should examine 4 browser activity claims and produce 1 supported, 2 contradicted, and 1 insufficient-evidence result.

Regenerate these fixtures from the repo root with:

```bash
python3 scripts/generate_diverse_synthetic_fixtures.py
```

Then verify them with:

```bash
UV_LINK_MODE=copy uv run --with pytest pytest tests/test_diverse_synthetic_fixtures.py -q
```

The diverse browser activity fixtures currently use only supported Chromium-family normalized browser labels:

```text
Microsoft Edge
Google Chrome
Chromium
```

Do not add Firefox or another browser to `BROWSERS = [...]` in `scripts/generate_diverse_synthetic_fixtures.py` until TraceBack has a matching extractor/parser path for that browser data type. Firefox support is future scope, likely through a `places.sqlite` extractor that normalizes `moz_places` and `moz_historyvisits` data into the existing browser activity record shape.
