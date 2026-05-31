"""Shared claim and validation result shapes for TraceBack."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ValidationStatus(StrEnum):
    """Allowed deterministic validation statuses."""

    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class ValidationResult:
    """A normalized result returned by a TraceBack validator."""

    claim_id: str
    claim_type: str
    claim_text: str
    status: ValidationStatus
    explanation: str
    evidence_references: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of this result."""

        return {
            "claim_id": self.claim_id,
            "claim_type": self.claim_type,
            "claim_text": self.claim_text,
            "status": self.status.value,
            "explanation": self.explanation,
            "evidence_references": self.evidence_references,
        }
