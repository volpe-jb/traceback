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
            "Contradicted by normalized Windows logon evidence for the same "
            "account, host, and timestamp. "
            f"What the claim expected: event_action={expected_values.get('event_action')}, "
            f"logon_type={expected_values.get('logon_type')} "
            f"({expected_values.get('logon_type_label')}). "
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
        and event.get("logon_type") == claim.get("expected_logon_type")
    )


def _build_evidence_reference(event: dict[str, Any]) -> dict[str, Any]:
    return {field: event.get(field) for field in LOGON_REFERENCE_FIELDS}


def _build_expected_values(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_action": claim.get("expected_event_action"),
        "logon_type": claim.get("expected_logon_type"),
        "logon_type_label": claim.get("expected_logon_type_label"),
    }


def _build_observed_values(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_action": event.get("event_action"),
        "logon_type": event.get("logon_type"),
        "logon_type_label": event.get("logon_type_label"),
    }


def _build_contradiction_reason(claim: dict[str, Any], events: list[dict[str, Any]]) -> str:
    reasons = [_plain_english_mismatch(claim, event) for event in events]
    unique_reasons = list(dict.fromkeys(reasons))
    return " ".join(unique_reasons)


def _plain_english_mismatch(claim: dict[str, Any], event: dict[str, Any]) -> str:
    expected_action = claim.get("expected_event_action")
    observed_action = event.get("event_action")
    expected_type = claim.get("expected_logon_type")
    observed_type = event.get("logon_type")
    expected_label = claim.get("expected_logon_type_label")
    observed_label = event.get("logon_type_label")

    if expected_action == "logon_success" and observed_action == "logon_failure":
        return (
            "The claim says the logon succeeded, but the matching Windows Security "
            "event is a failed logon event."
        )

    if expected_type == 2 and observed_type == 3:
        return (
            "The claim says this was an Interactive console logon, but the matching "
            "Windows Security event shows a Network logon."
        )

    if expected_type != observed_type:
        return (
            f"The claim says this was a {expected_label} logon, but the matching "
            f"Windows Security event shows a {observed_label} logon."
        )

    if expected_action != observed_action:
        return (
            f"The claim expected event_action={expected_action}, but the matching "
            f"Windows Security event shows event_action={observed_action}."
        )

    return "The matching Windows Security event conflicts with the claim."


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
