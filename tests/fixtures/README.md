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
