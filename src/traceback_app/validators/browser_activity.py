"""Deterministic browser activity claim validation."""

from __future__ import annotations

from typing import Any

from traceback_app.claims.schema import ValidationResult, ValidationStatus

BROWSER_ACTIVITY_REFERENCE_FIELDS = (
    "event_uid",
    "timestamp_utc",
    "account",
    "host",
    "event_action",
    "activity_type",
    "browser",
    "url",
    "title",
    "download_name",
    "source_artifact",
    "artifact_type",
    "parser_tool",
)


def validate_browser_activity_claims(
    claims: list[dict[str, Any]], events: list[dict[str, Any]]
) -> list[ValidationResult]:
    """Validate browser activity claims against normalized browser records."""

    return [validate_browser_activity_claim(claim, events) for claim in claims]


def validate_browser_activity_claim(claim: dict[str, Any], events: list[dict[str, Any]]) -> ValidationResult:
    """Validate one browser activity claim.

    A claim is:
    - supported when account, host, timestamp, action, activity type, and URL match
    - contradicted when same account/host/timestamp exists but action, activity type, or URL differs
    - insufficient when no event exists for account/host/timestamp
    """

    claim_id = str(claim.get("claim_id", "unknown-claim"))
    claim_type = str(claim.get("claim_type", "browser_activity"))
    claim_text = str(claim.get("claim_text", ""))

    candidates = [event for event in events if _same_account_host_timestamp(claim, event)]

    if not candidates:
        return ValidationResult(
            claim_id=claim_id,
            claim_type=claim_type,
            claim_text=claim_text,
            status=ValidationStatus.INSUFFICIENT_EVIDENCE,
            explanation=(
                "No normalized browser activity event was found for "
                f"account={claim.get('account')}, host={claim.get('host')}, "
                f"timestamp_utc={claim.get('timestamp_utc')}."
            ),
            evidence_references=[],
            expected_values=_build_matching_criteria(claim),
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
                "Supported by normalized browser activity evidence: "
                f"event_uid={reference.get('event_uid')}, "
                f"timestamp_utc={reference.get('timestamp_utc')}, "
                f"account={reference.get('account')}, host={reference.get('host')}, "
                f"event_action={reference.get('event_action')}, "
                f"activity_type={reference.get('activity_type')}, "
                f"url={reference.get('url')}, "
                f"source_artifact={reference.get('source_artifact')}."
            ),
            evidence_references=[reference],
        )

    expected_values = _build_expected_values(claim)
    observed_values = [_build_observed_values(event) for event in candidates]
    conflicts = [_describe_conflict(claim, event) for event in candidates]
    contradiction_reason = _build_contradiction_reason(claim, candidates)
    return ValidationResult(
        claim_id=claim_id,
        claim_type=claim_type,
        claim_text=claim_text,
        status=ValidationStatus.CONTRADICTED,
        explanation=(
            "Contradicted by normalized browser activity evidence for the same account, host, and timestamp. "
            f"What the claim expected: event_action={expected_values.get('event_action')}, "
            f"activity_type={expected_values.get('activity_type')}, url={expected_values.get('url')}. "
            "What the evidence shows: "
            + "; ".join(conflicts)
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
        and event.get("activity_type") == claim.get("expected_activity_type")
        and _casefold(event.get("url")) == _casefold(claim.get("expected_url"))
    )


def _build_evidence_reference(event: dict[str, Any]) -> dict[str, Any]:
    return {field: event.get(field) for field in BROWSER_ACTIVITY_REFERENCE_FIELDS}


def _build_matching_criteria(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "account": claim.get("account"),
        "host": claim.get("host"),
        "timestamp_utc": claim.get("timestamp_utc"),
    }


def _build_expected_values(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_action": claim.get("expected_event_action"),
        "activity_type": claim.get("expected_activity_type"),
        "url": claim.get("expected_url"),
    }


def _build_observed_values(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_action": event.get("event_action"),
        "activity_type": event.get("activity_type"),
        "url": event.get("url"),
        "title": event.get("title"),
        "download_name": event.get("download_name"),
        "source_artifact": event.get("source_artifact"),
    }


def _build_contradiction_reason(claim: dict[str, Any], events: list[dict[str, Any]]) -> str:
    reasons = [_plain_english_mismatch(claim, event) for event in events]
    unique_reasons = list(dict.fromkeys(reasons))
    return " ".join(unique_reasons)


def _plain_english_mismatch(claim: dict[str, Any], event: dict[str, Any]) -> str:
    expected_action = claim.get("expected_event_action")
    observed_action = event.get("event_action")
    expected_activity = claim.get("expected_activity_type")
    observed_activity = event.get("activity_type")
    expected_url = claim.get("expected_url")
    observed_url = event.get("url")

    if expected_activity != observed_activity:
        return (
            f"The claim expected browser activity_type={expected_activity}, "
            f"but the matching evidence shows activity_type={observed_activity}."
        )

    if _casefold(expected_url) != _casefold(observed_url):
        return f"The claim says the browser activity involved {expected_url}, but the matching evidence shows {observed_url}."

    if expected_action != observed_action:
        return (
            f"The claim expected event_action={expected_action}, "
            f"but the matching browser evidence shows event_action={observed_action}."
        )

    return "The matching browser activity evidence conflicts with the claim."


def _describe_conflict(claim: dict[str, Any], event: dict[str, Any]) -> str:
    reference = _build_evidence_reference(event)
    differences: list[str] = []

    if event.get("event_action") != claim.get("expected_event_action"):
        differences.append(
            f"expected event_action={claim.get('expected_event_action')} "
            f"but evidence has event_action={event.get('event_action')}"
        )

    if event.get("activity_type") != claim.get("expected_activity_type"):
        differences.append(
            f"expected activity_type={claim.get('expected_activity_type')} "
            f"but evidence has activity_type={event.get('activity_type')}"
        )

    if _casefold(event.get("url")) != _casefold(claim.get("expected_url")):
        differences.append(f"expected url={claim.get('expected_url')} but evidence has url={event.get('url')}")

    if not differences:
        differences.append("the event differs from the claim in an unspecified field")

    return (
        f"event_uid={reference.get('event_uid')}, "
        f"timestamp_utc={reference.get('timestamp_utc')}, "
        f"account={reference.get('account')}, host={reference.get('host')}, "
        f"event_action={reference.get('event_action')}, "
        f"activity_type={reference.get('activity_type')}, "
        f"url={reference.get('url')}, "
        f"source_artifact={reference.get('source_artifact')} -- "
        + ", ".join(differences)
    )


def _casefold(value: object) -> str:
    return str(value or "").casefold()
