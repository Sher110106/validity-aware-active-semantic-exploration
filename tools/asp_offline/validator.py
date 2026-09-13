from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from .geometry import aabb, contains, overlaps, segment_intersects_aabb
from .models import Edge, Graph, Node, ValidationIssue, ValidationResult

_BLOCK_RE = re.compile(r"```(?:yaml|yml)\s*\n?(.*?)```", re.IGNORECASE | re.DOTALL)
_PREDICTABLE = {"object", "room"}
_ALL_TYPES = {"object", "room", "structure", "door", "nothing"}
_IMPASSABLE = {"wall", "structure", "curtain", "window", "blind"}


@dataclass(frozen=True)
class ValidationConfig:
    overlap_tolerance: float = 1e-6
    containment_tolerance: float = 1e-6
    enforce_impassable_crossings: bool = True
    require_dimensions: bool = True


def _parse_completion(value: Any) -> Tuple[Optional[Mapping[str, Any]], Optional[str]]:
    if isinstance(value, Mapping):
        return value, None
    if not isinstance(value, str):
        return None, "completion is neither a mapping nor text"
    blocks = _BLOCK_RE.findall(value)
    if len(blocks) != 1:
        return None, "completion must contain exactly one YAML code block"
    body = blocks[0].strip()
    try:
        # JSON is a strict subset of YAML, giving a dependency-free path for
        # fixtures and cached completions.
        return json.loads(body), None
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError:
            return None, "YAML parsing requires PyYAML (or JSON inside the YAML block)"
        try:
            parsed = yaml.safe_load(body)
        except Exception as exc:  # pragma: no cover - parser-specific errors
            return None, "invalid YAML: %s" % exc
        return parsed, None


def _nodes(graph: Mapping[str, Any], *, observed: bool = False) -> List[Node]:
    raw = graph.get("nodes", [])
    if isinstance(raw, Mapping):
        raw = list(raw.values())
    return [Node.from_mapping(n, observed=observed) for n in raw if isinstance(n, Mapping)]


def _edges(graph: Mapping[str, Any]) -> List[Edge]:
    raw = graph.get("edges", [])
    return [Edge.from_mapping(e) for e in raw if isinstance(e, Mapping)]


def _graph(nodes: Iterable[Node], edges: Iterable[Edge], template: Optional[Mapping[str, Any]] = None) -> Graph:
    result = dict(template or {})
    result["nodes"] = [n.as_dict() for n in nodes]
    result["edges"] = [e.as_dict() for e in edges]
    return result


def _edge_allowed(a: Node, b: Node) -> bool:
    types = {a.type, b.type}
    return types in ({"object", "room"}, {"room"}) or types == {"room"}


def validate_completion(
    completion: Any,
    observed_graph: Mapping[str, Any],
    config: ValidationConfig = ValidationConfig(),
) -> ValidationResult:
    """Validate one sampled graph and remove only invalid predicted nodes.

    Decisions use the observed graph and fixed geometry only.  A completion is
    rejected when it cannot preserve every observed node; otherwise invalid
    predictions are removed and the surviving graph is accepted.
    """
    parsed, parse_error = _parse_completion(completion)
    observed_nodes = _nodes(observed_graph, observed=True)
    observed_ids = {n.id for n in observed_nodes}
    issues: List[ValidationIssue] = []
    if parse_error or not isinstance(parsed, Mapping):
        issues.append(ValidationIssue("parse", parse_error or "top-level YAML value must be a mapping", severity="reject"))
        return ValidationResult(_graph(observed_nodes, _edges(observed_graph), observed_graph), False, True, issues)

    # ASP responses may echo the partial graph.  Treat identifiers already in
    # the observed graph as preserved observations rather than predictions.
    predicted = [n for n in _nodes(parsed, observed=False) if n.id not in observed_ids]
    edges = _edges(parsed)
    by_id: Dict[str, Node] = {}
    invalid: Set[str] = set()
    for node in observed_nodes:
        if not node.id or node.id in by_id:
            issues.append(ValidationIssue("observed_identity", "observed nodes must have unique non-empty identifiers", node.id or None, "reject"))
            return ValidationResult(_graph(observed_nodes, _edges(observed_graph), observed_graph), False, True, issues)
        by_id[node.id] = node

    for node in predicted:
        if not node.id or node.id in by_id:
            issues.append(ValidationIssue("unique_identifier", "predicted identifier is empty or collides with an observed node", node.id or None))
            if node.id:
                invalid.add(node.id)
            continue
        by_id[node.id] = node

    def fail(code: str, message: str, node: Node) -> None:
        raw_support = node.data.get("support") if isinstance(node.data, Mapping) else None
        try:
            support = float(raw_support) if raw_support is not None else None
        except (TypeError, ValueError):
            support = None
        issues.append(ValidationIssue(code, message, node.id, "remove", support))
        invalid.add(node.id)

    for node in predicted:
        if node.id in invalid:
            continue
        if node.type not in _PREDICTABLE:
            fail("node_schema", "new nodes may only be objects or rooms", node)
            continue
        if node.center is None or (config.require_dimensions and node.dimensions is None) or aabb(node) is None:
            fail("finite_geometry", "predicted node must have finite center and non-negative dimensions", node)

    # Remove malformed/unknown edges and enforce the prompt's two edge forms.
    valid_edges: List[Edge] = list(_edges(observed_graph))
    for edge in edges:
        a, b = by_id.get(edge.source), by_id.get(edge.target)
        if a is None or b is None:
            issues.append(ValidationIssue("edge_endpoint", "edge endpoint does not exist", edge.source or edge.target))
            continue
        if a.id in observed_ids and b.id in observed_ids:
            valid_edges.append(edge)
            continue
        if not _edge_allowed(a, b):
            issues.append(ValidationIssue("edge_schema", "only object-room and room-room edges are allowed", a.id))
            continue
        valid_edges.append(edge)

    active = [n for n in observed_nodes + predicted if n.id not in invalid]
    active_by_id = {n.id: n for n in active}
    rooms = {n.id: n for n in active if n.type == "room"}
    for node in list(active):
        if node.type != "object" or node.id in observed_ids:
            continue
        parent = node.room_id
        parent_edge = next((e for e in valid_edges if node.id in (e.source, e.target) and active_by_id.get(e.source if e.target == node.id else e.target, Node("", "")).type == "room"), None)
        if parent is None and parent_edge:
            parent = parent_edge.source if parent_edge.target == node.id else parent_edge.target
        if parent is None or parent not in rooms:
            fail("object_parent", "every predicted object needs an existing parent room", node)
            continue
        if node.center is not None and aabb(rooms[parent]) is not None and not contains(aabb(rooms[parent]), node.center, tolerance=config.containment_tolerance):
            fail("room_containment", "predicted object lies outside its parent room", node)

    active = [n for n in active if n.id not in invalid]
    active_by_id = {n.id: n for n in active}
    # AABB conflicts include observed objects, structures, and nothing nodes.
    blockers = [n for n in active if n.type in {"object", "structure", "nothing"}]
    for node in [n for n in active if n.id not in observed_ids and n.type in _PREDICTABLE]:
        box = aabb(node)
        if box is None:
            continue
        for other in blockers:
            if other.id == node.id or aabb(other) is None:
                continue
            if overlaps(box, aabb(other), tolerance=config.overlap_tolerance):
                fail("aabb_conflict", "predicted node overlaps an observed or predicted blocker", node)
                break
        if node.id in invalid:
            continue
        for other in active:
            if other.id == node.id or other.type != "room" or aabb(other) is None:
                continue
            # Room boxes are allowed to contain objects; do not treat them as blockers.

    if config.enforce_impassable_crossings:
        structures = [n for n in active if n.type == "structure" and (n.label.lower() in _IMPASSABLE or not n.label)]
        doors = [n for n in active if n.type == "door"]
        for node in [n for n in active if n.id not in observed_ids and n.type == "object" and n.room_id in rooms and node.center is not None]:
            room = rooms.get(node.room_id or "")
            if room is None or room.center is None:
                continue
            for structure in structures:
                sbox = aabb(structure)
                if sbox and segment_intersects_aabb(room.center, node.center, sbox):
                    if not any(aabb(d) and segment_intersects_aabb(room.center, node.center, aabb(d)) for d in doors):
                        fail("impassable_crossing", "object-room connection crosses an impassable structure without a door", node)
                        break

    final_nodes = [n for n in observed_nodes + predicted if n.id not in invalid]
    final_ids = {n.id for n in final_nodes}
    final_edges = [e for e in valid_edges if e.source in final_ids and e.target in final_ids]
    return ValidationResult(_graph(final_nodes, final_edges, observed_graph), True, False, issues, sorted(invalid))


def validate_ensemble(
    completions: Iterable[Any],
    observed_graph: Mapping[str, Any],
    config: ValidationConfig = ValidationConfig(),
) -> List[ValidationResult]:
    """Validate K samples; if all fail, return one observed-graph fallback."""
    results = [validate_completion(c, observed_graph, config) for c in completions]
    if results and any(r.accepted for r in results):
        return results
    fallback = _graph(_nodes(observed_graph, observed=True), _edges(observed_graph), observed_graph)
    issue = ValidationIssue("ensemble_fallback", "all completions failed; continuing with observed graph and geometric frontier fallback", severity="fallback")
    return results + [ValidationResult(fallback, True, False, [issue])]
