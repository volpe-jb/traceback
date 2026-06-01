"""Streamlit review/demo GUI for TraceBack validation.

Run with:
    uv run streamlit run streamlit_app.py
"""

from __future__ import annotations

from traceback_app.claims.schema import ValidationResult
from traceback_app.gui.adapters import (
    SAMPLE_CASES,
    ValidationReport,
    display_status_label,
    load_sample_case,
    validate_claim,
)


def main() -> None:
    """Render the thin Streamlit GUI over the deterministic validation core."""

    import streamlit as st

    st.set_page_config(page_title="TraceBack Review GUI v0", layout="wide")
    st.title("TraceBack Review GUI v0")
    st.caption(
        "Read-only review/demo layer over deterministic local validation. "
        "No LLM or API key is required."
    )

    case_key = st.selectbox(
        "Select sample case / evidence bundle",
        options=list(SAMPLE_CASES),
        format_func=lambda key: SAMPLE_CASES[key].name,
    )
    sample = load_sample_case(case_key)

    st.subheader("Original claim")
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
        _future_ai_placeholder(st)
        return

    _render_report_summary(st, report)
    _render_grouped_results(st, report)
    _render_corrected_claim(st, report)
    _render_report_exports(st, report)
    _future_ai_placeholder(st)


def _render_report_summary(st: object, report: ValidationReport) -> None:
    st.subheader("Validation summary")
    supported, contradicted, unsupported = st.columns(3)
    supported.metric("supported", report.status_counts.get("supported", 0))
    contradicted.metric("contradicted", report.status_counts.get("contradicted", 0))
    unsupported.metric("unsupported", report.status_counts.get("insufficient_evidence", 0))


def _render_grouped_results(st: object, report: ValidationReport) -> None:
    st.subheader("Evidence checks by type")
    for group_report in report.groups.values():
        with st.expander(group_report.label, expanded=True):
            for result in group_report.results:
                _render_result(st, result)


def _render_result(st: object, result: ValidationResult) -> None:
    status_label = display_status_label(result.status)
    st.markdown(f"### {result.claim_id}: `{status_label}`")
    st.write(result.claim_text)
    st.write(result.explanation)

    if result.contradiction_reason:
        st.markdown("**Why this contradicts the claim**")
        st.write(result.contradiction_reason)

    if result.expected_values:
        st.markdown("**Expected values**")
        st.json(result.expected_values, expanded=False)

    if result.observed_values:
        st.markdown("**Observed values**")
        st.json(result.observed_values, expanded=False)

    if result.evidence_references:
        st.markdown("**Evidence references**")
        st.dataframe(result.evidence_references, use_container_width=True)


def _render_corrected_claim(st: object, report: ValidationReport) -> None:
    st.subheader("Corrected claim")
    if report.corrected_claim:
        st.success(report.corrected_claim)
    else:
        st.write(
            "No standalone corrected claim is produced by the deterministic core yet. "
            "Use the contradicted result details above as the evidence-grounded correction path."
        )


def _render_report_exports(st: object, report: ValidationReport) -> None:
    st.subheader("Validation report")
    report_format = st.radio("Report view", ["Markdown", "JSON"], horizontal=True)
    if report_format == "Markdown":
        st.code(report.markdown_report, language="markdown")
        st.download_button(
            "Download Markdown report",
            data=report.markdown_report,
            file_name="traceback-gui-v0-validation-report.md",
            mime="text/markdown",
        )
    else:
        st.code(report.json_report, language="json")
        st.download_button(
            "Download JSON report",
            data=report.json_report,
            file_name="traceback-gui-v0-validation-report.json",
            mime="application/json",
        )


def _future_ai_placeholder(st: object) -> None:
    st.divider()
    st.caption(
        "Future optional reviewer layer placeholder: "
        "agent_review(claim, validation_report) -> RevisedClaim/Narrative. "
        "Not implemented in GUI v0."
    )


if __name__ == "__main__":
    main()
