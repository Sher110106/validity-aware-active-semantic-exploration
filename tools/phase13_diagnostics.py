#!/usr/bin/env python3
"""Reproduce the remaining Phase 13 diagnostics from frozen ASP artifacts.

The report deliberately distinguishes measurements from unavailable outcomes.
In particular, cached decision replay has no counterfactual trajectory and the
pinned live controller did not record robot-contact events.  Planner failures,
LLM object-placement collision checks, and selected-pose displacement are not
renamed as false-positive detours or robot collisions.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from asp_offline.author_io import load_author_graph
from asp_offline.calibration import fit_leave_one_scene_out
from asp_offline.evaluator import evaluate_graph
from asp_offline.models import Node
from asp_offline.support_policy import collect_calibration_samples
from asp_offline.validator import ValidationConfig, validate_completion


EXPECTED_ENSEMBLE_SIZE = 4
RELIABILITY_BIN_COUNT = 10
F1_MAX_ABSOLUTE_LOSS = 0.05
GED_MAX_RELATIVE_INCREASE = 0.10
COMBINED_STATIC_POLICY = "filter_plus_support_threshold_calibrated_tau_1.0"

CALIBRATION_SCENES = {
    "00069": {
        "run": "runs/scene00069_seed42_25m_20260914_v3/stages",
        "reference": "runs/scene00069_frontier_reference/stages/25/habitat_scene_graph_original_graph0.yaml",
    },
    "00573": {
        "run": "runs/scene00573_seed42_calib_high32k/stages",
        "reference": "runs/scene00573_frontier_reference/stages/53/habitat_scene_graph_original_graph0.yaml",
    },
    "00853": {
        "run": "runs/scene00853_seed42_calib_high32k/stages",
        "reference": "runs/scene00853_frontier_reference/stages/33/habitat_scene_graph_original_graph0.yaml",
    },
    "00871": {
        "run": "runs/scene00871_seed42_calib_high32k/stages",
        "reference": "runs/scene00871_frontier_reference/stages/54/habitat_scene_graph_original_graph0.yaml",
    },
}

MATRIX_SCENES = {
    "00069": {
        "run": "runs/scene00069_seed42_matrix120m",
        "reference": "runs/scene00069_frontier_reference/stages/25/habitat_scene_graph_original_graph0.yaml",
        "static": "runs/matrix120m_scoring/scene00069_extension_policy_replay.json",
        "decision": "runs/matrix120m_scoring/null_v3_00069_workdir/decision_replay_scene00069_matrix120m_null_v3.json",
    },
    "00573": {
        "run": "runs/scene00573_seed42_matrix120m",
        "reference": "runs/scene00573_frontier_reference/stages/53/habitat_scene_graph_original_graph0.yaml",
        "static": "runs/matrix120m_scoring/scene00573_extension_policy_replay.json",
        "decision": "runs/matrix120m_scoring/null_v3_00573_workdir/decision_replay_scene00573_matrix120m_null_v3.json",
    },
    "00853": {
        "run": "runs/scene00853_seed42_matrix120m",
        "reference": "runs/scene00853_frontier_reference/stages/33/habitat_scene_graph_original_graph0.yaml",
        "static": "runs/matrix120m_scoring/scene00853_extension_policy_replay.json",
        "decision": "runs/matrix120m_scoring/null_v3_00853_workdir/decision_replay_scene00853_matrix120m_null_v3.json",
    },
}


def _checked_probability_rows(
    predictions: Sequence[float], labels: Sequence[int]
) -> Tuple[List[float], List[int]]:
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must have equal length")
    checked_predictions: List[float] = []
    checked_labels: List[int] = []
    for prediction, label in zip(predictions, labels):
        p = float(prediction)
        y = int(label)
        if not math.isfinite(p) or not 0.0 <= p <= 1.0:
            raise ValueError(f"prediction outside [0, 1]: {prediction!r}")
        if y not in (0, 1):
            raise ValueError(f"label must be binary: {label!r}")
        checked_predictions.append(p)
        checked_labels.append(y)
    return checked_predictions, checked_labels


def brier_score(predictions: Sequence[float], labels: Sequence[int]) -> float:
    predictions, labels = _checked_probability_rows(predictions, labels)
    if not predictions:
        raise ValueError("Brier score requires at least one sample")
    return sum((prediction - label) ** 2 for prediction, label in zip(predictions, labels)) / len(predictions)


def reliability_bins(
    predictions: Sequence[float],
    labels: Sequence[int],
    *,
    n_bins: int = RELIABILITY_BIN_COUNT,
) -> List[Dict[str, Any]]:
    predictions, labels = _checked_probability_rows(predictions, labels)
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")
    grouped: List[List[Tuple[float, int]]] = [[] for _ in range(n_bins)]
    for prediction, label in zip(predictions, labels):
        index = min(int(prediction * n_bins), n_bins - 1)
        grouped[index].append((prediction, label))

    bins: List[Dict[str, Any]] = []
    for index, rows in enumerate(grouped):
        count = len(rows)
        mean_prediction = sum(prediction for prediction, _ in rows) / count if count else None
        fraction_positive = sum(label for _, label in rows) / count if count else None
        bins.append(
            {
                "index": index,
                "lower": index / n_bins,
                "upper": (index + 1) / n_bins,
                "upper_inclusive": index == n_bins - 1,
                "count": count,
                "mean_prediction": mean_prediction,
                "fraction_positive": fraction_positive,
                "absolute_gap": (
                    abs(mean_prediction - fraction_positive) if count else None
                ),
            }
        )
    return bins


def calibration_metrics(
    predictions: Sequence[float],
    labels: Sequence[int],
    *,
    n_bins: int = RELIABILITY_BIN_COUNT,
) -> Dict[str, Any]:
    predictions, labels = _checked_probability_rows(predictions, labels)
    if not predictions:
        return {
            "status": "unavailable_no_samples",
            "n": 0,
            "positives": 0,
            "positive_rate": None,
            "brier": None,
            "ece": None,
            "bins": reliability_bins([], [], n_bins=n_bins),
        }
    bins = reliability_bins(predictions, labels, n_bins=n_bins)
    ece = sum(row["count"] * row["absolute_gap"] for row in bins if row["count"]) / len(predictions)
    return {
        "status": "measured",
        "n": len(predictions),
        "positives": sum(labels),
        "positive_rate": sum(labels) / len(labels),
        "brier": brier_score(predictions, labels),
        "ece": ece,
        "bins": bins,
    }


def build_calibration_diagnostics(
    scene_samples: Mapping[str, Sequence[Tuple[float, int, str]]],
    *,
    n_bins: int = RELIABILITY_BIN_COUNT,
) -> Dict[str, Any]:
    pooled_samples = {
        scene: [(support, label) for support, label, _ in triples]
        for scene, triples in scene_samples.items()
    }
    folds = fit_leave_one_scene_out(pooled_samples)
    per_scene: Dict[str, Any] = {}
    aggregate_rows: Dict[str, Dict[str, List[Any]]] = {
        subset: {"raw": [], "calibrated": [], "baseline": [], "labels": []}
        for subset in ("overall", "object", "room")
    }

    for scene in scene_samples:
        triples = list(scene_samples[scene])
        fold = folds[scene]
        labels = [int(label) for _, label, _ in triples]
        if labels != list(fold.labels):
            raise AssertionError(f"{scene}: LOSO labels drifted from sample order")
        calibrated = list(fold.predictions)
        raw = [float(support) for support, _, _ in triples]
        subsets: Dict[str, Any] = {}
        for subset in ("overall", "object", "room"):
            indices = [
                index
                for index, (_, _, kind) in enumerate(triples)
                if subset == "overall" or kind == subset
            ]
            subset_raw = [raw[index] for index in indices]
            subset_calibrated = [calibrated[index] for index in indices]
            subset_labels = [labels[index] for index in indices]
            training_labels = [
                int(label)
                for other_scene, other_triples in scene_samples.items()
                if other_scene != scene
                for _, label, kind in other_triples
                if subset == "overall" or kind == subset
            ]
            training_prevalence = (
                sum(training_labels) / len(training_labels) if training_labels else None
            )
            subset_baseline = (
                [training_prevalence] * len(indices)
                if training_prevalence is not None
                else []
            )
            raw_metrics = calibration_metrics(subset_raw, subset_labels, n_bins=n_bins)
            calibrated_metrics = calibration_metrics(
                subset_calibrated, subset_labels, n_bins=n_bins
            )
            baseline_metrics = calibration_metrics(
                subset_baseline,
                subset_labels if training_prevalence is not None else [],
                n_bins=n_bins,
            )
            subsets[subset] = {
                "raw": raw_metrics,
                "calibrated": calibrated_metrics,
                "training_prevalence_baseline": baseline_metrics,
                "training_prevalence": training_prevalence,
                "brier_delta_calibrated_minus_raw": (
                    calibrated_metrics["brier"] - raw_metrics["brier"]
                    if raw_metrics["brier"] is not None
                    and calibrated_metrics["brier"] is not None
                    else None
                ),
                "ece_delta_calibrated_minus_raw": (
                    calibrated_metrics["ece"] - raw_metrics["ece"]
                    if raw_metrics["ece"] is not None
                    and calibrated_metrics["ece"] is not None
                    else None
                ),
                "brier_delta_calibrated_minus_training_prevalence": (
                    calibrated_metrics["brier"] - baseline_metrics["brier"]
                    if calibrated_metrics["brier"] is not None
                    and baseline_metrics["brier"] is not None
                    else None
                ),
            }
            aggregate_rows[subset]["raw"].extend(subset_raw)
            aggregate_rows[subset]["calibrated"].extend(subset_calibrated)
            aggregate_rows[subset]["baseline"].extend(subset_baseline)
            aggregate_rows[subset]["labels"].extend(subset_labels)

        per_scene[scene] = {
            "trained_on_scenes": sorted(set(scene_samples) - {scene}),
            "subsets": subsets,
        }

    aggregate: Dict[str, Any] = {}
    for subset, rows in aggregate_rows.items():
        raw_metrics = calibration_metrics(rows["raw"], rows["labels"], n_bins=n_bins)
        calibrated_metrics = calibration_metrics(
            rows["calibrated"], rows["labels"], n_bins=n_bins
        )
        baseline_metrics = calibration_metrics(
            rows["baseline"], rows["labels"], n_bins=n_bins
        )
        aggregate[subset] = {
            "raw": raw_metrics,
            "calibrated": calibrated_metrics,
            "training_prevalence_baseline": baseline_metrics,
            "brier_delta_calibrated_minus_raw": (
                calibrated_metrics["brier"] - raw_metrics["brier"]
                if raw_metrics["brier"] is not None
                and calibrated_metrics["brier"] is not None
                else None
            ),
            "ece_delta_calibrated_minus_raw": (
                calibrated_metrics["ece"] - raw_metrics["ece"]
                if raw_metrics["ece"] is not None
                and calibrated_metrics["ece"] is not None
                else None
            ),
            "brier_delta_calibrated_minus_training_prevalence": (
                calibrated_metrics["brier"] - baseline_metrics["brier"]
                if calibrated_metrics["brier"] is not None
                and baseline_metrics["brier"] is not None
                else None
            ),
        }

    return {
        "method": "leave_one_scene_out_isotonic",
        "fit_population": "pooled_room_and_object_hypotheses",
        "evaluation": "held_out_predictions_only",
        "baseline": (
            "constant probability equal to the matching subset's prevalence "
            "in the other three training scenes; no held-out labels enter it"
        ),
        "ece_definition": {
            "bins": n_bins,
            "mode": "equal_width",
            "intervals": "[lower, upper), except final bin includes 1.0",
            "formula": "sum_bin(n_bin / n * abs(mean_prediction - fraction_positive))",
        },
        "caveat": (
            "The fitted map is pooled across room and object hypotheses. "
            "Object/room splits below diagnose that pooled map; they are not "
            "separately fitted per-kind calibrators."
        ),
        "per_scene": per_scene,
        "aggregate": aggregate,
    }


def pairwise_jaccard_diversity(semantic_sets: Sequence[Set[Tuple[str, str]]]) -> Optional[float]:
    if len(semantic_sets) < 2:
        return None
    distances: List[float] = []
    for left_index in range(len(semantic_sets)):
        for right_index in range(left_index + 1, len(semantic_sets)):
            left, right = semantic_sets[left_index], semantic_sets[right_index]
            union = left | right
            distances.append(1.0 - len(left & right) / len(union) if union else 0.0)
    return sum(distances) / len(distances)


def _new_nodes(graph: Mapping[str, Any], observed_ids: Set[str]) -> List[Node]:
    nodes = []
    for raw in graph.get("nodes", []):
        if not isinstance(raw, Mapping):
            continue
        node = Node.from_mapping(raw)
        if node.id not in observed_ids:
            nodes.append(node)
    return nodes


def _semantic_set(nodes: Iterable[Node]) -> Set[Tuple[str, str]]:
    return {
        (node.type.strip().casefold(), node.label.strip().casefold())
        for node in nodes
        if node.type in {"object", "room"} and node.label.strip()
    }


def collect_validation_diagnostics(run_dir: Path, reference_path: Path) -> Dict[str, Any]:
    reference = load_author_graph(reference_path, observed=True)
    config = ValidationConfig(allow_parsed_mapping=True)
    totals: Counter[str] = Counter()
    issues: Counter[str] = Counter()
    diversity_before: List[float] = []
    diversity_after: List[float] = []
    stage_tracks = 0

    stages_dir = run_dir / "stages" if (run_dir / "stages").is_dir() else run_dir
    stage_dirs = sorted(
        (path for path in stages_dir.iterdir() if path.is_dir() and path.name.isdigit()),
        key=lambda path: int(path.name),
    )
    completed_stage_dirs = [
        stage_dir
        for stage_dir in stage_dirs
        if (stage_dir / "path_log.json").exists()
        and (stage_dir / "navigation_stats.json").exists()
    ]
    for stage_dir in completed_stage_dirs:
        for scene_index in (0, 1):
            observed_path = stage_dir / f"habitat_scene_graph_original_graph{scene_index}.yaml"
            if not observed_path.exists():
                continue
            stage_tracks += 1
            observed = load_author_graph(observed_path, observed=True)
            observed_ids = {str(node["id"]) for node in observed.get("nodes", [])}
            before_sets: List[Set[Tuple[str, str]]] = []
            after_sets: List[Set[Tuple[str, str]]] = []
            lo = scene_index * EXPECTED_ENSEMBLE_SIZE
            for graph_id in range(lo, lo + EXPECTED_ENSEMBLE_SIZE):
                totals["expected_completions"] += 1
                completion_path = stage_dir / f"habitat_scene_graph_new_graph_{graph_id}.yaml"
                if not completion_path.exists():
                    totals["missing_completions"] += 1
                    continue
                totals["available_completions"] += 1
                completion = load_author_graph(completion_path)
                predicted_nodes = _new_nodes(completion, observed_ids)
                totals["predicted_nodes"] += len(predicted_nodes)
                before_sets.append(_semantic_set(predicted_nodes))

                # Survivor recall is about the LLM hypotheses, not the unchanged
                # observed map.  Evaluate predicted-only graphs on both sides.
                # Re-running the evaluator after filtering also lets an equivalent
                # surviving duplicate rematch a reference node instead of pinning
                # truth to whichever duplicate happened to match first before the
                # validator acted.
                before_prediction_graph = {
                    "nodes": [node.as_dict() for node in predicted_nodes],
                    "edges": [],
                }
                before_metrics = evaluate_graph(before_prediction_graph, reference)
                before_object_count = sum(node.type == "object" for node in predicted_nodes)
                before_room_count = sum(node.type == "room" for node in predicted_nodes)

                result = validate_completion(completion, observed, config)
                totals["accepted_completions"] += int(result.accepted)
                totals["rejected_completions"] += int(result.rejected)
                issues.update(issue.code for issue in result.issues)
                removed_ids = {str(node_id) for node_id in result.removed_nodes}
                totals["structurally_invalid_predicted_nodes"] += len(removed_ids)
                survivor_nodes = _new_nodes(result.graph, observed_ids)
                totals["surviving_predicted_nodes"] += len(survivor_nodes)
                totals["validator_excluded_predicted_nodes"] += max(
                    0, len(predicted_nodes) - len(survivor_nodes)
                )
                after_sets.append(_semantic_set(survivor_nodes))
                after_prediction_graph = {
                    "nodes": [node.as_dict() for node in survivor_nodes],
                    "edges": [],
                }
                after_metrics = evaluate_graph(after_prediction_graph, reference)
                after_object_count = sum(node.type == "object" for node in survivor_nodes)
                after_room_count = sum(node.type == "room" for node in survivor_nodes)

                for kind, before_count, after_count in (
                    ("object", before_object_count, after_object_count),
                    ("room", before_room_count, after_room_count),
                ):
                    before_tp = int(before_metrics[f"{kind}_tp"])
                    after_tp = int(after_metrics[f"{kind}_tp"])
                    totals[f"{kind}_predicted_nodes_before"] += before_count
                    totals[f"{kind}_predicted_nodes_after"] += after_count
                    totals[f"{kind}_true_positives_before"] += before_tp
                    totals[f"{kind}_true_positives_after"] += after_tp
                    totals[f"{kind}_false_positives_before"] += max(0, before_count - before_tp)
                    totals[f"{kind}_false_positives_after"] += max(0, after_count - after_tp)

            before = pairwise_jaccard_diversity(before_sets)
            after = pairwise_jaccard_diversity(after_sets)
            if before is not None:
                diversity_before.append(before)
            if after is not None:
                diversity_after.append(after)

    expected = totals["expected_completions"]
    available = totals["available_completions"]
    predicted_nodes = totals["predicted_nodes"]
    aggregate = dict(sorted(totals.items()))
    aggregate.update(
        {
            "completion_availability_rate": available / expected if expected else None,
            "accepted_completion_rate_of_expected": totals["accepted_completions"] / expected if expected else None,
            "accepted_completion_rate_of_available": totals["accepted_completions"] / available if available else None,
            "predicted_node_survival_rate": totals["surviving_predicted_nodes"] / predicted_nodes if predicted_nodes else None,
            "object_true_positive_retention": totals["object_true_positives_after"] / totals["object_true_positives_before"] if totals["object_true_positives_before"] else None,
            "room_true_positive_retention": totals["room_true_positives_after"] / totals["room_true_positives_before"] if totals["room_true_positives_before"] else None,
            "object_false_positive_removal_rate": (totals["object_false_positives_before"] - totals["object_false_positives_after"]) / totals["object_false_positives_before"] if totals["object_false_positives_before"] else None,
            "room_false_positive_removal_rate": (totals["room_false_positives_before"] - totals["room_false_positives_after"]) / totals["room_false_positives_before"] if totals["room_false_positives_before"] else None,
            "mean_pairwise_semantic_jaccard_diversity_before": sum(diversity_before) / len(diversity_before) if diversity_before else None,
            "mean_pairwise_semantic_jaccard_diversity_after": sum(diversity_after) / len(diversity_after) if diversity_after else None,
            "defined_diversity_tracks_before": len(diversity_before),
            "defined_diversity_tracks_after": len(diversity_after),
        }
    )
    return {
        "run_dir": str(run_dir),
        "reference": str(reference_path),
        "stages": len(completed_stage_dirs),
        "excluded_incomplete_stage_directories": len(stage_dirs) - len(completed_stage_dirs),
        "stage_tracks": stage_tracks,
        "aggregate": aggregate,
        "issue_counts": dict(sorted(issues.items())),
        "definitions": {
            "completion_validity": "accepted completions / expected four-member scene-track slots; missing members remain in the denominator",
            "survivor_recall": "sum of evaluator-matched true positives in predicted-only graphs after validation / sum before validation; the unchanged observed map is excluded and matching is recomputed after filtering so an equivalent surviving duplicate can replace a removed node",
            "diversity": "mean pairwise Jaccard distance between per-completion sets of case-folded (kind, label), macro-averaged over stage-tracks",
            "defined_diversity_tracks": "number of stage-tracks with at least two available completions; only these tracks define a pairwise diversity value and are used to weight the cross-scene aggregate",
        },
    }


def aggregate_validation_diagnostics(per_scene: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    summed: Counter[str] = Counter()
    issue_counts: Counter[str] = Counter()
    weighted_diversity_before: List[Tuple[float, int]] = []
    weighted_diversity_after: List[Tuple[float, int]] = []
    derived_keys = {
        "completion_availability_rate",
        "accepted_completion_rate_of_expected",
        "accepted_completion_rate_of_available",
        "predicted_node_survival_rate",
        "object_true_positive_retention",
        "room_true_positive_retention",
        "object_false_positive_removal_rate",
        "room_false_positive_removal_rate",
        "mean_pairwise_semantic_jaccard_diversity_before",
        "mean_pairwise_semantic_jaccard_diversity_after",
        "defined_diversity_tracks_before",
        "defined_diversity_tracks_after",
    }
    for result in per_scene.values():
        aggregate = result["aggregate"]
        for key, value in aggregate.items():
            if key not in derived_keys and isinstance(value, int):
                summed[key] += value
        issue_counts.update(result["issue_counts"])
        before_weight = int(aggregate["defined_diversity_tracks_before"])
        after_weight = int(aggregate["defined_diversity_tracks_after"])
        before = aggregate["mean_pairwise_semantic_jaccard_diversity_before"]
        after = aggregate["mean_pairwise_semantic_jaccard_diversity_after"]
        if before is not None:
            weighted_diversity_before.append((before, before_weight))
        if after is not None:
            weighted_diversity_after.append((after, after_weight))

    def ratio(numerator: str, denominator: str) -> Optional[float]:
        return summed[numerator] / summed[denominator] if summed[denominator] else None

    def weighted(rows: Sequence[Tuple[float, int]]) -> Optional[float]:
        denominator = sum(weight for _, weight in rows)
        return sum(value * weight for value, weight in rows) / denominator if denominator else None

    aggregate = dict(sorted(summed.items()))
    aggregate.update(
        {
            "completion_availability_rate": ratio("available_completions", "expected_completions"),
            "accepted_completion_rate_of_expected": ratio("accepted_completions", "expected_completions"),
            "accepted_completion_rate_of_available": ratio("accepted_completions", "available_completions"),
            "predicted_node_survival_rate": ratio("surviving_predicted_nodes", "predicted_nodes"),
            "object_true_positive_retention": ratio("object_true_positives_after", "object_true_positives_before"),
            "room_true_positive_retention": ratio("room_true_positives_after", "room_true_positives_before"),
            "object_false_positive_removal_rate": (summed["object_false_positives_before"] - summed["object_false_positives_after"]) / summed["object_false_positives_before"] if summed["object_false_positives_before"] else None,
            "room_false_positive_removal_rate": (summed["room_false_positives_before"] - summed["room_false_positives_after"]) / summed["room_false_positives_before"] if summed["room_false_positives_before"] else None,
            "mean_pairwise_semantic_jaccard_diversity_before": weighted(weighted_diversity_before),
            "mean_pairwise_semantic_jaccard_diversity_after": weighted(weighted_diversity_after),
            "defined_diversity_tracks_before": sum(weight for _, weight in weighted_diversity_before),
            "defined_diversity_tracks_after": sum(weight for _, weight in weighted_diversity_after),
        }
    )
    return {
        "per_scene": dict(per_scene),
        "aggregate": aggregate,
        "issue_counts": dict(sorted(issue_counts.items())),
    }


def evaluate_guardrails(
    static_results: Mapping[str, Mapping[str, Any]],
    validation_diagnostics: Mapping[str, Any],
) -> Dict[str, Any]:
    per_scene: Dict[str, Any] = {}
    for scene, payload in static_results.items():
        budget = payload.get("path_normalized_auc_capped_budget_m")
        if budget != 120.0:
            raise ValueError(f"{scene}: expected a 120.0 m capped AUC, found {budget!r}")
        auc = payload.get("path_normalized_auc_capped") or {}
        if "official" not in auc or COMBINED_STATIC_POLICY not in auc:
            raise ValueError(f"{scene}: missing official or {COMBINED_STATIC_POLICY} capped AUC")
        official = auc["official"]
        combined = auc[COMBINED_STATIC_POLICY]
        f1_loss = float(official["object_f1"]) - float(combined["object_f1"])
        official_ged = float(official["normalized_ged"])
        ged_relative_increase = (
            (float(combined["normalized_ged"]) - official_ged) / official_ged
            if official_ged
            else None
        )
        f1_passed = f1_loss <= F1_MAX_ABSOLUTE_LOSS + 1e-12
        ged_passed = (
            ged_relative_increase is not None
            and ged_relative_increase <= GED_MAX_RELATIVE_INCREASE + 1e-12
        )
        per_scene[scene] = {
            "official_object_f1_auc": official["object_f1"],
            "combined_object_f1_auc": combined["object_f1"],
            "absolute_f1_loss": f1_loss,
            "f1_passed": f1_passed,
            "official_normalized_ged_auc": official["normalized_ged"],
            "combined_normalized_ged_auc": combined["normalized_ged"],
            "relative_ged_increase": ged_relative_increase,
            "ged_passed": ged_passed,
            "static_quality_passed": f1_passed and ged_passed,
        }

    static_passed = all(row["static_quality_passed"] for row in per_scene.values())
    validation_aggregate = validation_diagnostics.get("aggregate", {})
    excluded = int(
        validation_aggregate.get(
            "validator_excluded_predicted_nodes",
            validation_aggregate.get("structurally_invalid_predicted_nodes", 0),
        )
    )
    invalid_passed = excluded > 0
    detour_gate = {
        "status": "not_identifiable",
        "passed": None,
        "reason": (
            "Counterfactual policies selected stage-local poses but never navigated. "
            "The replay omits the live reachability gate and records no cumulative "
            "counterfactual path, so false-positive detour distance cannot be measured."
        ),
        "prohibited_substitutes": [
            "selected-pose displacement from official",
            "zero novel objects visible at a selected pose",
            "A* planning failures on the official trajectory",
        ],
    }
    return {
        "policy_under_test": COMBINED_STATIC_POLICY,
        "thresholds": {
            "maximum_absolute_object_f1_auc_loss": F1_MAX_ABSOLUTE_LOSS,
            "maximum_relative_normalized_ged_auc_increase": GED_MAX_RELATIVE_INCREASE,
            "path_budget_m": 120.0,
        },
        "per_scene": per_scene,
        "static_quality_gate": {"passed": static_passed},
        "invalid_hypothesis_gate": {
            "passed": invalid_passed,
            "validator_excluded_predicted_nodes": excluded,
        },
        "false_positive_detour_gate": detour_gate,
        "combined_usefulness_claim": {
            "passed": False,
            "status": "not_established_missing_required_trajectory_outcome",
            "reason": (
                "The preregistered claim requires all conditions. Static quality and "
                "invalid-hypothesis checks cannot substitute for an unmeasured detour condition."
            ),
        },
    }


def parse_live_run_diagnostics(run_dir: Path) -> Dict[str, Any]:
    log_candidates = [
        run_dir / "logs" / "exploration_pipeline.log",
        run_dir / "exploration_pipeline.log",
    ]
    log_path = next((path for path in log_candidates if path.exists()), None)
    log_text = log_path.read_text(errors="replace") if log_path else ""
    prompts_dir = run_dir / "prompts"
    call_counter_path = prompts_dir / "_call_counter"
    call_counter = None
    if call_counter_path.exists():
        try:
            call_counter = int(call_counter_path.read_text().strip())
        except ValueError:
            call_counter = None

    jsonl_path = prompts_dir / "prompts_responses.jsonl"
    logged_records = 0
    aggregate_request_seconds = 0.0
    recorded_cost = 0.0
    cost_records = 0
    if jsonl_path.exists():
        for line in jsonl_path.read_text(errors="replace").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            logged_records += 1
            duration = record.get("duration_s")
            if isinstance(duration, (int, float)):
                aggregate_request_seconds += float(duration)
            cost = record.get("cost")
            if isinstance(cost, (int, float)):
                recorded_cost += float(cost)
                cost_records += 1

    stages_dir = run_dir / "stages"
    navigation_rows = []
    if stages_dir.is_dir():
        for path in sorted(
            stages_dir.glob("*/navigation_stats.json"),
            key=lambda item: int(item.parent.name),
        ):
            try:
                navigation_rows.append(json.loads(path.read_text()))
            except (json.JSONDecodeError, ValueError):
                continue
    final_path_m = (
        navigation_rows[-1].get("total_path_length_meters") if navigation_rows else None
    )
    return {
        "run_dir": str(run_dir),
        "log": str(log_path) if log_path else None,
        "completed_stage_records": len(navigation_rows),
        "final_recorded_path_m": final_path_m,
        "planner_failures": {
            "astar_failed": len(re.findall(r"A\* search failed to find a mid path", log_text)),
            "empty_mid_level_path": len(
                re.findall(r"Received empty mid-level path", log_text, flags=re.IGNORECASE)
            ),
            "interpretation": "planner failures, not robot-contact events",
        },
        "robot_collisions": {
            "status": "not_instrumented",
            "count": None,
            "reason": (
                "The pinned controller advances with agent.set_state and unconditionally "
                "increments path length; artifacts contain no contact, blocked-step, or "
                "collision sensor field. LLM check_collision text concerns proposed object "
                "boxes, not robot motion."
            ),
        },
        "api_calls": {
            "counter": call_counter,
            "logged_records": logged_records,
            "aggregate_request_seconds": aggregate_request_seconds,
            "duration_note": "sum of per-request durations; concurrent calls make this larger than wall time",
        },
        "api_cost": {
            "status": "measured" if cost_records else "unavailable_no_cost_or_token_usage_fields",
            "recorded_cost": recorded_cost if cost_records else None,
            "records_with_cost": cost_records,
        },
    }


def inspect_decision_replay(payload: Mapping[str, Any]) -> Dict[str, Any]:
    stages = list(payload.get("stages", []))
    error_stages = [stage.get("stage") for stage in stages if "error" in stage]
    trajectory_fields = {"path_length_m", "executed_path", "collision_count", "collisions"}

    def contains_field(value: Any) -> bool:
        if isinstance(value, Mapping):
            if trajectory_fields & set(value):
                return True
            return any(contains_field(child) for child in value.values())
        if isinstance(value, list):
            return any(contains_field(child) for child in value)
        return False

    return {
        "scene_id": payload.get("scene_id"),
        "stages": len(stages),
        "error_stages": error_stages,
        "contains_counterfactual_trajectory_or_collision_field": contains_field(stages),
        "false_positive_detours": {
            "status": "not_identifiable",
            "reason": "stage-independent selected poses are not executed cumulative paths",
        },
        "collisions": {
            "status": "not_identifiable",
            "reason": "no counterfactual policy entered the live controller or simulator",
        },
    }


def render_reliability_svg(
    panels: Mapping[str, Mapping[str, Mapping[str, Any]]],
    *,
    title: str,
) -> str:
    names = list(panels)
    columns = 2
    rows = max(1, math.ceil(len(names) / columns))
    width = 1600
    header_height = 150
    panel_width = 760
    panel_height = 650
    height = header_height + rows * panel_height + 60
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfaf7"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#24211d}.title{font-size:38px;font-weight:700}.panel{font-size:25px;font-weight:700}.axis{font-size:17px}.note{font-size:15px;fill:#5d574f}.legend{font-size:17px}</style>',
        f'<text class="title" x="70" y="65">{html.escape(title)}</text>',
        '<circle cx="82" cy="112" r="7" fill="#77736d"/><text class="legend" x="99" y="118">Raw support</text>',
        '<rect x="250" y="105" width="14" height="14" fill="#2563a6"/><text class="legend" x="275" y="118">LOSO calibrated</text>',
        '<line x1="475" y1="112" x2="515" y2="112" stroke="#c7bfb5" stroke-width="3" stroke-dasharray="8 7"/><text class="legend" x="525" y="118">Perfect calibration</text>',
    ]
    for panel_index, name in enumerate(names):
        column = panel_index % columns
        row = panel_index // columns
        origin_x = 70 + column * panel_width
        origin_y = header_height + row * panel_height
        plot_x = origin_x + 95
        plot_y = origin_y + 75
        plot_size = 455
        elements.append(
            f'<text class="panel" x="{origin_x}" y="{origin_y + 30}">{html.escape(str(name))}</text>'
        )
        elements.append(
            f'<rect x="{plot_x}" y="{plot_y}" width="{plot_size}" height="{plot_size}" fill="#ffffff" stroke="#d8d1c7" stroke-width="2"/>'
        )
        for tick in range(6):
            value = tick / 5
            x = plot_x + value * plot_size
            y = plot_y + (1 - value) * plot_size
            elements.extend(
                [
                    f'<line x1="{x:.2f}" y1="{plot_y}" x2="{x:.2f}" y2="{plot_y + plot_size}" stroke="#ece7df"/>',
                    f'<line x1="{plot_x}" y1="{y:.2f}" x2="{plot_x + plot_size}" y2="{y:.2f}" stroke="#ece7df"/>',
                    f'<text class="axis" text-anchor="middle" x="{x:.2f}" y="{plot_y + plot_size + 28}">{value:.1f}</text>',
                    f'<text class="axis" text-anchor="end" x="{plot_x - 12}" y="{y + 6:.2f}">{value:.1f}</text>',
                ]
            )
        elements.append(
            f'<line x1="{plot_x}" y1="{plot_y + plot_size}" x2="{plot_x + plot_size}" y2="{plot_y}" stroke="#c7bfb5" stroke-width="3" stroke-dasharray="8 7"/>'
        )
        elements.append(
            f'<text class="axis" text-anchor="middle" x="{plot_x + plot_size / 2}" y="{plot_y + plot_size + 58}">Mean predicted probability</text>'
        )
        elements.append(
            f'<text class="axis" text-anchor="middle" transform="translate({plot_x - 62},{plot_y + plot_size / 2}) rotate(-90)">Observed positive fraction</text>'
        )
        for series_name, color, shape in (
            ("raw", "#77736d", "circle"),
            ("calibrated", "#2563a6", "square"),
        ):
            metrics = panels[name][series_name]
            for bin_row in metrics.get("bins", []):
                if not bin_row["count"]:
                    continue
                x = plot_x + bin_row["mean_prediction"] * plot_size
                y = plot_y + (1 - bin_row["fraction_positive"]) * plot_size
                if shape == "circle":
                    elements.append(
                        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="8" fill="{color}" stroke="#fff" stroke-width="2"><title>n={bin_row["count"]}</title></circle>'
                    )
                else:
                    elements.append(
                        f'<rect x="{x - 8:.2f}" y="{y - 8:.2f}" width="16" height="16" fill="{color}" stroke="#fff" stroke-width="2"><title>n={bin_row["count"]}</title></rect>'
                    )
        raw = panels[name]["raw"]
        calibrated = panels[name]["calibrated"]
        note_x = plot_x + plot_size + 24
        note_y = plot_y + 30
        if raw.get("n"):
            baseline = panels[name].get("training_prevalence_baseline")
            lines = [
                f'n = {raw["n"]}',
                f'positive rate = {raw["positive_rate"]:.4f}',
                f'raw Brier = {raw["brier"]:.4f}',
                f'raw ECE = {raw["ece"]:.4f}',
                f'cal Brier = {calibrated["brier"]:.4f}',
                f'cal ECE = {calibrated["ece"]:.4f}',
            ]
            if baseline and baseline.get("brier") is not None:
                lines.append(f'train-rate Brier = {baseline["brier"]:.4f}')
        else:
            lines = ["No samples"]
        for line_index, line in enumerate(lines):
            elements.append(
                f'<text class="note" x="{note_x}" y="{note_y + line_index * 25}">{html.escape(line)}</text>'
            )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def _plot_panels(calibration: Mapping[str, Any], subset: str) -> Dict[str, Any]:
    panels = {
        scene: result["subsets"][subset]
        for scene, result in calibration["per_scene"].items()
    }
    panels["Pooled held-out"] = calibration["aggregate"][subset]
    return panels


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_config(root: Path, config: Mapping[str, Mapping[str, str]]) -> Dict[str, Dict[str, Path]]:
    return {
        scene: {key: root / relative for key, relative in values.items()}
        for scene, values in config.items()
    }


def _require_paths(config: Mapping[str, Mapping[str, Path]]) -> None:
    missing = [str(path) for values in config.values() for path in values.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("missing required Phase 13 input(s):\n" + "\n".join(missing))


def _atomic_write(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def run_phase13(workspace_root: Path) -> Dict[str, Any]:
    started = time.monotonic()
    calibration_config = _resolve_config(workspace_root, CALIBRATION_SCENES)
    matrix_config = _resolve_config(workspace_root, MATRIX_SCENES)
    _require_paths(calibration_config)
    _require_paths(matrix_config)

    scene_samples = {
        scene: collect_calibration_samples(
            paths["run"], paths["reference"], expected_size=EXPECTED_ENSEMBLE_SIZE
        )
        for scene, paths in calibration_config.items()
    }
    calibration = build_calibration_diagnostics(scene_samples)

    validation_per_scene = {
        scene: collect_validation_diagnostics(paths["run"], paths["reference"])
        for scene, paths in matrix_config.items()
    }
    validation = aggregate_validation_diagnostics(validation_per_scene)

    static_results = {
        scene: json.loads(paths["static"].read_text())
        for scene, paths in matrix_config.items()
    }
    guardrails = evaluate_guardrails(static_results, validation)
    live_runs = {
        scene: parse_live_run_diagnostics(paths["run"])
        for scene, paths in matrix_config.items()
    }
    decision_replay = {
        scene: inspect_decision_replay(json.loads(paths["decision"].read_text()))
        for scene, paths in matrix_config.items()
    }

    input_files: Dict[str, str] = {}
    for scene, paths in matrix_config.items():
        for key in ("reference", "static", "decision"):
            input_files[f"matrix.{scene}.{key}"] = _sha256(paths[key])
    for scene, paths in calibration_config.items():
        input_files[f"calibration.{scene}.reference"] = _sha256(paths["reference"])

    return {
        "schema": "asp_phase13_diagnostics_v5",
        "scope": {
            "matrix": "3 scenes x seed 42 x 120 m",
            "calibration": "4-scene leave-one-scene-out corpus",
            "reliability_bin_count": RELIABILITY_BIN_COUNT,
        },
        "calibration": calibration,
        "validation": validation,
        "guardrails": guardrails,
        "trajectory_diagnostics": {
            "live_official_runs": live_runs,
            "counterfactual_decision_replay": decision_replay,
            "false_positive_detours": {
                "status": "not_identifiable_from_frozen_corpus",
                "value": None,
            },
            "robot_collisions": {
                "status": "not_instrumented_in_live_or_replay_artifacts",
                "value": None,
            },
        },
        "provenance": {
            "workspace_root": str(workspace_root),
            "tool_sha256": _sha256(Path(__file__)),
            "input_sha256": input_files,
        },
        "runtime_seconds": time.monotonic() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path("/workspace"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-name", default="phase13_diagnostics_v5.json")
    args = parser.parse_args()

    output_dir = args.output_dir
    output_paths = [
        output_dir / args.output_name,
        output_dir / "reliability_overall.svg",
        output_dir / "reliability_object.svg",
        output_dir / "reliability_room.svg",
        output_dir / "SHA256SUMS",
    ]
    collisions = [path for path in output_paths if path.exists()]
    if collisions:
        raise SystemExit(
            "refusing to overwrite existing Phase 13 output(s): "
            + ", ".join(str(path) for path in collisions)
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = run_phase13(args.workspace_root)
    _atomic_write(output_paths[0], json.dumps(payload, indent=2) + "\n")
    for subset, output_path in zip(
        ("overall", "object", "room"), output_paths[1:4]
    ):
        title = f"LOSO reliability — {subset} hypotheses"
        _atomic_write(
            output_path,
            render_reliability_svg(
                _plot_panels(payload["calibration"], subset), title=title
            ),
        )
    checksums = "".join(
        f"{_sha256(path)}  {path.name}\n" for path in output_paths[:4]
    )
    _atomic_write(output_paths[4], checksums)
    print(json.dumps({"output_dir": str(output_dir), "files": [path.name for path in output_paths]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
