"""Simple human-readable Markdown-style report formatting."""

from __future__ import annotations

from collections.abc import Mapping

from traceback_app.claims.schema import ValidationResult, ValidationStatus


def results_to_markdown(
    results: list[ValidationResult],
    *,
    title: str = "TraceBack Windows Logon Validation Summary",
    provenance_metadata: Mapping[str, object] | None = None,
) -> str:
    """Return a compact Markdown-style validation summary."""

    lines = [f"# {title}", ""]
    if provenance_metadata is not None:
        lines.extend(_format_provenance_metadata(provenance_metadata, results))
        lines.append("")
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
                    lines.append(
                        "  - " + _format_inline_evidence_reference(reference, separator="=")
                    )
        lines.append("")
    return "\n".join(lines)


def _format_provenance_metadata(
    metadata: Mapping[str, object], results: list[ValidationResult]
) -> list[str]:
    parser_tool = metadata.get("parser_tool")
    parser_tool_version = metadata.get("parser_tool_version")
    parser_line = f"- Parser/extractor: {parser_tool}"
    if parser_tool_version:
        parser_line += f" (version {parser_tool_version})"

    status_counts = _count_result_statuses(results)
    lines = [
        "## Evidence provenance",
        f"- Source artifact: {metadata.get('source_artifact')}",
        f"- Source SHA-256: {metadata.get('source_sha256')}",
        f"- Normalized records: {metadata.get('normalized_file')}",
        f"- Normalized SHA-256: {metadata.get('normalized_sha256')}",
        parser_line,
        f"- Records examined: {metadata.get('record_count')}",
        f"- Supported: {status_counts[ValidationStatus.SUPPORTED]}",
        f"- Contradicted: {status_counts[ValidationStatus.CONTRADICTED]}",
        f"- Insufficient evidence: {status_counts[ValidationStatus.INSUFFICIENT_EVIDENCE]}",
    ]

    parser_output = metadata.get("parser_output")
    if parser_output:
        lines.append(f"- Parser-native output: {parser_output}")
        lines.append(
            f"- Parser-native output SHA-256: {metadata.get('parser_output_sha256')}"
        )

    return lines


def _count_result_statuses(results: list[ValidationResult]) -> dict[ValidationStatus, int]:
    return {status: sum(result.status == status for result in results) for status in ValidationStatus}


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
