"""Adapters for the author's YAML scene-graph artifact format.

The offline validator uses a small canonical graph schema.  The author
pipeline serializes nodes as ``node_type/name/position/dimension`` and edges
as two-element lists, so this module is the explicit boundary between those
formats.  It intentionally keeps YAML optional: JSON/canonical fixtures still
work without PyYAML, while real author artifacts require the dependency listed
in ``requirements.txt``.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Union


def _load_yaml(value: Union[str, Path], *, from_text: bool = False) -> Mapping[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised on minimal installs
        raise RuntimeError("reading author YAML requires PyYAML; install tools/asp_offline/requirements.txt") from exc
    text = str(value) if from_text else Path(value).read_text()
    parsed = yaml.safe_load(text)
    if not isinstance(parsed, Mapping):
        raise ValueError("author graph must be a YAML mapping")
    return parsed


def _vector(value: Any) -> Optional[Sequence[float]]:
    if isinstance(value, (list, tuple)) and len(value) == 3:
        try:
            return [float(component) for component in value]
        except (TypeError, ValueError):
            return None
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError, json.JSONDecodeError):
                return None
        return _vector(parsed)
    return None


def normalize_author_graph(raw: Mapping[str, Any], *, observed: Optional[bool] = None) -> Dict[str, Any]:
    """Convert one author graph mapping to the canonical offline schema."""
    raw_nodes = raw.get("nodes", [])
    if isinstance(raw_nodes, Mapping):
        raw_nodes = list(raw_nodes.values())
    if not isinstance(raw_nodes, list):
        raise ValueError("author graph nodes must be a list")

    nodes = []
    for item in raw_nodes:
        if not isinstance(item, Mapping):
            continue
        node_id = item.get("id")
        if node_id is None:
            raise ValueError("author graph node is missing id")
        predicted = bool(item.get("is_predicted", False))
        node_observed = (not predicted) if observed is None else bool(observed)
        node: Dict[str, Any] = {
            "id": node_id,
            "type": item.get("type", item.get("node_type", "")),
            "label": item.get("label", item.get("name", "")),
            "observed": node_observed,
        }
        center = _vector(item.get("center", item.get("position")))
        dimensions = _vector(item.get("dimensions", item.get("dimension")))
        if center is not None:
            node["center"] = list(center)
        if dimensions is not None:
            node["dimensions"] = list(dimensions)
        if "room_id" in item:
            node["room_id"] = item["room_id"]
        nodes.append(node)

    by_id = {str(node["id"]): node for node in nodes}
    raw_edges = raw.get("edges", [])
    if isinstance(raw_edges, Mapping):
        raw_edges = list(raw_edges.values())
    if not isinstance(raw_edges, list):
        raise ValueError("author graph edges must be a list")
    edges = []
    for item in raw_edges:
        if isinstance(item, Mapping):
            source = item.get("source", item.get("from", item.get("u")))
            target = item.get("target", item.get("to", item.get("v")))
            edge_type = item.get("type", item.get("relation", ""))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            source, target = item[0], item[1]
            edge_type = ""
        else:
            continue
        if source is None or target is None:
            continue
        edge: Dict[str, Any] = {"source": source, "target": target}
        if edge_type:
            edge["type"] = edge_type
        edges.append(edge)
        source_node, target_node = by_id.get(str(source)), by_id.get(str(target))
        if source_node and target_node:
            if source_node.get("type") == "object" and target_node.get("type") == "room":
                source_node.setdefault("room_id", target_node["id"])
            elif target_node.get("type") == "object" and source_node.get("type") == "room":
                target_node.setdefault("room_id", source_node["id"])
    return {"nodes": nodes, "edges": edges}


def load_author_graph(path: Union[str, Path], *, observed: Optional[bool] = None) -> Dict[str, Any]:
    return normalize_author_graph(_load_yaml(path), observed=observed)


def load_author_graph_text(text: str, *, observed: Optional[bool] = None) -> Dict[str, Any]:
    return normalize_author_graph(_load_yaml(text, from_text=True), observed=observed)
