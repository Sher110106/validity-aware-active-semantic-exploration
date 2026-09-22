"""Conservative reference labels and imported external FP evidence."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .schema import Classification, EvidenceReceipt


@dataclass(frozen=True)
class EvidencePolicy:
    allowed_reviewers: frozenset[str] = frozenset()
    require_reference_criterion: bool = True


def classify_reference(*, reference_match: Optional[bool], physical_evidence: Optional[bool], policy: EvidencePolicy) -> Classification:
    if physical_evidence is True:
        return Classification.SUPPORTED
    if reference_match is False:
        return Classification.REFERENCE_UNMATCHED
    return Classification.UNKNOWN


def import_confirmed_false_positive(receipt: EvidenceReceipt, policy: EvidencePolicy) -> Classification:
    """Import only a hashed external review receipt, never a free-form enum."""
    if not receipt.verify() or receipt.kind != "false_positive_label":
        raise ValueError("invalid false-positive evidence receipt")
    payload = receipt.payload
    if payload.get("label") != Classification.CONFIRMED_FALSE_POSITIVE.value:
        raise ValueError("receipt does not carry the confirmed FP label")
    reviewer = payload.get("reviewer_id")
    if not isinstance(reviewer, str) or (policy.allowed_reviewers and reviewer not in policy.allowed_reviewers):
        raise ValueError("reviewer is not allowlisted")
    if not payload.get("provenance_hash") or (policy.require_reference_criterion and not payload.get("reference_criterion")):
        raise ValueError("missing FP provenance or reference criterion")
    return Classification.CONFIRMED_FALSE_POSITIVE
