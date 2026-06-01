"""Deterministic Windows Prefetch-style process execution claim validation."""

from __future__ import annotations

from typing import Any

from traceback_app.claims.schema import ValidationResult, ValidationStatus

PREFETCH_PROCESS_REFERENCE_FIELDS = (
    "event_uid",
    "timestamp_utc",
    "account",
    "host",
    "event_action",
    "process_name",
    "process_path",
    "source_artifact",
    "artifact_type",
    "parser_tool",
    "run_count",
)


def validate_prefetch_process_claims(
    claims: list[dict[str, Any]], events: list[dict[str, Any]]
) -> list[ValidationResult]:
    """Validate Prefetch-style process claims against normalized process events."""

    return [validate_prefetch_process_claim(claim, events) for claim in claims]


def validate_prefetch_process_claim(
    claim: dict[str, Any], events: list[dict[str, Any]]
) -> ValidationResult:
    """Validate one Prefetch-style process execution claim.

    A claim is:
    - supported when account, host, timestamp, action, and process name match
    - contradicted when same account/host/timestamp exists but action or process differs
    - insufficient when no event exists for account/host/timestamp
    """

    claim_id = str(claim.get("claim_id", "unknown-claim"))
    claim_type = str(claim.get("claim_type", "windows_prefetch_process_execution"))
    claim_text = str(claim.get("claim_text", ""))

    candidates = [event for event in events if _same_account_host_timestamp(claim, event)]

    if not candidates:
        return ValidationResult(
            claim_id=claim_id,
            claim_type=claim_type,
            claim_text=claim_text,
            status=ValidationStatus.INSUFFICIENT_EVIDENCE,
            explanation=(
                "No normalized Windows Prefetch-style process event was found for "
                f"account={claim.get('account')}, host={claim.get('host')}, "
                f"timestamp_utc={claim.get('timestamp_utc')}."
            ),
            evidence_references=[],
        )

    supported_event = next((event for event in candidates if _matches_expected_claim(claim, event)), None)
    references = [_build_evidence_reference(event) for event in candidates]

    if supported_event is not None:
        reference = _build_evidence_reference(supported_event)
        return ValidationResult(
            claim_id=claim_id,
            claim_type=claim_type,
            claim_text=claim_text,
            status=ValidationStatus.SUPPORTED,
            explanation=(
                "Supported by normalized Windows Prefetch-style process evidence: "
                f"event_uid={reference.get('event_uid')}, "
                f"timestamp_utc={reference.get('timestamp_utc')}, "
                f"account={reference.get('account')}, host={reference.get('host')}, "
                f"event_action={reference.get('event_action')}, "
                f"process_name={reference.get('process_name')}, "
                f"process_path={reference.get('process_path')}, "
                f"source_artifact={reference.get('source_artifact')}."
            ),
            evidence_references=[reference],
        )

    conflicts = [_describe_conflict(claim, event) for event in candidates]
    expected_values = _build_expected_values(claim)
    observed_values = [_build_observed_values(event) for event in candidates]
    contradiction_reason = _build_contradiction_reason(claim, candidates)
    return ValidationResult(
        claim_id=claim_id,
        claim_type=claim_type,
        claim_text=claim_text,
        status=ValidationStatus.CONTRADICTED,
        explanation=(
            f"Claim checked: {claim_text} "
            "Contradicted by normalized Windows Prefetch-style process evidence "
            "for the same account, host, and timestamp. "
            f"What the claim expected: event_action={expected_values.get('event_action')}, "
            f"process_name={expected_values.get('process_name')}. "
            "What the evidence shows: "
            + "; ".join(conflicts)
            + f" Why this contradicts the claim: {contradiction_reason}"
        ),
        evidence_references=references,
        expected_values=expected_values,
        observed_values=observed_values,
        contradiction_reason=contradiction_reason,
    )


def _same_account_host_timestamp(claim: dict[str, Any], event: dict[str, Any]) -> bool:
    return (
        event.get("account") == claim.get("account")
        and event.get("host") == claim.get("host")
        and event.get("timestamp_utc") == claim.get("timestamp_utc")
    )


def _matches_expected_claim(claim: dict[str, Any], event: dict[str, Any]) -> bool:
    return (
        event.get("event_action") == claim.get("expected_event_action")
        and _casefold(event.get("process_name")) == _casefold(claim.get("expected_process_name"))
    )


def _build_evidence_reference(event: dict[str, Any]) -> dict[str, Any]:
    return {field: event.get(field) for field in PREFETCH_PROCESS_REFERENCE_FIELDS}


def _build_expected_values(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_action": claim.get("expected_event_action"),
        "process_name": claim.get("expected_process_name"),
    }


def _build_observed_values(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_action": event.get("event_action"),
        "process_name": event.get("process_name"),
        "process_path": event.get("process_path"),
        "source_artifact": event.get("source_artifact"),
    }


def _build_contradiction_reason(claim: dict[str, Any], events: list[dict[str, Any]]) -> str:
    reasons = [_plain_english_mismatch(claim, event) for event in events]
    unique_reasons = list(dict.fromkeys(reasons))
    return " ".join(unique_reasons)


def _plain_english_mismatch(claim: dict[str, Any], event: dict[str, Any]) -> str:
    expected_action = claim.get("expected_event_action")
    observed_action = event.get("event_action")
    expected_process = claim.get("expected_process_name")
    observed_process = event.get("process_name")

    if expected_action == "process_executed" and observed_action == "prefetch_absent":
        return (
            "A matching normalized Prefetch record exists for this account, host, "
            "and timestamp, but it records event_action=prefetch_absent instead of "
            "process_executed. Because the evidence directly conflicts with the claim, "
            "TraceBack marks this as contradicted rather than unsupported."
        )

    if _casefold(expected_process) != _casefold(observed_process):
        return (
            f"The claim says {expected_process} executed, but the matching "
            f"Prefetch-style evidence shows {observed_process}."
        )

    if expected_action != observed_action:
        return (
            f"The claim expected event_action={expected_action}, but the matching "
            f"Prefetch-style evidence shows event_action={observed_action}."
        )

    return "The matching Prefetch-style process evidence conflicts with the claim."


def _describe_conflict(claim: dict[str, Any], event: dict[str, Any]) -> str:
    reference = _build_evidence_reference(event)
    differences: list[str] = []

    if event.get("event_action") != claim.get("expected_event_action"):
        differences.append(
            f"expected event_action={claim.get('expected_event_action')} "
            f"but evidence has event_action={event.get('event_action')}"
        )

    if _casefold(event.get("process_name")) != _casefold(claim.get("expected_process_name")):
        differences.append(
            f"expected process_name={claim.get('expected_process_name')} "
            f"but evidence has process_name={event.get('process_name')}"
        )

    if not differences:
        differences.append("the event differs from the claim in an unspecified field")

    return (
        f"event_uid={reference.get('event_uid')}, "
        f"timestamp_utc={reference.get('timestamp_utc')}, "
        f"account={reference.get('account')}, host={reference.get('host')}, "
        f"event_action={reference.get('event_action')}, "
        f"process_name={reference.get('process_name')}, "
        f"process_path={reference.get('process_path')}, "
        f"source_artifact={reference.get('source_artifact')} -- "
        + ", ".join(differences)
    )


def _casefold(value: object) -> str:
    return str(value or "").casefold()
