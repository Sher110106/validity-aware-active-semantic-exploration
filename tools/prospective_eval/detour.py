"""Fail-closed prospective detour intervention evaluator."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from .classification import EvidencePolicy
from .schema import Classification, stable_hash


@dataclass(frozen=True)
class InterventionRecord:
    snapshot_hash: str
    original_policy_input: Mapping[str, Any]
    fp_removed_policy_input: Mapping[str, Any]
    selected_target: Optional[str]
    live_reachability: Optional[bool]
    original_path_points: Sequence[Sequence[float]]
    alternative_path_points: Sequence[Sequence[float]]
    original_distance_m: Optional[float]
    alternative_distance_m: Optional[float]
    original_completion: str
    alternative_completion: str
    useful_observation_original: Optional[bool]
    useful_observation_alternative: Optional[bool]
    classification: Classification
    fp_dependence: bool

    def as_dict(self) -> dict:
        data = self.__dict__.copy()
        data["signed_distance_difference_m"] = (
            None if self.original_distance_m is None or self.alternative_distance_m is None
            else self.alternative_distance_m - self.original_distance_m
        )
        data["record_hash"] = stable_hash(data)
        return data


def evaluate_detour(record: InterventionRecord, policy: EvidencePolicy) -> str:
    evidence = {
        # ``confirmed_false_positive`` is itself the auditable, post-review
        # label; an unmatched/unknown label can never satisfy this gate.
        "reference_supported": record.classification == Classification.CONFIRMED_FALSE_POSITIVE,
        "counterfactual": record.fp_dependence,
        "executed_paths": bool(record.original_path_points) and bool(record.alternative_path_points),
        "shorter_alternative": (
            record.original_distance_m is not None
            and record.alternative_distance_m is not None
            and record.alternative_distance_m < record.original_distance_m
        ),
        "no_useful_observation_loss": record.useful_observation_alternative is True,
    }
    if record.classification == Classification.CONFIRMED_FALSE_POSITIVE and all(evidence.values()):
        return "false_positive_detour"
    if record.classification in {Classification.REFERENCE_UNMATCHED, Classification.UNKNOWN}:
        return "unknown"
    if evidence["executed_paths"] and evidence["shorter_alternative"]:
        return "tradeoff"
    return "not_identifiable"
