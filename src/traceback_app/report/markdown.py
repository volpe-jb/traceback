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
                    "- Claim:",
                    f"  - {result.claim_text}",
                    "- Explanation:",
                    f"  - {_human_summary(result)}",
                ]
            )
            if result.evidence_references:
                lines.append("- Evidence references:")
                for reference in result.evidence_references:
                    lines.extend(_format_key_value_table(reference))
        lines.append("")
    lines.extend(["---", "", "**End of validation report**", ""])
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

    lines.extend(
        _format_key_value_table(
            {f"expected_{key}": value for key, value in result.expected_values.items()}
        )
    )

    lines.append("- What the evidence actually shows:")
    for reference in result.evidence_references:
        lines.extend(_format_key_value_table(reference))

    lines.extend(
        [
            "- Why this contradicts the claim:",
            f"  - {result.contradiction_reason}",
            "- Explanation:",
            f"  - {_human_summary(result)}",
        ]
    )
    return lines


def _format_key_value_table(values: Mapping[str, object]) -> list[str]:
    lines = ["", "  | Field | Value |", "  | --- | --- |"]
    for key, value in values.items():
        lines.append(f"  | {_escape_table_cell(str(key))} | {_escape_table_cell(_format_value(value))} |")
    lines.append("")
    return lines


def _format_value(value: object) -> str:
    if value is None:
        return "None"
    return str(value)


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _human_summary(result: ValidationResult) -> str:
    if result.status == ValidationStatus.SUPPORTED:
        return _before_first_marker(result.explanation, ": ")
    if result.status == ValidationStatus.CONTRADICTED:
        return _before_first_marker(result.explanation, " What the claim expected:")
    return result.explanation


def _before_first_marker(value: str, marker: str) -> str:
    if marker not in value:
        return value
    return value.split(marker, 1)[0].rstrip(" .") + "."
