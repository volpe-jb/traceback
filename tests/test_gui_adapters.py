"""Tests for the thin Streamlit GUI adapter layer."""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

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


class _SummaryCaptureStreamlit:
    def __init__(self) -> None:
        self.markdown_calls: list[tuple[str, bool]] = []
        self.info_calls: list[str] = []

    def subheader(self, _text: str) -> None:
        pass

    def markdown(self, body: str, unsafe_allow_html: bool = False) -> None:
        self.markdown_calls.append((body, unsafe_allow_html))

    def info(self, body: str) -> None:
        self.info_calls.append(body)


class _NoOpColumn:
    def __enter__(self) -> "_NoOpColumn":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _ReportActionsCaptureStreamlit:
    def __init__(self) -> None:
        self.download_files: list[str] = []
        self.iframe_body = ""

    def subheader(self, _text: str) -> None:
        pass

    def info(self, _text: str) -> None:
        pass

    def columns(self, count: int) -> list[_NoOpColumn]:
        return [_NoOpColumn() for _ in range(count)]

    def download_button(self, _label: str, *, data: str, file_name: str, mime: str) -> None:
        self.download_files.append(file_name)

    def iframe(self, body: str, *, height: int, width: int) -> None:
        self.iframe_body = body


class _PrintButtonCaptureStreamlit:
    def __init__(self) -> None:
        self.iframe_body = ""
        self.iframe_height = 0
        self.iframe_width = 0

    def iframe(self, body: str, *, height: int, width: int) -> None:
        self.iframe_body = body
        self.iframe_height = height
        self.iframe_width = width


def _load_streamlit_app_module():
    streamlit_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    spec = importlib.util.spec_from_file_location("traceback_streamlit_app", streamlit_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assert_summary_card_is_visually_distinct_for(evidence_type: str) -> None:
    streamlit_app = _load_streamlit_app_module()
    _render_report_summary = streamlit_app._render_report_summary

    sample = build_sample_case_for_evidence_selection(evidence_type, "small-synthetic")
    report = validate_claim(sample.original_claim, sample.evidence_bundle)
    fake_st = _SummaryCaptureStreamlit()

    _render_report_summary(fake_st, report)

    summary_html = fake_st.markdown_calls[0][0]
    assert fake_st.markdown_calls[0][1] is True
    assert "traceback-validation-summary-card" in summary_html
    assert "traceback-validation-summary-title" in summary_html
    assert "traceback-validation-summary-counts" in summary_html
    assert "Supported" in summary_html
    assert "Contradicted" in summary_html
    assert "Unsupported / insufficient evidence" in summary_html
    assert fake_st.info_calls == [status_explainer_text()]


def test_logon_validation_summary_uses_neutral_card_separate_from_blue_explainer() -> None:
    _assert_summary_card_is_visually_distinct_for("logon")


def test_prefetch_validation_summary_uses_neutral_card_separate_from_blue_explainer() -> None:
    _assert_summary_card_is_visually_distinct_for("prefetch-process")


def test_browser_validation_summary_uses_neutral_card_separate_from_blue_explainer() -> None:
    _assert_summary_card_is_visually_distinct_for("browser-activity")


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
    assert "TraceBack GUI v0 Validation Report" not in report.markdown_report
    assert report.markdown_report.startswith("## Original claim")
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
    assert '"report_type": "traceback_gui_v0_1_validation"' in report.json_report
    assert "traceback_gui_v0_validation" not in report.json_report


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


def test_streamlit_result_display_avoids_repeating_contradiction_reason() -> None:
    streamlit_source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
        encoding="utf-8"
    )

    assert "Why this contradicts the claim" not in streamlit_source


def test_streamlit_printed_report_hides_placeholder_old_gui_title_and_marks_end() -> None:
    streamlit_source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
        encoding="utf-8"
    )

    assert "Future optional reviewer layer placeholder" not in streamlit_source
    assert "agent_review(claim, validation_report)" not in streamlit_source
    assert "TraceBack Review GUI v0" not in streamlit_source
    assert "TraceBack Review" in streamlit_source
    assert "End of validation report" in streamlit_source
    assert "_render_end_marker(st)" in streamlit_source


def test_streamlit_print_css_allows_tables_to_split_without_large_blank_gaps() -> None:
    streamlit_source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
        encoding="utf-8"
    )

    assert "@media print" in streamlit_source
    assert "break-inside: auto" in streamlit_source
    assert "page-break-inside: auto" in streamlit_source
    assert "break-inside: avoid" in streamlit_source


def test_streamlit_provenance_prints_full_hashes_and_top_report_actions() -> None:
    streamlit_source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
        encoding="utf-8"
    )

    assert "Source SHA-256: `{source_hash}`" in streamlit_source
    assert "Normalized SHA-256: `{normalized_hash}`" in streamlit_source
    assert "_short_hash" not in streamlit_source
    assert "_render_report_actions(st, report, filename_stem)" in streamlit_source
    assert "Print / Save as PDF" in streamlit_source
    assert "Print / Save screen as PDF" not in streamlit_source
    assert "Use this browser print helper" not in streamlit_source
    assert "The Markdown report includes full source and normalized SHA-256 hashes" in streamlit_source
    assert "The JSON report includes full provenance metadata" in streamlit_source


def test_streamlit_report_export_buttons_use_fixed_sizes_without_iframe_scrollbar() -> None:
    streamlit_source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
        encoding="utf-8"
    )

    assert "width=190" in streamlit_source
    assert "overflow: hidden" in streamlit_source
    assert "box-sizing: border-box" in streamlit_source
    assert "width: 100%;" in streamlit_source


def test_streamlit_report_filename_uses_gui_version_dataset_name_and_timestamp() -> None:
    streamlit_app = _load_streamlit_app_module()

    filename = streamlit_app._report_filename_stem(
        Path("tests/fixtures/small/windows_logon_events.synthetic.json"),
        datetime(2026, 6, 1, 14, 35, 9),
    )

    assert filename == (
        "TraceBack-Gui-v0.1-windows_logon_events.synthetic-"
        "Validation report-2026-06-01-143509"
    )


def test_streamlit_markdown_and_json_downloads_use_selected_dataset_filename() -> None:
    streamlit_app = _load_streamlit_app_module()
    sample = build_sample_case_for_evidence_selection("logon", "small-synthetic")
    report = validate_claim(sample.original_claim, sample.evidence_bundle)
    fake_st = _ReportActionsCaptureStreamlit()
    filename_stem = "TraceBack-Gui-v0.1-windows_logon_events.synthetic-Validation report-2026-06-01-143509"

    streamlit_app._render_report_actions(fake_st, report, filename_stem)

    assert fake_st.download_files == [
        f"{filename_stem}.md",
        f"{filename_stem}.json",
    ]


def test_streamlit_print_button_sets_pdf_default_title_before_printing() -> None:
    streamlit_app = _load_streamlit_app_module()
    fake_st = _PrintButtonCaptureStreamlit()
    filename_stem = "TraceBack-Gui-v0.1-windows_logon_events.synthetic-Validation report-2026-06-01-143509"

    streamlit_app._render_print_button(fake_st, filename_stem)

    assert f"window.parent.document.title = '{filename_stem}'" in fake_st.iframe_body
    assert "window.parent.print()" in fake_st.iframe_body


def test_streamlit_print_helper_uses_current_iframe_api() -> None:
    streamlit_source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
        encoding="utf-8"
    )

    assert "st.iframe(" in streamlit_source
    assert "streamlit.components.v1" not in streamlit_source
    assert "components.html(" not in streamlit_source


def test_streamlit_result_details_use_two_column_tables() -> None:
    streamlit_source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
        encoding="utf-8"
    )

    assert "_render_key_value_table(st, result.expected_values)" in streamlit_source
    assert "Matching criteria searched" in streamlit_source
    assert "No normalized evidence record was found for the matching criteria below." in streamlit_source
    assert "_result_expected_values_heading(result)" in streamlit_source
    assert "_render_result_summary(st, result)" in streamlit_source
    assert "st.warning(_result_summary(result), icon=\"⚠️\")" in streamlit_source
    assert "st.json(result.expected_values" not in streamlit_source
    assert "st.dataframe(result.evidence_references" not in streamlit_source


def test_streamlit_key_value_tables_are_compact_and_print_friendly() -> None:
    streamlit_source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
        encoding="utf-8"
    )

    assert "traceback-kv-table" in streamlit_source
    assert "border-collapse: collapse" in streamlit_source
    assert "break-inside: auto" in streamlit_source
    assert "st.table(rows)" not in streamlit_source


def test_streamlit_prefetch_path_display_uses_single_windows_separators() -> None:
    streamlit_app = _load_streamlit_app_module()

    assert (
        streamlit_app._display_value(r"C:\\Windows\\System32\\notepad.exe")
        == r"C:\Windows\System32\notepad.exe"
    )
    assert (
        streamlit_app._display_value(r"C:\\Windows\\Prefetch\\NOTEPAD.EXE-12345678.pf")
        == r"C:\Windows\Prefetch\NOTEPAD.EXE-12345678.pf"
    )


def test_streamlit_report_preview_is_hidden_behind_collapsed_expander() -> None:
    streamlit_source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
        encoding="utf-8"
    )

    assert "with st.expander(\"Validation report preview\", expanded=False):" in streamlit_source
    assert "st.subheader(\"Validation report preview\")" not in streamlit_source


def test_streamlit_report_preview_does_not_print_raw_json_paths() -> None:
    streamlit_source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
        encoding="utf-8"
    )

    assert "st.code(report.json_report, language=\"json\")" not in streamlit_source
    assert "Optional quick review copy of the downloadable Markdown report." in streamlit_source


def test_streamlit_emphasizes_observed_values_only_for_contradicted_results() -> None:
    streamlit_source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
        encoding="utf-8"
    )

    assert "_render_observed_values(st, result)" in streamlit_source
    assert "Observed values from evidence" in streamlit_source
    assert "traceback-observed-values" in streamlit_source
    assert "result.status.value == \"contradicted\"" in streamlit_source
    assert "color: #0f766e" in streamlit_source
    assert streamlit_source.index(".traceback-observed-values") < streamlit_source.index("@media print")


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
