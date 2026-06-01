"""Streamlit review/demo GUI for TraceBack validation.

Run with:
    uv run streamlit run streamlit_app.py
"""

from __future__ import annotations

from collections.abc import Mapping
from html import escape
from typing import Any

from traceback_app.claims.schema import ValidationResult
from traceback_app.gui.adapters import (
    DATASET_OPTIONS,
    EVIDENCE_TYPE_LABELS,
    ValidationReport,
    build_sample_case_for_evidence_selection,
    dataset_option_display_label,
    display_status_label,
    status_callout_text,
    status_explainer_text,
    validate_claim,
)


def main() -> None:
    """Render the thin Streamlit GUI over the deterministic validation core."""

    import streamlit as st

    st.set_page_config(page_title="TraceBack Review GUI v0", layout="wide")
    _inject_print_styles(st)
    st.title("TraceBack Review GUI v0")
    st.caption(
        "Read-only review/demo layer over deterministic local validation. "
        "No LLM or API key is required."
    )

    evidence_type_key = st.selectbox(
        "Select evidence type",
        options=list(DATASET_OPTIONS),
        format_func=lambda key: EVIDENCE_TYPE_LABELS[key],
    )
    dataset_options = DATASET_OPTIONS[evidence_type_key]
    dataset_key = st.selectbox(
        "Select evidence file and paired claims/assertions file",
        options=list(dataset_options),
        format_func=lambda key: dataset_option_display_label(dataset_options[key]),
    )
    sample = build_sample_case_for_evidence_selection(evidence_type_key, dataset_key)
    selection_key = f"{evidence_type_key}:{dataset_key}"
    if st.session_state.get("traceback_selection_key") != selection_key:
        st.session_state["traceback_selection_key"] = selection_key
        st.session_state.pop("traceback_report", None)

    st.subheader("Selected claim/assertion set")
    st.write(sample.original_claim)
    st.info(sample.description)

    with st.expander("Evidence bundle files", expanded=False):
        for group in sample.evidence_bundle.groups.values():
            st.markdown(f"**{group.label}**")
            st.write(f"Claims: `{group.claims_path}`")
            st.write(f"Evidence: `{group.events_path}`")
            if group.metadata_path:
                st.write(f"Provenance metadata: `{group.metadata_path}`")

    if st.button("Run validation", type="primary"):
        st.session_state["traceback_report"] = validate_claim(
            sample.original_claim, sample.evidence_bundle
        )

    report = st.session_state.get("traceback_report")
    if report is None:
        st.warning("Choose a sample case, then run validation.")
        return

    _render_report_summary(st, report)
    _render_report_actions(st, report)
    _render_grouped_results(st, report)
    _render_corrected_claim(st, report)
    _render_end_marker(st)
    _render_report_preview(st, report)


def _inject_print_styles(st: Any) -> None:
    st.markdown(
        """
        <style>
        .traceback-observed-values {
            border-left: 0.25rem solid #0f766e;
            color: #0f766e;
            font-weight: 700;
            padding-left: 0.75rem;
        }
        .traceback-validation-summary-card {
            background: #111827;
            border: 1px solid rgba(148, 163, 184, 0.55);
            border-radius: 0.65rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.35);
            color: #e5e7eb;
            margin: 0.25rem 0 0.75rem 0;
            padding: 0.85rem 1rem;
        }
        .traceback-validation-summary-title {
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.65rem;
        }
        .traceback-validation-summary-counts {
            display: grid;
            gap: 0.65rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }
        .traceback-validation-summary-item {
            background: rgba(31, 41, 55, 0.9);
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 0.5rem;
            padding: 0.55rem 0.65rem;
        }
        .traceback-validation-summary-label {
            color: #cbd5e1;
            font-size: 0.82rem;
            font-weight: 650;
            text-transform: uppercase;
        }
        .traceback-validation-summary-value {
            color: #f8fafc;
            font-size: 1.55rem;
            font-weight: 800;
            line-height: 1.2;
            margin-top: 0.2rem;
        }
        .traceback-kv-table {
            border-collapse: collapse;
            break-inside: auto;
            margin: 0.2rem 0 0.65rem 0;
            page-break-inside: auto;
            width: 100%;
        }
        .traceback-kv-table th,
        .traceback-kv-table td {
            border: 1px solid rgba(148, 163, 184, 0.45);
            padding: 0.25rem 0.45rem;
            text-align: left;
            vertical-align: top;
        }
        .traceback-kv-table tr {
            break-inside: avoid;
            page-break-inside: avoid;
        }
        .traceback-kv-table th:first-child,
        .traceback-kv-table td:first-child {
            width: 13rem;
        }
        @media print {
            table,
            tbody {
                break-inside: auto !important;
                page-break-inside: auto !important;
            }
            tr {
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }
            thead {
                display: table-header-group;
            }
            h3,
            [data-testid="stMarkdownContainer"] strong {
                break-after: avoid;
                page-break-after: avoid;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_report_summary(st: Any, report: ValidationReport) -> None:
    st.subheader("Validation summary")
    supported_count = report.status_counts.get("supported", 0)
    contradicted_count = report.status_counts.get("contradicted", 0)
    unsupported_count = report.status_counts.get("insufficient_evidence", 0)
    st.markdown(
        f"""
        <section class="traceback-validation-summary-card">
            <div class="traceback-validation-summary-title">Validation summary</div>
            <div class="traceback-validation-summary-counts">
                <div class="traceback-validation-summary-item">
                    <div class="traceback-validation-summary-label">Supported</div>
                    <div class="traceback-validation-summary-value">{supported_count}</div>
                </div>
                <div class="traceback-validation-summary-item">
                    <div class="traceback-validation-summary-label">Contradicted</div>
                    <div class="traceback-validation-summary-value">{contradicted_count}</div>
                </div>
                <div class="traceback-validation-summary-item">
                    <div class="traceback-validation-summary-label">Unsupported / insufficient evidence</div>
                    <div class="traceback-validation-summary-value">{unsupported_count}</div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.info(status_explainer_text())


def _render_grouped_results(st: object, report: ValidationReport) -> None:
    st.subheader("Evidence checks by type")
    for group_report in report.groups.values():
        with st.expander(group_report.label, expanded=True):
            _render_provenance_summary(
                st, group_report.label, group_report.provenance_metadata
            )
            for result in group_report.results:
                _render_result(st, result)


def _render_provenance_summary(
    st: Any, group_label: str, provenance_metadata: Mapping[str, object] | None
) -> None:
    if provenance_metadata is None:
        st.caption("No sidecar provenance metadata is attached for this evidence group yet.")
        return

    st.markdown(f"### Evidence provenance for {group_label}")
    source_hash = str(provenance_metadata.get("source_sha256", ""))
    normalized_hash = str(provenance_metadata.get("normalized_sha256", ""))
    st.write(f"Source artifact: `{provenance_metadata.get('source_artifact')}`")
    st.write(f"Source SHA-256: `{source_hash}`")
    st.write(f"Normalized records: `{provenance_metadata.get('normalized_file')}`")
    st.write(f"Normalized SHA-256: `{normalized_hash}`")
    st.write(
        "Parser/extractor: "
        f"`{provenance_metadata.get('parser_tool')}` "
        f"version `{provenance_metadata.get('parser_tool_version')}`"
    )
    st.write(f"Records: `{provenance_metadata.get('record_count')}`")
    with st.expander("View full provenance metadata", expanded=False):
        st.json(provenance_metadata, expanded=True)



def _render_result(st: Any, result: ValidationResult) -> None:
    status_label = display_status_label(result.status)
    st.markdown(f"### {result.claim_id}: `{status_label}`")
    _render_status_callout(st, result)
    st.write(result.claim_text)
    _render_result_summary(st, result)

    if result.expected_values:
        st.markdown(f"**{_result_expected_values_heading(result)}**")
        _render_key_value_table(st, result.expected_values)

    if result.observed_values:
        _render_observed_values(st, result)

    if result.evidence_references:
        st.markdown("**Evidence references**")
        for reference in result.evidence_references:
            _render_key_value_table(st, reference)


def _render_key_value_table(st: Any, values: Mapping[str, object]) -> None:
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(key))}</td>"
        f"<td>{escape(_display_value(value))}</td>"
        "</tr>"
        for key, value in values.items()
    )
    st.markdown(
        f"""
        <table class="traceback-kv-table">
            <thead>
                <tr><th>Field</th><th>Value</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _display_value(value: object) -> str:
    if value is None:
        return "None"
    return str(value)


def _render_observed_values(st: Any, result: ValidationResult) -> None:
    if result.status.value == "contradicted":
        st.markdown(
            """
            <div class="traceback-observed-values">
            <strong>Observed values from evidence</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown("**Observed values**")

    for observed_value in result.observed_values:
        _render_key_value_table(st, observed_value)


def _render_result_summary(st: Any, result: ValidationResult) -> None:
    if result.status.value == "insufficient_evidence":
        st.warning(_result_summary(result), icon="⚠️")
    else:
        st.write(_result_summary(result))


def _result_summary(result: ValidationResult) -> str:
    if result.status.value == "supported":
        return _before_first_marker(result.explanation, ": ")
    if result.status.value == "contradicted":
        return _before_first_marker(result.explanation, " What the claim expected:")
    if result.status.value == "insufficient_evidence" and result.expected_values:
        return "No normalized evidence record was found for the matching criteria below."
    return result.explanation


def _result_expected_values_heading(result: ValidationResult) -> str:
    if result.status.value == "insufficient_evidence":
        return "Matching criteria searched"
    return "Expected values"


def _before_first_marker(value: str, marker: str) -> str:
    if marker not in value:
        return value
    return value.split(marker, 1)[0].rstrip(" .") + "."


def _render_status_callout(st: Any, result: ValidationResult) -> None:
    if result.status.value == "supported":
        st.success(status_callout_text(result))
    elif result.status.value == "contradicted":
        st.error(status_callout_text(result))
    else:
        st.info(status_callout_text(result))


def _render_report_actions(st: Any, report: ValidationReport) -> None:
    st.subheader("Report exports")
    st.info(
        "Report exports are available here. "
        "The Markdown report includes full source and normalized SHA-256 hashes. "
        "The JSON report includes full provenance metadata for archival review."
    )
    markdown_column, json_column, print_column = st.columns(3)
    with markdown_column:
        st.download_button(
            "Download Markdown report",
            data=report.markdown_report,
            file_name="traceback-gui-v0-validation-report.md",
            mime="text/markdown",
        )
    with json_column:
        st.download_button(
            "Download JSON report",
            data=report.json_report,
            file_name="traceback-gui-v0-validation-report.json",
            mime="application/json",
        )
    with print_column:
        _render_print_button()


def _render_print_button() -> None:
    import streamlit as st

    st.iframe(
        """
        <style>
            html, body {
                margin: 0;
                overflow: hidden;
            }
        </style>
        <button onclick="window.parent.print()" style="
            background-color: #2563eb;
            border: 0;
            border-radius: 0.5rem;
            box-sizing: border-box;
            color: white;
            cursor: pointer;
            font-weight: 600;
            padding: 0.55rem 0.8rem;
            width: 100%;
        ">
            Print / Save as PDF
        </button>
        """,
        height=44,
        width=190,
    )


def _render_corrected_claim(st: Any, report: ValidationReport) -> None:
    if not report.corrected_claim:
        return

    st.subheader("Corrected claim")
    st.success(report.corrected_claim)


def _render_end_marker(st: Any) -> None:
    st.divider()
    st.markdown("**End of validation report**")


def _render_report_preview(st: Any, report: ValidationReport) -> None:
    with st.expander("Validation report preview", expanded=False):
        st.caption(
            "Optional quick review copy of the downloadable Markdown and JSON reports."
        )
        report_format = st.radio("Report preview", ["Markdown", "JSON"], horizontal=True)
        if report_format == "Markdown":
            st.code(report.markdown_report, language="markdown")
        else:
            st.code(report.json_report, language="json")


if __name__ == "__main__":
    main()
