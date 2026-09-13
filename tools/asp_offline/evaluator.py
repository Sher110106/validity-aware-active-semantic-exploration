from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .geometry import distance
from .models import Graph, Node
from .validator import _edges, _nodes


def area_under_curve(rows: Sequence[Mapping[str, Any]], metric: str, *, budget_m: Optional[float] = None) -> float:
    """Trapezoidal AUC over path distance, normalized by the path budget.

    When a budget is supplied, points beyond it are excluded and the curve is
    linearly interpolated (or held at the nearest value) at both 0 and the
    budget. This keeps a malformed/overlong replay from inflating a
    preregistered 0--120 m AUC.
    """
    points = []
    for row in rows:
        if metric not in row:
            continue
        try:
            x = float(row.get("path_m", row.get("checkpoint", 0.0)))
            y = float(row[metric])
        except (TypeError, ValueError):
            continue
        if math.isfinite(x) and math.isfinite(y):
            points.append((x, y))
    if len(points) < 2:
        return 0.0
    points.sort(key=lambda p: p[0])
    if budget_m is not None:
        budget = float(budget_m)
        if not math.isfinite(budget) or budget <= 0:
            return 0.0

        def at(x: float) -> float:
            if x <= points[0][0]:
                return points[0][1]
            for (x0, y0), (x1, y1) in zip(points, points[1:]):
                if x <= x1:
                    if x1 == x0:
                        return y1
                    fraction = (x - x0) / (x1 - x0)
                    return y0 + fraction * (y1 - y0)
            return points[-1][1]

        clipped = [(x, y) for x, y in points if 0.0 <= x <= budget]
        if not clipped or clipped[0][0] > 0.0:
            clipped.insert(0, (0.0, at(0.0)))
        elif clipped[0][0] < 0.0:  # defensive; the filter above normally prevents this
            clipped[0] = (0.0, at(0.0))
        if clipped[-1][0] < budget:
            clipped.append((budget, at(budget)))
        else:
            clipped[-1] = (budget, at(budget))
        # Collapse duplicate checkpoints after clipping (for example, when a
        # source replay contains two rows at the budget boundary).
        deduped = {}
        for x, y in clipped:
            deduped[x] = y
        points = sorted(deduped.items())
        denominator = budget
    else:
        denominator = points[-1][0]
    area = sum((x1 - x0) * (y0 + y1) / 2.0 for (x0, y0), (x1, y1) in zip(points, points[1:]))
    return area / denominator if denominator > 0 else 0.0


def summarize_metrics(rows: Sequence[Mapping[str, Any]], *, budget_m: Optional[float] = None) -> Dict[str, float]:
    """Compute the preregistered path-normalized primary outcome AUCs."""
    return {name + "_auc": area_under_curve(rows, name, budget_m=budget_m)
            for name in ("object_precision", "object_recall", "object_f1", "normalized_ged")}


def _match_nodes(pred: Sequence[Node], ref: Sequence[Node], threshold: float) -> Tuple[int, Dict[str, str]]:
    candidates = sorted(((distance(p.center, r.center), p, r) for p in pred if p.center is not None for r in ref if r.center is not None and p.label == r.label and distance(p.center, r.center) <= threshold), key=lambda item: item[0])
    used_p, used_r, mapping = set(), set(), {}
    for _, p, r in candidates:
        if p.id not in used_p and r.id not in used_r:
            used_p.add(p.id); used_r.add(r.id); mapping[p.id] = r.id
    return len(mapping), mapping


def evaluate_graph(predicted: Mapping[str, Any], reference: Mapping[str, Any]) -> Dict[str, float]:
    p_objects = [n for n in _nodes(predicted) if n.type == "object"]
    r_objects = [n for n in _nodes(reference) if n.type == "object"]
    p_rooms = [n for n in _nodes(predicted) if n.type == "room"]
    r_rooms = [n for n in _nodes(reference) if n.type == "room"]
    object_tp, object_map = _match_nodes(p_objects, r_objects, 0.5)
    room_tp, room_map = _match_nodes(p_rooms, r_rooms, 4.0)
    precision = object_tp / len(p_objects) if p_objects else (1.0 if not r_objects else 0.0)
    recall = object_tp / len(r_objects) if r_objects else (1.0 if not p_objects else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    comparable_p = p_objects + p_rooms
    comparable_r = r_objects + r_rooms
    _, object_map = _match_nodes(p_objects, r_objects, 0.5)
    all_map = dict(object_map)
    all_map.update(room_map)
    node_edits = (len(comparable_p) - len(all_map)) + (len(comparable_r) - len(all_map))
    ref_ids = {n.id for n in comparable_r}
    pred_ids = {n.id for n in comparable_p}
    def undirected(edge):
        return tuple(sorted((edge.source, edge.target)))
    ref_edges = {undirected(e) for e in _edges(reference) if e.source in ref_ids and e.target in ref_ids}
    pred_edges = {undirected(e) for e in _edges(predicted) if e.source in pred_ids and e.target in pred_ids}
    mapped_pred_edges = {(all_map.get(a), all_map.get(b)) for a, b in pred_edges if a in all_map and b in all_map}
    edge_edits = len(ref_edges - mapped_pred_edges) + len(mapped_pred_edges - ref_edges)
    ged = float(node_edits + edge_edits)
    norm = len(comparable_r) + len(ref_edges)
    return {"object_precision": precision, "object_recall": recall, "object_f1": f1,
            "ged": ged, "normalized_ged": ged / norm if norm else 0.0,
            "object_tp": float(object_tp), "room_tp": float(room_tp)}


def evaluate_run(run_dir: Union[str, Path], reference_graph: Union[str, Path, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Evaluate JSON checkpoint graphs in a cached run directory."""
    run_path = Path(run_dir)
    if isinstance(reference_graph, Mapping):
        reference = reference_graph
    else:
        reference = json.loads(Path(reference_graph).read_text())
    checkpoint_dir = run_path / "graphs"
    files = sorted(checkpoint_dir.glob("*.json"))
    rows: List[Dict[str, Any]] = []
    for path in files:
        payload = json.loads(path.read_text())
        graph = payload.get("graph", payload)
        row = evaluate_graph(graph, reference)
        row["checkpoint"] = payload.get("path_m", payload.get("path", path.stem))
        raw_path = payload.get("path_m", payload.get("path", path.stem))
        try:
            row["path_m"] = float(raw_path)
        except (TypeError, ValueError):
            match = re.search(r"[-+]?\d+(?:\.\d+)?", str(raw_path))
            row["path_m"] = float(match.group(0)) if match else float(len(rows))
        if "runtime_s" in payload:
            row["runtime_s"] = float(payload["runtime_s"])
        if "api_cost_usd" in payload:
            row["api_cost_usd"] = float(payload["api_cost_usd"])
        rows.append(row)
    return rows
