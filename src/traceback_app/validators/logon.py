"""Deterministic Windows logon claim validation."""

from __future__ import annotations

from typing import Any

from traceback_app.claims.schema import ValidationResult, ValidationStatus

LOGON_REFERENCE_FIELDS = (
    "event_uid",
    "event_id",
    "timestamp_utc",
    "account",
    "host",
    "event_action",
    "logon_type",
    "logon_type_label",
)


def validate_logon_claims(
    claims: list[dict[str, Any]], events: list[dict[str, Any]]
) -> list[ValidationResult]:
    """Validate Windows logon claims against normalized Windows logon events."""

    return [validate_logon_claim(claim, events) for claim in claims]


def validate_logon_claim(
    claim: dict[str, Any], events: list[dict[str, Any]]
) -> ValidationResult:
    """Validate one Windows logon claim against normalized event records.

    A claim is:
    - supported when account, host, timestamp, event action, and logon type match
    - contradicted when same account/host/timestamp exists but action or type differs
    - insufficient when no event exists for account/host/timestamp
    """

    claim_id = str(claim.get("claim_id", "unknown-claim"))
    claim_type = str(claim.get("claim_type", "windows_logon"))
    claim_text = str(claim.get("claim_text", ""))

    candidates = [event for event in events if _same_account_host_timestamp(claim, event)]

    if not candidates:
        return ValidationResult(
            claim_id=claim_id,
            claim_type=claim_type,
            claim_text=claim_text,
            status=ValidationStatus.INSUFFICIENT_EVIDENCE,
            explanation=(
                "No normalized Windows logon event was found for "
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
                "Supported by normalized Windows logon evidence: "
                f"event_uid={reference.get('event_uid')}, "
                f"event_id={reference.get('event_id')}, "
                f"timestamp_utc={reference.get('timestamp_utc')}, "
                f"account={reference.get('account')}, host={reference.get('host')}, "
                f"event_action={reference.get('event_action')}, "
                f"logon_type={reference.get('logon_type')} "
                f"({reference.get('logon_type_label')})."
            ),
            evidence_references=[reference],
        )

    conflicts = [_describe_conflict(claim, event) for event in candidates]
    return ValidationResult(
        claim_id=claim_id,
        claim_type=claim_type,
        claim_text=claim_text,
        status=ValidationStatus.CONTRADICTED,
        explanation=(
            "Contradicted by normalized Windows logon evidence for the same "
            "account, host, and timestamp: " + "; ".join(conflicts)
        ),
        evidence_references=references,
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
        and event.get("logon_type") == claim.get("expected_logon_type")
    )


def _build_evidence_reference(event: dict[str, Any]) -> dict[str, Any]:
    return {field: event.get(field) for field in LOGON_REFERENCE_FIELDS}


def _describe_conflict(claim: dict[str, Any], event: dict[str, Any]) -> str:
    reference = _build_evidence_reference(event)
    differences: list[str] = []

    if event.get("event_action") != claim.get("expected_event_action"):
        differences.append(
            f"expected event_action={claim.get('expected_event_action')} "
            f"but evidence has event_action={event.get('event_action')}"
        )

    if event.get("logon_type") != claim.get("expected_logon_type"):
        differences.append(
            f"expected logon_type={claim.get('expected_logon_type')} "
            f"({claim.get('expected_logon_type_label')}) but evidence has "
            f"logon_type={event.get('logon_type')} ({event.get('logon_type_label')})"
        )

    if not differences:
        differences.append("the event differs from the claim in an unspecified field")

    return (
        f"event_uid={reference.get('event_uid')}, "
        f"event_id={reference.get('event_id')}, "
        f"timestamp_utc={reference.get('timestamp_utc')}, "
        f"account={reference.get('account')}, host={reference.get('host')}, "
        f"event_action={reference.get('event_action')}, "
        f"logon_type={reference.get('logon_type')} "
        f"({reference.get('logon_type_label')}) -- "
        + ", ".join(differences)
    )
