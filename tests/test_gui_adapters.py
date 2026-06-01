"""Tests for the thin Streamlit GUI adapter layer."""

from __future__ import annotations

from traceback_app.claims.schema import ValidationStatus
from traceback_app.gui.adapters import (
    DATASET_OPTIONS,
    EVIDENCE_TYPE_LABELS,
    SAMPLE_CASES,
    build_sample_case_for_evidence_selection,
    dataset_option_display_label,
    display_status_label,
    load_sample_case,
    status_explainer_text,
    status_callout_text,
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
        == "unsupported / insufficient evidence"
    )


def test_status_guidance_explains_contradicted_versus_unsupported() -> None:
    explainer = status_explainer_text()

    assert "matching evidence was found, but it conflicts with the claim" in explainer
    assert "no matching evidence was found" in explainer


def test_status_callout_text_explains_prefetch_absent_is_contradicted_not_unsupported() -> None:
    sample = build_sample_case_for_evidence_selection("prefetch-process", "small-synthetic")
    report = validate_claim(sample.original_claim, sample.evidence_bundle)
    result = report.groups["prefetch-process"].results[2]

    callout = status_callout_text(result)

    assert "matching record" in callout
    assert "prefetch_absent" in callout
    assert "contradicted rather than unsupported" in callout


def test_sample_case_registry_includes_streamlit_default_case() -> None:
    assert "small-synthetic-demo" in SAMPLE_CASES
    assert SAMPLE_CASES["small-synthetic-demo"].name == "Small synthetic demo bundle"


def test_dataset_options_are_grouped_by_evidence_type_and_pair_claims_with_events() -> None:
    assert set(DATASET_OPTIONS) == {"logon", "prefetch-process", "browser-activity"}

    logon_large = DATASET_OPTIONS["logon"]["large-synthetic"]
    assert "windows_logon_events.large.synthetic.json" in str(logon_large.events_path)
    assert "windows_logon_claims.large.synthetic.json" in str(logon_large.claims_path)

    prefetch_large = DATASET_OPTIONS["prefetch-process"]["large-synthetic"]
    assert "windows_prefetch_process_events.large.synthetic.json" in str(
        prefetch_large.events_path
    )
    assert "windows_prefetch_process_claims.large.synthetic.json" in str(
        prefetch_large.claims_path
    )

    browser_large = DATASET_OPTIONS["browser-activity"]["large-synthetic"]
    assert "browser_activity_events.large.synthetic.json" in str(browser_large.events_path)
    assert "browser_activity_claims.large.synthetic.json" in str(browser_large.claims_path)
    assert browser_large.metadata_path is not None


def test_dataset_option_display_label_shows_evidence_and_paired_claims_files() -> None:
    option = DATASET_OPTIONS["logon"]["small-synthetic"]

    label = dataset_option_display_label(option)

    assert "Evidence: windows_logon_events.synthetic.json" in label
    assert "Claims: windows_logon_claims.synthetic.json" in label


def test_build_sample_case_for_selected_evidence_type_loads_only_that_group() -> None:
    sample = build_sample_case_for_evidence_selection("browser-activity", "large-synthetic")

    assert sample.key == "browser-activity:large-synthetic"
    assert set(sample.evidence_bundle.groups) == {"browser-activity"}
    assert "Browser activity evidence" in sample.name

    report = validate_claim(sample.original_claim, sample.evidence_bundle)

    assert set(report.groups) == {"browser-activity"}
    assert report.groups["browser-activity"].provenance_metadata is not None
