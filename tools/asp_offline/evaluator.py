from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .geometry import distance
from .models import Graph, Node
from .validator import _edges, _nodes


def area_under_curve(rows: Sequence[Mapping[str, Any]], metric: str, *, budget_m: Optional[float] = None) -> float:
    """Trapezoidal AUC over path distance, normalized by the path budget."""
    points = [(float(r.get("path_m", r.get("checkpoint", 0.0))), float(r[metric])) for r in rows if metric in r]
    if len(points) < 2:
        return 0.0
    points.sort(key=lambda p: p[0])
    area = sum((x1 - x0) * (y0 + y1) / 2.0 for (x0, y0), (x1, y1) in zip(points, points[1:]))
    denominator = float(budget_m) if budget_m is not None else points[-1][0]
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


def evaluate_run(run_dir: str | Path, reference_graph: str | Path | Mapping[str, Any]) -> List[Dict[str, Any]]:
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
