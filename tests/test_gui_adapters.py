"""Tests for the thin Streamlit GUI adapter layer."""

from __future__ import annotations

from traceback_app.claims.schema import ValidationStatus
from traceback_app.gui.adapters import (
    EVIDENCE_TYPE_LABELS,
    SAMPLE_CASES,
    display_status_label,
    load_sample_case,
    validate_claim,
)


def test_load_sample_case_exposes_original_claim_and_all_evidence_groups() -> None:
    sample = load_sample_case("small-synthetic-demo")

    assert "addie_smith" in sample.original_claim
    assert set(sample.evidence_bundle.groups) == {
        "logon",
        "prefetch-process",
        "browser-activity",
    }
    assert EVIDENCE_TYPE_LABELS["logon"] == "Logon evidence"
    assert EVIDENCE_TYPE_LABELS["prefetch-process"] == "Process execution evidence"
    assert EVIDENCE_TYPE_LABELS["browser-activity"] == "Browser activity evidence"


def test_validate_claim_returns_grouped_validation_report_for_sample_bundle() -> None:
    sample = load_sample_case("small-synthetic-demo")

    report = validate_claim(sample.original_claim, sample.evidence_bundle)

    assert report.original_claim == sample.original_claim
    assert set(report.groups) == set(sample.evidence_bundle.groups)
    assert report.status_counts[ValidationStatus.SUPPORTED.value] >= 1
    assert report.status_counts[ValidationStatus.CONTRADICTED.value] >= 1
    assert report.status_counts[ValidationStatus.INSUFFICIENT_EVIDENCE.value] >= 1
    assert "TraceBack GUI v0 Validation Report" in report.markdown_report
    assert report.corrected_claim is None


def test_validate_claim_carries_sidecar_provenance_into_gui_reports() -> None:
    sample = load_sample_case("small-synthetic-demo")

    report = validate_claim(sample.original_claim, sample.evidence_bundle)
    browser_report = report.groups["browser-activity"]

    assert browser_report.provenance_metadata is not None
    assert browser_report.provenance_metadata["source_sha256"] == (
        "b35c2bfb4e54fa29f4c4c7e616372e93557ed230305a0f11cb1debde90d56f9f"
    )
    assert "Evidence provenance" in report.markdown_report
    assert "Source SHA-256" in report.markdown_report
    assert "Normalized SHA-256" in report.markdown_report
    assert '"evidence_provenance"' in report.json_report
    assert '"source_sha256"' in report.json_report


def test_display_status_label_uses_plain_unsupported_wording_for_insufficient_evidence() -> None:
    assert display_status_label(ValidationStatus.SUPPORTED.value) == "supported"
    assert display_status_label(ValidationStatus.CONTRADICTED.value) == "contradicted"
    assert (
        display_status_label(ValidationStatus.INSUFFICIENT_EVIDENCE.value)
        == "unsupported (insufficient_evidence)"
    )


def test_sample_case_registry_includes_streamlit_default_case() -> None:
    assert "small-synthetic-demo" in SAMPLE_CASES
    assert SAMPLE_CASES["small-synthetic-demo"].name == "Small synthetic demo bundle"
