from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .geometry import distance
from .models import Graph, Hypothesis, Node
from .validator import _nodes


def _hypotheses(graph: Mapping, *, include_observed: bool = False) -> List[Hypothesis]:
    result = []
    for n in _nodes(graph):
        if n.type not in {"object", "room"} or n.center is None:
            continue
        if n.observed and not include_observed:
            continue
        result.append(Hypothesis(n.label, n.room_id, n.center, node_id=n.id, kind=n.type))
    return result


def match_hypotheses(hypotheses: Sequence[Hypothesis], completions: Sequence[Graph], *, expected_size: int, object_threshold: float = 0.5, room_threshold: float = 4.0) -> List[Hypothesis]:
    """Return hypotheses with raw support measured over the ensemble.

    `expected_size` is the pipeline's intended per-scene-track ensemble
    size (`LLM_ENSEMBLE_COUNT`, 4 in this pipeline's config - the paper's
    stated "8 samples" is 4 completions x 2 independently-scored scene-
    graph tracks, never a pooled 8-member set; room ids are a raw
    per-graph integer namespace, not shared across tracks, so pooling
    would silently compare unrelated rooms - see REVIEW_2026-09-14.md).
    Required, no default: `completions` is whatever survived upstream
    parse-failure drops, which is frequently less than the intended
    ensemble size, and support MUST be measured against the intended
    size, not the surviving count - a hypothesis in 1 of 1 surviving
    completions is NOT the same claim as 1 of 4 intended completions
    agreeing, and conflating the two silently inflates support exactly
    on the stages with the most parsing failures.
    """
    if len(completions) > expected_size:
        raise ValueError(f"got {len(completions)} completions but expected_size={expected_size} - "
                          f"check the caller is passing one scene-track's completions, not a pooled/stale set")
    completion_nodes = [_hypotheses(c, include_observed=True) for c in completions]
    out: List[Hypothesis] = []
    for h in hypotheses:
        threshold = room_threshold if h.kind == "room" else object_threshold
        hits = 0
        for nodes in completion_nodes:
            candidates = [n for n in nodes if n.label == h.label and n.parent_room == h.parent_room and distance(n.center, h.center) <= threshold]
            if candidates:
                hits += 1
        out.append(Hypothesis(h.label, h.parent_room, h.center, hits / expected_size, node_id=h.node_id, kind=h.kind, hits=hits))
    return out


def label_hypotheses_against_reference(
    hypotheses: Sequence[Hypothesis],
    reference: Mapping[str, Any],
    *,
    object_threshold: float = 0.5,
    room_threshold: float = 4.0,
) -> List[int]:
    """Label each hypothesis 1 if it matches the fully-explored reference
    under the same rule as `tools/evaluator/matching.py`'s `match_objects`
    (the author-faithful evaluator, exactly replicating the paper's own
    f1_score_plot.py) - this defines the calibration training LABEL per
    IMPLEMENTATION_RESEARCH.md section 4.2, "Label = hypothesis matches
    the fully-explored reference under the evaluator thresholds." The
    rule is deliberately reimplemented here (not imported from
    tools/evaluator/, which needs numpy and a different node type this
    module's own PyYAML-only dependency contract does not carry) so it
    stays a pure function over this module's own Hypothesis/Node types.
    A cross-implementation test in tools/evaluator/tests/test_evaluator.py
    checks the two produce the same match count on a shared fixture -
    that test is the real guard on this duplication, not a docstring
    promise.

    Deliberately NOT the same rule as match_hypotheses (support): no
    parent_room check, greedy in INPUT order (not global-distance-sorted
    order), and strict `<` at the threshold (not `<=`). Two reasons, not
    one:
    - `match_objects` is what "the evaluator" means everywhere else in
      this project, and using a different matching rule for the label
      than for the metric it is trying to predict would be a train/
      metric mismatch for no benefit - nothing about this fit is
      compared to a published number, so byte-faithfulness itself buys
      nothing; consistency with the project's own declared evaluator is
      the actual reason.
    - parent_room CANNOT be checked against the reference even if we
      wanted to: it is a raw per-graph integer id with no shared
      namespace between an independent frontier-baseline reference run
      and a completion's own observed graph (confirmed on real data:
      scene 00069's reference rooms are ids 206-214, its completions'
      rooms are ids 101-110 - zero overlap). match_hypotheses can check
      parent_room only because completions in one scene-track inherit
      IDs from that track's own observed graph, which the reference
      never does. Checking it here would label every hypothesis 0.

    Returns a list positional-parallel to `hypotheses` (0/1), not keyed
    by node_id (node_id is optional on Hypothesis). Matching is one-to-
    one over the WHOLE input list at once - a hypothesis's label depends
    on which of its same-label siblings already claimed the nearest
    reference node, so never call this hypothesis-by-hypothesis, and
    always pair the result with the same list (e.g. support_scores'
    output) in the same order so (support, label) rows cannot drift
    apart.
    """
    refs = [n for n in _nodes(reference) if n.type in {"object", "room"} and n.center is not None]
    available = list(range(len(refs)))
    labels = [0] * len(hypotheses)
    for h_idx, h in enumerate(hypotheses):
        if h.center is None:
            continue
        threshold = room_threshold if h.kind == "room" else object_threshold
        best_ref_pos = None
        best_dist = float("inf")
        for pos, r_idx in enumerate(available):
            ref = refs[r_idx]
            if ref.type != h.kind or ref.label != h.label:
                continue
            d = distance(ref.center, h.center)
            if d < best_dist:
                best_dist = d
                best_ref_pos = pos
        if best_ref_pos is not None and best_dist < threshold:
            labels[h_idx] = 1
            available.pop(best_ref_pos)
    return labels


class IsotonicCalibrator:
    """Least-squares non-decreasing support-to-probability map (PAVA).

    Samples with identical x are pooled into one weighted block (mean y,
    weight = count) BEFORE PAVA merging - 2026-09-15 bug fix. Support
    only takes a handful of discrete values under a fixed K=4 denominator
    (deviation #56), so tied x is not an edge case here, it is most of
    the dataset. The un-pooled version built one singleton block per
    SAMPLE (not per distinct x) and only merged blocks on a strict
    decrease between adjacent blocks in (x, y)-sorted order - within a
    tie group that never decreases (e.g. nine 0s then one 1, sorted by y
    ascending), nothing merged, and predict() silently returned whichever
    tied block happened to sort first (the 0s), not the true empirical
    mean of the tie group. That is not isotonic regression, it is an
    artifact of tie-breaking order. Pooling first makes each block
    represent one distinct x value with its real weighted mean, which is
    what PAVA is defined over.
    """

    def __init__(self, x: Sequence[float], y: Sequence[float]):
        if len(x) != len(y) or not x:
            raise ValueError("calibrator needs equally sized, non-empty samples")
        clipped = [(max(0.0, min(1.0, float(a))), max(0.0, min(1.0, float(b)))) for a, b in zip(x, y)]
        grouped: Dict[float, List[float]] = {}
        for sx, label in clipped:
            grouped.setdefault(sx, []).append(label)
        pooled = sorted((sx, sum(labels) / len(labels), float(len(labels))) for sx, labels in grouped.items())
        blocks: List[List[float]] = []  # [x_min, x_max, weighted_y, count]
        for sx, mean_label, count in pooled:
            blocks.append([sx, sx, mean_label, count])
            while len(blocks) >= 2 and blocks[-2][2] > blocks[-1][2]:
                left, right = blocks[-2], blocks[-1]
                total = left[3] + right[3]
                merged = [left[0], right[1], (left[2] * left[3] + right[2] * right[3]) / total, total]
                blocks[-2:] = [merged]
        self._blocks = blocks

    def predict(self, support: float) -> float:
        value = max(0.0, min(1.0, float(support)))
        if value <= self._blocks[0][0]:
            return self._blocks[0][2]
        for block in self._blocks:
            if value <= block[1]:
                return block[2]
        return self._blocks[-1][2]

    def __call__(self, support: float) -> float:
        return self.predict(support)


@dataclass(frozen=True)
class FoldResult:
    held_out_scene: str
    calibrator: IsotonicCalibrator
    predictions: Tuple[float, ...]
    labels: Tuple[int, ...]


def fit_leave_one_scene_out(scene_samples: Mapping[str, Sequence[Tuple[float, int]]]) -> Dict[str, FoldResult]:
    """Fit three-scene monotone calibrators and evaluate each held-out scene."""
    scenes = list(scene_samples)
    if len(scenes) < 2:
        raise ValueError("leave-one-scene-out requires at least two scenes")
    result: Dict[str, FoldResult] = {}
    for held_out in scenes:
        train = [sample for scene in scenes if scene != held_out for sample in scene_samples[scene]]
        if not train:
            raise ValueError("calibration fold has no training samples")
        calibrator = IsotonicCalibrator([x for x, _ in train], [y for _, y in train])
        held = scene_samples[held_out]
        result[held_out] = FoldResult(held_out, calibrator, tuple(calibrator(x) for x, _ in held), tuple(int(y) for _, y in held))
    return result
