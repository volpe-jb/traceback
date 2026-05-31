"""Simple human-readable Markdown-style report formatting."""

from __future__ import annotations

from traceback_app.claims.schema import ValidationResult


def results_to_markdown(results: list[ValidationResult]) -> str:
    """Return a compact Markdown-style validation summary."""

    lines = ["# TraceBack Windows Logon Validation Summary", ""]
    for result in results:
        lines.extend(
            [
                f"## {result.claim_id}",
                f"- Status: {result.status.value}",
                f"- Claim: {result.claim_text}",
                f"- Explanation: {result.explanation}",
            ]
        )
        if result.evidence_references:
            lines.append("- Evidence references:")
            for reference in result.evidence_references:
                lines.append(
                    "  - "
                    f"event_uid={reference.get('event_uid')}, "
                    f"event_id={reference.get('event_id')}, "
                    f"timestamp_utc={reference.get('timestamp_utc')}, "
                    f"account={reference.get('account')}, "
                    f"host={reference.get('host')}, "
                    f"event_action={reference.get('event_action')}, "
                    f"logon_type={reference.get('logon_type')} "
                    f"({reference.get('logon_type_label')})"
                )
        lines.append("")
    return "\n".join(lines)
