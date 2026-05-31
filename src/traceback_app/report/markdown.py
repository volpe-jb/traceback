"""Simple human-readable Markdown-style report formatting."""

from __future__ import annotations

from traceback_app.claims.schema import ValidationResult, ValidationStatus


def results_to_markdown(results: list[ValidationResult]) -> str:
    """Return a compact Markdown-style validation summary."""

    lines = ["# TraceBack Windows Logon Validation Summary", ""]
    for result in results:
        lines.extend(
            [
                f"## {result.claim_id}",
                f"- Status: {result.status.value}",
            ]
        )
        if result.status == ValidationStatus.CONTRADICTED:
            lines.extend(_contradicted_result_lines(result))
        else:
            lines.extend(
                [
                    f"- Claim: {result.claim_text}",
                    f"- Explanation: {result.explanation}",
                ]
            )
            if result.evidence_references:
                lines.append("- Evidence references:")
                for reference in result.evidence_references:
                    lines.append("  - " + _format_evidence_reference(reference, separator="="))
        lines.append("")
    return "\n".join(lines)


def _contradicted_result_lines(result: ValidationResult) -> list[str]:
    lines = [
        "- Claim checked:",
        f"  - {result.claim_text}",
        "- What the claim expected:",
        f"  - expected_event_action: {result.expected_values.get('event_action')}",
        f"  - expected_logon_type: {result.expected_values.get('logon_type')}",
        f"  - expected_logon_type_label: {result.expected_values.get('logon_type_label')}",
        "- What the evidence shows:",
    ]

    for reference in result.evidence_references:
        lines.extend(
            [
                f"  - event_uid: {reference.get('event_uid')}",
                f"    event_id: {reference.get('event_id')}",
                f"    timestamp_utc: {reference.get('timestamp_utc')}",
                f"    account: {reference.get('account')}",
                f"    host: {reference.get('host')}",
                f"    event_action: {reference.get('event_action')}",
                f"    logon_type: {reference.get('logon_type')}",
                f"    logon_type_label: {reference.get('logon_type_label')}",
            ]
        )

    lines.extend(
        [
            "- Why this contradicts the claim:",
            f"  - {result.contradiction_reason}",
            "- Explanation:",
            f"  - {result.explanation}",
        ]
    )
    return lines


def _format_evidence_reference(reference: dict[str, object], *, separator: str) -> str:
    return (
        f"event_uid{separator}{reference.get('event_uid')}, "
        f"event_id{separator}{reference.get('event_id')}, "
        f"timestamp_utc{separator}{reference.get('timestamp_utc')}, "
        f"account{separator}{reference.get('account')}, "
        f"host{separator}{reference.get('host')}, "
        f"event_action{separator}{reference.get('event_action')}, "
        f"logon_type{separator}{reference.get('logon_type')} "
        f"({reference.get('logon_type_label')})"
    )
