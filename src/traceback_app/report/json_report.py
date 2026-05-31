"""Machine-readable JSON report formatting."""

from __future__ import annotations

import json

from traceback_app.claims.schema import ValidationResult


def results_to_dict(
    results: list[ValidationResult], *, report_type: str = "traceback_windows_logon_validation"
) -> dict[str, object]:
    """Return a machine-readable report dictionary."""

    return {
        "report_type": report_type,
        "result_count": len(results),
        "results": [result.to_dict() for result in results],
    }


def results_to_json(
    results: list[ValidationResult], *, indent: int = 2, report_type: str = "traceback_windows_logon_validation"
) -> str:
    """Return a JSON string for validation results."""

    return json.dumps(results_to_dict(results, report_type=report_type), indent=indent)
