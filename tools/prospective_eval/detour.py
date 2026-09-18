"""Receipt-verified exact-branch detour evaluation."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from .classification import EvidencePolicy, import_confirmed_false_positive
from .schema import Classification, EvidenceReceipt, Pose, position_error, stable_hash, _identifier, _timestamp


@dataclass(frozen=True)
class PathSample:
    timestamp: str
    segment_id: str
    pose: Pose


@dataclass(frozen=True)
class BranchEvidence:
    branch: str
    execution_id: str
    restore_receipt: EvidenceReceipt
    execution_receipt: EvidenceReceipt
    reachability_receipt: EvidenceReceipt
    target_id: str
    path_samples: Sequence[PathSample]
    completion_receipt: EvidenceReceipt
    useful_observation_receipt: EvidenceReceipt
    state_before_hash: str
    state_after_hash: str
    external_hashes: Mapping[str, str]


@dataclass(frozen=True)
class InterventionEvidence:
    snapshot_manifest: EvidenceReceipt
    fp_label_receipt: EvidenceReceipt
    original: BranchEvidence
    alternative: BranchEvidence
    common_policy_attribution: str
    expected_target_id: str
    expected_attribution: str


def _receipt(receipt: EvidenceReceipt, kind: str) -> Mapping[str, Any]:
    if not receipt.verify() or receipt.kind != kind:
        raise ValueError(f"invalid {kind} receipt")
    return receipt.payload


def _path_distance(samples: Sequence[PathSample]) -> float:
    if not samples:
        raise ValueError("complete executed path samples required")
    total = 0.0
    previous_time = None
    previous = None
    for sample in samples:
        _timestamp(sample.timestamp)
        _identifier(sample.segment_id, "segment_id")
        if previous_time is not None and sample.timestamp <= previous_time:
            raise ValueError("path timestamps must be strictly monotonic")
        if previous is not None:
            total += position_error(previous, sample.pose)
        previous_time, previous = sample.timestamp, sample.pose
    return total


def paired_policy_comparison(original: Sequence[PathSample], alternative: Sequence[PathSample], *, removed_nodes: Sequence[str]) -> dict:
    """Descriptive independent-trajectory comparison; never a causal FP claim."""
    return {"result": "not_identifiable", "original_distance_m": _path_distance(original), "alternative_distance_m": _path_distance(alternative), "distance_difference_m": _path_distance(alternative) - _path_distance(original), "removed_node_attribution": list(removed_nodes), "causal_false_positive_detour": "not_identifiable"}


def evaluate_intervention(evidence: InterventionEvidence, policy: EvidencePolicy) -> str:
    """Verify every receipt and recompute all quantities; fail closed on defects."""
    label = import_confirmed_false_positive(evidence.fp_label_receipt, policy)
    manifest = _receipt(evidence.snapshot_manifest, "snapshot_manifest")
    if not manifest.get("manifest_hash") or not evidence.snapshot_manifest.receipt_hash:
        raise ValueError("snapshot manifest hash mismatch")
    if evidence.common_policy_attribution != evidence.expected_attribution:
        return "not_identifiable"
    if evidence.original.target_id != evidence.expected_target_id or evidence.alternative.target_id != evidence.expected_target_id:
        return "not_identifiable"
    distances = []
    for branch in (evidence.original, evidence.alternative):
        restore = _receipt(branch.restore_receipt, "restore")
        execution = _receipt(branch.execution_receipt, "execution")
        reach = _receipt(branch.reachability_receipt, "reachability")
        completion = _receipt(branch.completion_receipt, "completion")
        useful = _receipt(branch.useful_observation_receipt, "useful_observation")
        if restore.get("branch") != branch.branch or restore.get("snapshot_manifest_hash") != manifest.get("manifest_hash"):
            return "not_identifiable"
        if execution.get("execution_id") != branch.execution_id or reach.get("execution_id") != branch.execution_id:
            return "not_identifiable"
        if execution.get("snapshot_manifest_hash") != manifest.get("manifest_hash"):
            return "not_identifiable"
        if execution.get("policy_attribution") != evidence.common_policy_attribution:
            return "not_identifiable"
        if execution.get("fp_removed") is not (branch.branch == "alternative"):
            return "not_identifiable"
        if reach.get("reachable") is not True or completion.get("completed") is not True:
            return "not_identifiable"
        if branch.state_before_hash != manifest.get("state_hash") or not branch.state_after_hash or not all(branch.external_hashes.get(key) for key in ("rng", "observation", "filesystem")):
            return "not_identifiable"
        if not completion.get("abort_reason") and completion.get("completed") is not True:
            return "not_identifiable"
        if useful.get("criterion_met") is not True:
            return "tradeoff"
        distances.append(_path_distance(branch.path_samples))
        claimed = execution.get("cumulative_distance_m")
        if not isinstance(claimed, (int, float)) or not math.isfinite(claimed) or abs(float(claimed) - distances[-1]) > 1e-9:
            raise ValueError("execution receipt distance does not match path samples")
    if distances[1] >= distances[0]:
        return "not_identifiable"
    return "false_positive_detour" if label == Classification.CONFIRMED_FALSE_POSITIVE else "unknown"
