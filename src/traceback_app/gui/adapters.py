"""Read-only adapter layer for the TraceBack Streamlit GUI.

This module keeps the GUI out of the validation business. It loads known local
fixtures, calls the deterministic validators, and packages results for display.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from traceback_app.claims.schema import ValidationResult, ValidationStatus
from traceback_app.cli import _load_provenance_metadata
from traceback_app.evidence.loaders import (
    BROWSER_ACTIVITY_CLAIM_SCHEMA,
    BROWSER_ACTIVITY_EVENT_SCHEMA,
    LOGON_CLAIM_SCHEMA,
    LOGON_EVENT_SCHEMA,
    PREFETCH_PROCESS_CLAIM_SCHEMA,
    PREFETCH_PROCESS_EVENT_SCHEMA,
    RecordSchema,
    load_json_records,
)
from traceback_app.report.json_report import results_to_json
from traceback_app.report.markdown import results_to_markdown
from traceback_app.validators.browser_activity import validate_browser_activity_claims
from traceback_app.validators.logon import validate_logon_claims
from traceback_app.validators.prefetch_process import validate_prefetch_process_claims

PROJECT_ROOT = Path(__file__).resolve().parents[3]

EVIDENCE_TYPE_LABELS: dict[str, str] = {
    "logon": "Logon evidence",
    "prefetch-process": "Process execution evidence",
    "browser-activity": "Browser activity evidence",
}

_GROUP_ORDER = ("logon", "prefetch-process", "browser-activity")

ValidatorFn = Callable[[list[dict[str, Any]], list[dict[str, Any]]], list[ValidationResult]]


@dataclass(frozen=True)
class EvidenceGroupConfig:
    """Fixture and validator configuration for one evidence type."""

    key: str
    label: str
    validator: ValidatorFn
    events_path: Path
    claims_path: Path
    event_schema: RecordSchema
    claim_schema: RecordSchema
    markdown_title: str
    report_type: str
    metadata_path: Path | None = None


@dataclass(frozen=True)
class EvidenceBundle:
    """A read-only collection of evidence groups for one review/demo case."""

    groups: Mapping[str, EvidenceGroupConfig]


@dataclass(frozen=True)
class SampleCase:
    """A selectable GUI sample case."""

    key: str
    name: str
    description: str
    original_claim: str
    evidence_bundle: EvidenceBundle


@dataclass(frozen=True)
class EvidenceGroupReport:
    """Validation results for one evidence type."""

    key: str
    label: str
    results: list[ValidationResult]
    markdown_report: str
    json_report: str
    provenance_metadata: Mapping[str, object] | None = None


@dataclass(frozen=True)
class ValidationReport:
    """GUI-facing validation report produced by deterministic core validators."""

    original_claim: str
    groups: Mapping[str, EvidenceGroupReport]
    markdown_report: str
    json_report: str
    status_counts: Mapping[str, int]
    corrected_claim: str | None = None


SAMPLE_CASES: dict[str, SampleCase] = {
    "small-synthetic-demo": SampleCase(
        key="small-synthetic-demo",
        name="Small synthetic demo bundle",
        description=(
            "Small deterministic fixtures covering Windows logon activity, "
            "Windows Prefetch process execution, and browser activity."
        ),
        original_claim=(
            "Sample TraceBack claim set: addie_smith activity on WIN-FORENSIC-01 "
            "is validated against normalized logon, process execution, and browser "
            "activity evidence."
        ),
        evidence_bundle=EvidenceBundle(
            groups={
                "logon": EvidenceGroupConfig(
                    key="logon",
                    label=EVIDENCE_TYPE_LABELS["logon"],
                    validator=validate_logon_claims,
                    events_path=PROJECT_ROOT / "tests/fixtures/small/windows_logon_events.synthetic.json",
                    claims_path=PROJECT_ROOT / "tests/fixtures/small/windows_logon_claims.synthetic.json",
                    event_schema=LOGON_EVENT_SCHEMA,
                    claim_schema=LOGON_CLAIM_SCHEMA,
                    markdown_title="TraceBack Windows Logon Validation Summary",
                    report_type="traceback_windows_logon_validation",
                ),
                "prefetch-process": EvidenceGroupConfig(
                    key="prefetch-process",
                    label=EVIDENCE_TYPE_LABELS["prefetch-process"],
                    validator=validate_prefetch_process_claims,
                    events_path=PROJECT_ROOT
                    / "tests/fixtures/small/windows_prefetch_process_events.synthetic.json",
                    claims_path=PROJECT_ROOT
                    / "tests/fixtures/small/windows_prefetch_process_claims.synthetic.json",
                    event_schema=PREFETCH_PROCESS_EVENT_SCHEMA,
                    claim_schema=PREFETCH_PROCESS_CLAIM_SCHEMA,
                    markdown_title="TraceBack Prefetch Process Validation Summary",
                    report_type="traceback_windows_prefetch_process_validation",
                ),
                "browser-activity": EvidenceGroupConfig(
                    key="browser-activity",
                    label=EVIDENCE_TYPE_LABELS["browser-activity"],
                    validator=validate_browser_activity_claims,
                    events_path=PROJECT_ROOT / "tests/fixtures/small/browser_activity_events.synthetic.json",
                    claims_path=PROJECT_ROOT / "tests/fixtures/small/browser_activity_claims.synthetic.json",
                    event_schema=BROWSER_ACTIVITY_EVENT_SCHEMA,
                    claim_schema=BROWSER_ACTIVITY_CLAIM_SCHEMA,
                    markdown_title="TraceBack Browser Activity Validation Summary",
                    report_type="traceback_browser_activity_validation",
                    metadata_path=PROJECT_ROOT
                    / "tests/fixtures/small/browser_activity_events.synthetic.metadata.json",
                ),
            }
        ),
    )
}


def load_sample_case(case_key: str) -> SampleCase:
    """Return a configured read-only sample case for GUI display."""

    try:
        return SAMPLE_CASES[case_key]
    except KeyError as exc:
        available = ", ".join(sorted(SAMPLE_CASES))
        raise ValueError(f"Unknown sample case {case_key!r}. Available cases: {available}") from exc


def validate_claim(claim: str, evidence_bundle: EvidenceBundle) -> ValidationReport:
    """Validate a GUI-selected claim/evidence bundle using deterministic validators.

    The ``claim`` argument is the original human-facing claim text shown by the
    GUI. The current deterministic core validates fixture claim records in each
    evidence group; this adapter preserves the desired GUI/API shape without
    moving validation logic into Streamlit.
    """

    group_reports: dict[str, EvidenceGroupReport] = {}
    all_results: list[ValidationResult] = []

    for key in _GROUP_ORDER:
        if key not in evidence_bundle.groups:
            continue
        config = evidence_bundle.groups[key]
        group_report = _validate_evidence_group(config)
        group_reports[key] = group_report
        all_results.extend(group_report.results)

    markdown_report = _combined_markdown_report(claim, group_reports)
    json_report = _combined_json_report(claim, group_reports)

    return ValidationReport(
        original_claim=claim,
        groups=group_reports,
        markdown_report=markdown_report,
        json_report=json_report,
        status_counts=_count_statuses(all_results),
        corrected_claim=None,
    )


def display_status_label(status: str | ValidationStatus) -> str:
    """Return GUI wording for deterministic validation statuses."""

    status_value = status.value if isinstance(status, ValidationStatus) else str(status)
    if status_value == ValidationStatus.INSUFFICIENT_EVIDENCE.value:
        return "unsupported (insufficient_evidence)"
    return status_value


def agent_review(claim: str, validation_report: ValidationReport) -> None:
    """Placeholder for a future optional AI reviewer layer.

    GUI v0 intentionally does not implement prompt design, API/secret handling,
    hallucination controls, or agentic correction behavior.
    """

    _ = (claim, validation_report)
    return None


def _validate_evidence_group(config: EvidenceGroupConfig) -> EvidenceGroupReport:
    events = load_json_records(config.events_path, schema=config.event_schema)
    claims = load_json_records(config.claims_path, schema=config.claim_schema)
    provenance_metadata = (
        _load_provenance_metadata(config.metadata_path) if config.metadata_path else None
    )
    results = config.validator(claims, events)
    return EvidenceGroupReport(
        key=config.key,
        label=config.label,
        results=results,
        provenance_metadata=provenance_metadata,
        markdown_report=results_to_markdown(
            results,
            title=config.markdown_title,
            provenance_metadata=provenance_metadata,
        ),
        json_report=results_to_json(
            results,
            report_type=config.report_type,
            provenance_metadata=provenance_metadata,
        ),
    )


def _count_statuses(results: list[ValidationResult]) -> dict[str, int]:
    counts = Counter(result.status.value for result in results)
    return {status.value: counts.get(status.value, 0) for status in ValidationStatus}


def _combined_markdown_report(
    original_claim: str, group_reports: Mapping[str, EvidenceGroupReport]
) -> str:
    lines = [
        "# TraceBack GUI v0 Validation Report",
        "",
        "## Original claim",
        original_claim,
        "",
    ]
    for group_report in group_reports.values():
        lines.extend([f"## {group_report.label}", ""])
        lines.append(group_report.markdown_report)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _combined_json_report(
    original_claim: str, group_reports: Mapping[str, EvidenceGroupReport]
) -> str:
    import json

    return json.dumps(
        {
            "report_type": "traceback_gui_v0_validation",
            "original_claim": original_claim,
            "groups": {
                key: {
                    "label": report.label,
                    "result_count": len(report.results),
                    "results": [result.to_dict() for result in report.results],
                    **(
                        {"evidence_provenance": dict(report.provenance_metadata)}
                        if report.provenance_metadata is not None
                        else {}
                    ),
                }
                for key, report in group_reports.items()
            },
        },
        indent=2,
    )
