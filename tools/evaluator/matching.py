"""
Object precision/recall/F1, replicating exploration/scripts/f1_score_plot.py's
calculate_f1_score exactly: greedy same-name nearest-neighbor matching within
a fixed centroid distance threshold (0.5 m per IMPLEMENTATION_RESEARCH.md
section 3.3 and the ASP paper), one-to-one (each ground-truth object can be
claimed by at most one predicted object).

Deliberately NOT parent-room-aware (unlike the GED substitution cost in
ged.py) - this asymmetry matches the two source scripts exactly and is not
an oversight; document any change here rather than "fixing" it to be
consistent with ged.py.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ObjectMatch:
    gt_id: object
    pred_id: object
    distance: float


@dataclass
class MatchResult:
    matches: list  # list[ObjectMatch]
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


def match_objects(gt_objects, pred_objects, threshold: float = 0.5) -> MatchResult:
    """gt_objects / pred_objects: lists of EvalNode (node_type == 'object')."""
    if not gt_objects:
        # Matches f1_score_plot.py's calculate_f1_score: warn-worthy, score 0.
        return MatchResult([], 0.0, 0.0, 0.0, 0, len(pred_objects), 0)
    if not pred_objects:
        return MatchResult([], 0.0, 0.0, 0.0, 0, 0, len(gt_objects))

    available_gt = list(range(len(gt_objects)))
    matches = []

    for pred_idx, pred_obj in enumerate(pred_objects):
        best_gt_idx = None
        min_dist = float("inf")
        for gt_idx in available_gt:
            gt_obj = gt_objects[gt_idx]
            if pred_obj.name != gt_obj.name:
                continue
            dist = float(np.linalg.norm(pred_obj.position - gt_obj.position))
            if dist < min_dist:
                min_dist = dist
                best_gt_idx = gt_idx
        if best_gt_idx is not None and min_dist < threshold:
            matches.append(ObjectMatch(
                gt_id=gt_objects[best_gt_idx].id,
                pred_id=pred_obj.id,
                distance=min_dist,
            ))
            available_gt.remove(best_gt_idx)

    true_positives = len(matches)
    false_positives = len(pred_objects) - true_positives
    false_negatives = len(gt_objects) - true_positives

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return MatchResult(matches, precision, recall, f1, true_positives, false_positives, false_negatives)
