"""
Load ASP scene-graph YAML files (the `habitat_scene_graph_original_graph{i}.yaml`
format the pipeline's own LLM-prompting step and evaluation scripts both use)
into a comparison-ready form.

Filtering here intentionally replicates the author's own evaluation scripts
(exploration/scripts/ged_score_plot.py, exploration/scripts/f1_score_plot.py)
exactly: door-named nodes and any node_type other than 'object'/'room' are
dropped. Per IMPLEMENTATION_RESEARCH.md section 3.3: "Released GED script
computes over object/room nodes only, skips door + other structure/nothing
nodes." This module is for the independent EVALUATOR only - it is not a
general-purpose scene-graph loader for the validator (Phase 8), which will
need the full node set (structure/nothing included).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import yaml


def _smart_eval(expr):
    """Positions are stored as string-encoded Python literals in these YAML
    files (e.g. "[1.0, 2.0, 0.5]"); parse if needed, pass through otherwise."""
    if isinstance(expr, str):
        return ast.literal_eval(expr)
    return expr


@dataclass
class EvalNode:
    id: object
    node_type: str  # 'object' or 'room' (only these two ever appear post-filter)
    name: str
    position: np.ndarray
    parent_name: Optional[str] = None  # objects only - name of the room node
    # they're connected to, resolved from edges below. None if no room
    # neighbor exists in the filtered graph.
    raw: dict = field(default_factory=dict, repr=False)


@dataclass
class EvalGraph:
    nodes: dict  # id -> EvalNode
    edges: list  # list of (u, v) id pairs, both endpoints present in `nodes`

    @property
    def objects(self):
        return [n for n in self.nodes.values() if n.node_type == "object"]

    @property
    def rooms(self):
        return [n for n in self.nodes.values() if n.node_type == "room"]


def load_eval_graph(yaml_path) -> EvalGraph:
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f) or {}

    raw_nodes = data.get("nodes", []) or []
    raw_edges = data.get("edges", []) or []

    nodes = {}
    for node_data in raw_nodes:
        name = node_data.get("name")
        node_type = node_data.get("node_type")
        if name is not None and str(name).lower() == "door":
            continue
        if node_type not in ("object", "room"):
            continue
        node_id = node_data["id"]
        position = np.array(_smart_eval(node_data["position"]), dtype=float)
        nodes[node_id] = EvalNode(
            id=node_id,
            node_type=node_type,
            name=name,
            position=position,
            raw=node_data,
        )

    edges = []
    for edge in raw_edges:
        if len(edge) != 2:
            continue
        u, v = edge
        if u in nodes and v in nodes:
            edges.append((u, v))

    # Resolve each object's parent room from its neighbors (first room
    # neighbor found), matching ged_score_plot.py's load_graph_from_yaml.
    neighbors = {node_id: set() for node_id in nodes}
    for u, v in edges:
        neighbors[u].add(v)
        neighbors[v].add(u)

    for node_id, node in nodes.items():
        if node.node_type != "object":
            continue
        for neighbor_id in neighbors[node_id]:
            neighbor = nodes[neighbor_id]
            if neighbor.node_type == "room":
                node.parent_name = neighbor.name
                break

    return EvalGraph(nodes=nodes, edges=edges)
