"""Machine-readable JSON report formatting."""

from __future__ import annotations

import json
from collections.abc import Mapping

from traceback_app.claims.schema import ValidationResult


def results_to_dict(
    results: list[ValidationResult],
    *,
    report_type: str = "traceback_windows_logon_validation",
    provenance_metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return a machine-readable report dictionary."""

    report: dict[str, object] = {
        "report_type": report_type,
        "result_count": len(results),
        "results": [result.to_dict() for result in results],
    }
    if provenance_metadata is not None:
        report["evidence_provenance"] = dict(provenance_metadata)
    return report


def results_to_json(
    results: list[ValidationResult],
    *,
    indent: int = 2,
    report_type: str = "traceback_windows_logon_validation",
    provenance_metadata: Mapping[str, object] | None = None,
) -> str:
    """Return a JSON string for validation results."""

    return json.dumps(
        results_to_dict(
            results,
            report_type=report_type,
            provenance_metadata=provenance_metadata,
        ),
        indent=indent,
    )
