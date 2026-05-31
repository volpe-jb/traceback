"""Machine-readable JSON report formatting."""

from __future__ import annotations

import json

from traceback_app.claims.schema import ValidationResult


def results_to_dict(results: list[ValidationResult]) -> dict[str, object]:
    """Return a machine-readable report dictionary."""

    return {
        "report_type": "traceback_windows_logon_validation",
        "result_count": len(results),
        "results": [result.to_dict() for result in results],
    }


def results_to_json(results: list[ValidationResult], *, indent: int = 2) -> str:
    """Return a JSON string for validation results."""

    return json.dumps(results_to_dict(results), indent=indent)
