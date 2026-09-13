from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

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


def match_hypotheses(hypotheses: Sequence[Hypothesis], completions: Sequence[Graph], *, object_threshold: float = 0.5, room_threshold: float = 4.0) -> List[Hypothesis]:
    """Return hypotheses with raw support measured over K completion graphs."""
    completion_nodes = [_hypotheses(c, include_observed=True) for c in completions]
    out: List[Hypothesis] = []
    for h in hypotheses:
        threshold = room_threshold if h.kind == "room" else object_threshold
        hits = 0
        for nodes in completion_nodes:
            candidates = [n for n in nodes if n.label == h.label and n.parent_room == h.parent_room and distance(n.center, h.center) <= threshold]
            if candidates:
                hits += 1
        out.append(Hypothesis(h.label, h.parent_room, h.center, hits / max(len(completions), 1), node_id=h.node_id, kind=h.kind))
    return out


class IsotonicCalibrator:
    """Least-squares non-decreasing support-to-probability map (PAVA)."""

    def __init__(self, x: Sequence[float], y: Sequence[float]):
        if len(x) != len(y) or not x:
            raise ValueError("calibrator needs equally sized, non-empty samples")
        pairs = sorted((max(0.0, min(1.0, float(a))), max(0.0, min(1.0, float(b)))) for a, b in zip(x, y))
        blocks: List[List[float]] = []  # [x_min, x_max, weighted_y, count]
        for sx, label in pairs:
            blocks.append([sx, sx, label, 1.0])
            while len(blocks) >= 2 and blocks[-2][2] > blocks[-1][2]:
                left, right = blocks[-2], blocks[-1]
                count = left[3] + right[3]
                merged = [left[0], right[1], (left[2] * left[3] + right[2] * right[3]) / count, count]
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
