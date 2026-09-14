"""Uncalibrated support-threshold policy for the extension-replay ablation.

IMPLEMENTATION_PLAN.md section 17 step 2 compares four policies on the same
cached ensemble completions: official ASP, filter-only (the structural
validator, validator.py), support-threshold-only, and filter+support-
threshold. This module implements the two support-threshold variants.

Per IMPLEMENTATION_RESEARCH.md section 4.2, raw support s_j is the fraction
of K completions containing a matching node (by label + parent room +
spatial threshold - the same hypothesis-matching rule calibration.py already
uses via match_hypotheses). This is NOT calibration: no monotone map is
fitted or applied here. See scoring.py's score_viewpoint docstring for why
calibration itself is not yet computable (only one scene, 00069, has a
ground-truth reference graph; IMPLEMENTATION_RESEARCH.md section 4.2's
leave-one-scene-out requires rotating 3-vs-1 across at least 4). Thresholding
raw, uncalibrated support is a real, nameable policy in its own right - the
control a fitted calibrator must beat - not a placeholder for one.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from .calibration import match_hypotheses, _hypotheses
from .models import Graph, Hypothesis
from .validator import _edges, _graph, _nodes


def support_filtered_graph(
    observed: Mapping[str, Any],
    completion: Mapping[str, Any],
    ensemble: Sequence[Mapping[str, Any]],
    tau: float,
    *,
    object_threshold: float = 0.5,
    room_threshold: float = 4.0,
) -> Dict[str, Any]:
    """One completion's predicted nodes, kept only where cross-ensemble support >= tau.

    `ensemble` is the full set of raw completions this `completion` is scored
    for agreement against (K completions per IMPLEMENTATION_RESEARCH.md
    4.2's s_j - fraction of K containing a matching node). `completion`
    itself is included in its own denominator, matching match_hypotheses'
    existing semantics (calibration.py) exactly, so this stays consistent
    with the one calibration code path already unit-tested.
    """
    predicted_hypotheses = _hypotheses(completion, include_observed=False)
    scored = match_hypotheses(
        predicted_hypotheses, list(ensemble),
        object_threshold=object_threshold, room_threshold=room_threshold,
    )
    kept_ids = {h.node_id for h in scored if h.support >= tau}
    observed_nodes = _nodes(observed, observed=True)
    predicted_nodes = [n for n in _nodes(completion, observed=False) if n.id in kept_ids]
    kept_node_ids = {n.id for n in observed_nodes} | kept_ids
    edges = [e for e in _edges(completion) if e.source in kept_node_ids and e.target in kept_node_ids]
    edges += [e for e in _edges(observed) if e.source in kept_node_ids and e.target in kept_node_ids]
    graph: Graph = _graph(observed_nodes + predicted_nodes, edges, observed)
    graph["support_threshold"] = {"tau": tau, "kept": len(predicted_nodes), "dropped": len(predicted_hypotheses) - len(predicted_nodes)}
    return graph


def support_scores(
    completion: Mapping[str, Any],
    ensemble: Sequence[Mapping[str, Any]],
    *,
    object_threshold: float = 0.5,
    room_threshold: float = 4.0,
) -> List[Hypothesis]:
    """Raw (uncalibrated) support per predicted node in `completion` - for inspection/reporting."""
    predicted_hypotheses = _hypotheses(completion, include_observed=False)
    return match_hypotheses(
        predicted_hypotheses, list(ensemble),
        object_threshold=object_threshold, room_threshold=room_threshold,
    )


UNCALIBRATED_STATUS = {
    "method": "none",
    "fitted_on_scenes": [],
    "held_out": False,
    "loso_scenes_available": 1,
    "loso_scenes_required": 4,
    "status": "UNCALIBRATED_PROVISIONAL",
}
"""Stamp this (or a copy with `loso_scenes_available` updated) into every
support-threshold-policy output record, per the Opus advisor's review of
this ablation (2026-09-14): the plan's "calibration-only"/"combined"
language must never appear unqualified next to a result produced with
calibrator=None. See scoring.py and DEVIATIONS.md for the full reasoning."""
