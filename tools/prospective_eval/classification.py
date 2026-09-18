"""Conservative reference and false-positive classification."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .schema import Classification


@dataclass(frozen=True)
class EvidencePolicy:
    """Prerequisite evidence for a confirmed false positive."""

    requires_reference_supported: bool = True
    requires_counterfactual: bool = True
    requires_executed_paths: bool = True
    requires_shorter_alternative: bool = True
    requires_no_useful_observation_loss: bool = True


def classify_reference(*, reference_match: Optional[bool], physical_evidence: Optional[bool], policy: EvidencePolicy) -> Classification:
    if physical_evidence is True:
        return Classification.SUPPORTED
    if reference_match is False:
        # A vocabulary/reference mismatch is not evidence of absence.
        return Classification.REFERENCE_UNMATCHED
    return Classification.UNKNOWN


def can_confirm_false_positive(classification: Classification, evidence: dict, policy: EvidencePolicy) -> bool:
    required = {
        "reference_supported": policy.requires_reference_supported,
        "counterfactual": policy.requires_counterfactual,
        "executed_paths": policy.requires_executed_paths,
        "shorter_alternative": policy.requires_shorter_alternative,
        "no_useful_observation_loss": policy.requires_no_useful_observation_loss,
    }
    return classification == Classification.CONFIRMED_FALSE_POSITIVE and all(
        not needed or evidence.get(name) is True for name, needed in required.items()
    )
