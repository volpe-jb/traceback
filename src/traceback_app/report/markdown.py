"""Simple human-readable Markdown-style report formatting."""

from __future__ import annotations

from traceback_app.claims.schema import ValidationResult, ValidationStatus


def results_to_markdown(
    results: list[ValidationResult], *, title: str = "TraceBack Windows Logon Validation Summary"
) -> str:
    """Return a compact Markdown-style validation summary."""

    lines = [f"# {title}", ""]
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
                    lines.append("  - " + _format_inline_evidence_reference(reference, separator="="))
        lines.append("")
    return "\n".join(lines)


def _contradicted_result_lines(result: ValidationResult) -> list[str]:
    lines = [
        "- Claim checked:",
        f"  - {result.claim_text}",
        "- What the claim expected:",
    ]

    for key, value in result.expected_values.items():
        lines.append(f"  - expected_{key}: {value}")

    lines.append("- What the evidence shows:")
    for reference in result.evidence_references:
        lines.extend(_format_block_evidence_reference(reference))

    lines.extend(
        [
            "- Why this contradicts the claim:",
            f"  - {result.contradiction_reason}",
            "- Explanation:",
            f"  - {result.explanation}",
        ]
    )
    return lines


def _format_block_evidence_reference(reference: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for index, (key, value) in enumerate(reference.items()):
        prefix = "  -" if index == 0 else "   "
        lines.append(f"{prefix} {key}: {value}")
    return lines


def _format_inline_evidence_reference(reference: dict[str, object], *, separator: str) -> str:
    parts = []
    for key, value in reference.items():
        parts.append(f"{key}{separator}{value}")
    return ", ".join(parts)
