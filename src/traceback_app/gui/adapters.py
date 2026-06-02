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
class EvidenceTypeConfig:
    """Stable validation settings for one evidence type."""

    key: str
    label: str
    validator: ValidatorFn
    event_schema: RecordSchema
    claim_schema: RecordSchema
    markdown_title: str
    report_type: str


@dataclass(frozen=True)
class EvidenceDatasetOption:
    """Selectable event/claim file pair for one evidence type."""

    key: str
    name: str
    description: str
    events_path: Path
    claims_path: Path
    metadata_path: Path | None = None


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


EVIDENCE_TYPE_CONFIGS: dict[str, EvidenceTypeConfig] = {
    "logon": EvidenceTypeConfig(
        key="logon",
        label=EVIDENCE_TYPE_LABELS["logon"],
        validator=validate_logon_claims,
        event_schema=LOGON_EVENT_SCHEMA,
        claim_schema=LOGON_CLAIM_SCHEMA,
        markdown_title="TraceBack Windows Logon Validation Summary",
        report_type="traceback_windows_logon_validation",
    ),
    "prefetch-process": EvidenceTypeConfig(
        key="prefetch-process",
        label=EVIDENCE_TYPE_LABELS["prefetch-process"],
        validator=validate_prefetch_process_claims,
        event_schema=PREFETCH_PROCESS_EVENT_SCHEMA,
        claim_schema=PREFETCH_PROCESS_CLAIM_SCHEMA,
        markdown_title="TraceBack Prefetch Process Validation Summary",
        report_type="traceback_windows_prefetch_process_validation",
    ),
    "browser-activity": EvidenceTypeConfig(
        key="browser-activity",
        label=EVIDENCE_TYPE_LABELS["browser-activity"],
        validator=validate_browser_activity_claims,
        event_schema=BROWSER_ACTIVITY_EVENT_SCHEMA,
        claim_schema=BROWSER_ACTIVITY_CLAIM_SCHEMA,
        markdown_title="TraceBack Browser Activity Validation Summary",
        report_type="traceback_browser_activity_validation",
    ),
}

DATASET_OPTIONS: dict[str, dict[str, EvidenceDatasetOption]] = {
    "logon": {
        "small-synthetic": EvidenceDatasetOption(
            key="small-synthetic",
            name="Small synthetic logon data",
            description="Small deterministic Windows logon event and claim pair.",
            events_path=PROJECT_ROOT / "tests/fixtures/small/windows_logon_events.synthetic.json",
            claims_path=PROJECT_ROOT / "tests/fixtures/small/windows_logon_claims.synthetic.json",
        ),
        "large-synthetic": EvidenceDatasetOption(
            key="large-synthetic",
            name="Large noisy synthetic logon data",
            description="Larger Windows logon event and claim pair for noisy review testing.",
            events_path=PROJECT_ROOT / "tests/fixtures/large/windows_logon_events.large.synthetic.json",
            claims_path=PROJECT_ROOT / "tests/fixtures/large/windows_logon_claims.large.synthetic.json",
        ),
        "diverse-small-zero-supported": EvidenceDatasetOption(
            key="diverse-small-zero-supported",
            name="Diverse small logon data: zero supported",
            description="Generated logon case with supported claims intentionally absent.",
            events_path=PROJECT_ROOT
            / "tests/fixtures/diverse/windows_logon_events.small.zero-supported-5-0-3-2.json",
            claims_path=PROJECT_ROOT
            / "tests/fixtures/diverse/windows_logon_claims.small.zero-supported-5-0-3-2.json",
        ),
        "diverse-large-zero-insufficient": EvidenceDatasetOption(
            key="diverse-large-zero-insufficient",
            name="Diverse large logon data: zero insufficient",
            description="Generated logon case with insufficient-evidence claims intentionally absent.",
            events_path=PROJECT_ROOT
            / "tests/fixtures/diverse/windows_logon_events.large.zero-insufficient-24-9-15-0.json",
            claims_path=PROJECT_ROOT
            / "tests/fixtures/diverse/windows_logon_claims.large.zero-insufficient-24-9-15-0.json",
        ),
    },
    "prefetch-process": {
        "small-synthetic": EvidenceDatasetOption(
            key="small-synthetic",
            name="Small synthetic Prefetch data",
            description="Small deterministic Prefetch process event and claim pair.",
            events_path=PROJECT_ROOT
            / "tests/fixtures/small/windows_prefetch_process_events.synthetic.json",
            claims_path=PROJECT_ROOT
            / "tests/fixtures/small/windows_prefetch_process_claims.synthetic.json",
        ),
        "large-synthetic": EvidenceDatasetOption(
            key="large-synthetic",
            name="Large noisy synthetic Prefetch data",
            description="Larger Prefetch process event and claim pair for noisy review testing.",
            events_path=PROJECT_ROOT
            / "tests/fixtures/large/windows_prefetch_process_events.large.synthetic.json",
            claims_path=PROJECT_ROOT
            / "tests/fixtures/large/windows_prefetch_process_claims.large.synthetic.json",
        ),
        "diverse-small-zero-contradicted": EvidenceDatasetOption(
            key="diverse-small-zero-contradicted",
            name="Diverse small Prefetch data: zero contradicted",
            description="Generated Prefetch case with contradicted claims intentionally absent.",
            events_path=PROJECT_ROOT
            / "tests/fixtures/diverse/windows_prefetch_process_execution_events.small.zero-contradicted-6-2-0-4.json",
            claims_path=PROJECT_ROOT
            / "tests/fixtures/diverse/windows_prefetch_process_execution_claims.small.zero-contradicted-6-2-0-4.json",
        ),
        "diverse-large-zero-supported": EvidenceDatasetOption(
            key="diverse-large-zero-supported",
            name="Diverse large Prefetch data: zero supported",
            description="Generated Prefetch case with supported claims intentionally absent.",
            events_path=PROJECT_ROOT
            / "tests/fixtures/diverse/windows_prefetch_process_execution_events.large.zero-supported-30-0-12-18.json",
            claims_path=PROJECT_ROOT
            / "tests/fixtures/diverse/windows_prefetch_process_execution_claims.large.zero-supported-30-0-12-18.json",
        ),
    },
    "browser-activity": {
        "small-synthetic": EvidenceDatasetOption(
            key="small-synthetic",
            name="Small synthetic browser data",
            description="Small deterministic browser activity event and claim pair.",
            events_path=PROJECT_ROOT / "tests/fixtures/small/browser_activity_events.synthetic.json",
            claims_path=PROJECT_ROOT / "tests/fixtures/small/browser_activity_claims.synthetic.json",
            metadata_path=PROJECT_ROOT
            / "tests/fixtures/small/browser_activity_events.synthetic.metadata.json",
        ),
        "large-synthetic": EvidenceDatasetOption(
            key="large-synthetic",
            name="Large noisy synthetic browser data",
            description="Larger browser activity event and claim pair for noisy review testing.",
            events_path=PROJECT_ROOT
            / "tests/fixtures/large/browser_activity_events.large.synthetic.json",
            claims_path=PROJECT_ROOT
            / "tests/fixtures/large/browser_activity_claims.large.synthetic.json",
            metadata_path=PROJECT_ROOT
            / "tests/fixtures/large/browser_activity_events.large.synthetic.metadata.json",
        ),
        "diverse-small-mixed": EvidenceDatasetOption(
            key="diverse-small-mixed",
            name="Diverse small browser data: mixed outcomes",
            description="Generated browser case with supported, contradicted, and insufficient outcomes.",
            events_path=PROJECT_ROOT
            / "tests/fixtures/diverse/browser_activity_events.small.mixed-4-1-2-1.json",
            claims_path=PROJECT_ROOT
            / "tests/fixtures/diverse/browser_activity_claims.small.mixed-4-1-2-1.json",
        ),
        "diverse-large-zero-insufficient": EvidenceDatasetOption(
            key="diverse-large-zero-insufficient",
            name="Diverse large browser data: zero insufficient",
            description="Generated browser case with insufficient-evidence claims intentionally absent.",
            events_path=PROJECT_ROOT
            / "tests/fixtures/diverse/browser_activity_events.large.zero-insufficient-40-16-24-0.json",
            claims_path=PROJECT_ROOT
            / "tests/fixtures/diverse/browser_activity_claims.large.zero-insufficient-40-16-24-0.json",
        ),
    },
}


def dataset_option_display_label(option: EvidenceDatasetOption) -> str:
    """Return a Streamlit-friendly label showing paired evidence and claim files."""

    return f"Evidence: {option.events_path.name}  |  Claims: {option.claims_path.name}"


def _evidence_group_config(
    evidence_type_key: str, dataset_option: EvidenceDatasetOption
) -> EvidenceGroupConfig:
    evidence_type = EVIDENCE_TYPE_CONFIGS[evidence_type_key]
    return EvidenceGroupConfig(
        key=evidence_type.key,
        label=evidence_type.label,
        validator=evidence_type.validator,
        events_path=dataset_option.events_path,
        claims_path=dataset_option.claims_path,
        event_schema=evidence_type.event_schema,
        claim_schema=evidence_type.claim_schema,
        markdown_title=evidence_type.markdown_title,
        report_type=evidence_type.report_type,
        metadata_path=dataset_option.metadata_path,
    )


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
                "logon": _evidence_group_config(
                    "logon", DATASET_OPTIONS["logon"]["small-synthetic"]
                ),
                "prefetch-process": _evidence_group_config(
                    "prefetch-process",
                    DATASET_OPTIONS["prefetch-process"]["small-synthetic"],
                ),
                "browser-activity": _evidence_group_config(
                    "browser-activity",
                    DATASET_OPTIONS["browser-activity"]["small-synthetic"],
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


def build_sample_case_for_evidence_selection(
    evidence_type_key: str, dataset_key: str
) -> SampleCase:
    """Build a one-evidence-type GUI case from a selected event/claim pair."""

    try:
        dataset_option = DATASET_OPTIONS[evidence_type_key][dataset_key]
    except KeyError as exc:
        available_types = ", ".join(sorted(DATASET_OPTIONS))
        available_datasets = ", ".join(
            sorted(DATASET_OPTIONS.get(evidence_type_key, {}))
        )
        raise ValueError(
            f"Unknown evidence selection type={evidence_type_key!r}, dataset={dataset_key!r}. "
            f"Available types: {available_types}. "
            f"Available datasets for this type: {available_datasets or 'none'}."
        ) from exc

    evidence_type = EVIDENCE_TYPE_CONFIGS[evidence_type_key]
    return SampleCase(
        key=f"{evidence_type_key}:{dataset_key}",
        name=f"{evidence_type.label} — {dataset_option.name}",
        description=dataset_option.description,
        original_claim=(
            f"Selected TraceBack claim set: {dataset_option.name} is validated "
            f"against its paired {evidence_type.label.lower()} claims/assertions file."
        ),
        evidence_bundle=EvidenceBundle(
            groups={
                evidence_type_key: _evidence_group_config(evidence_type_key, dataset_option)
            }
        ),
    )


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
        return "unsupported / insufficient evidence"
    return status_value


def status_explainer_text() -> str:
    """Return human-facing guidance for interpreting validation statuses."""

    return (
        "Supported: matching evidence agrees with the claim.\n\n"
        "Contradicted: matching evidence was found, but it conflicts with the claim.\n\n"
        "Unsupported / insufficient evidence: no matching evidence was found for the claim."
    )


def status_callout_text(result: ValidationResult) -> str:
    """Return a short GUI callout explaining the result status."""

    if result.status == ValidationStatus.SUPPORTED:
        return "Matching evidence agrees with this claim."

    if result.status == ValidationStatus.INSUFFICIENT_EVIDENCE:
        return "No matching evidence was found for this claim, so TraceBack marks it as unsupported / insufficient evidence."

    if _has_prefetch_absent_observation(result):
        return (
            "A matching record exists in the normalized Prefetch evidence, but it records "
            "event_action=prefetch_absent instead of process_executed. Because matching "
            "evidence exists and directly conflicts with the claim, TraceBack marks this "
            "as contradicted rather than unsupported."
        )

    return (
        "Matching evidence was found, but one or more fields conflict with the claim. "
        "Because relevant evidence exists, TraceBack marks this as contradicted rather "
        "than unsupported."
    )


def _has_prefetch_absent_observation(result: ValidationResult) -> bool:
    return any(
        observed.get("event_action") == "prefetch_absent"
        for observed in result.observed_values
    )


def agent_review(claim: str, validation_report: ValidationReport) -> None:
    """Placeholder for a future optional AI reviewer layer.

    GUI v0.1 intentionally does not implement prompt design, API/secret handling,
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
            "report_type": "traceback_gui_v0_1_validation",
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
