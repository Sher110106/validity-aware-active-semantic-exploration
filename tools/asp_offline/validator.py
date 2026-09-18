from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from .geometry import aabb, contains, overlaps, segment_intersects_aabb
from .models import Edge, Graph, Node, ValidationIssue, ValidationResult

_BLOCK_RE = re.compile(r"^\s*```(?:yaml|yml)\s*\n?(.*?)```\s*$", re.IGNORECASE | re.DOTALL)
_PREDICTABLE = {"object", "room"}
_IMPASSABLE = {"wall", "structure", "curtain", "window", "blind"}


@dataclass(frozen=True)
class ValidationConfig:
    overlap_tolerance: float = 1e-6
    containment_tolerance: float = 1e-6
    enforce_impassable_crossings: bool = True
    require_dimensions: bool = True
    allow_parsed_mapping: bool = False


def _parse_completion(value: Any) -> Tuple[Optional[Mapping[str, Any]], Optional[str]]:
    if isinstance(value, Mapping):
        return value, None
    if not isinstance(value, str):
        return None, "completion is neither a fenced YAML text block nor an explicitly allowed parsed mapping"
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
    return a.id != b.id and types in ({"object", "room"}, {"room"})


def _scalar_identifier(value: Any) -> bool:
    return isinstance(value, (str, int, float)) and not isinstance(value, bool) and bool(str(value).strip())


def _geometric_frontier_candidates(nodes: Iterable[Node]) -> List[List[float]]:
    """Return deterministic horizontal frontier candidates from free-space boxes.

    The online ROS planner owns the actual navigation frontier.  Offline
    validation still needs a concrete fail-soft hand-off, so expose the four
    horizontal faces of each observed ``nothing`` cuboid as candidate points.
    Empty observations produce an explicit empty list rather than inventing
    geometry.
    """
    candidates: List[List[float]] = []
    seen: Set[Tuple[float, float, float]] = set()
    for node in nodes:
        if node.type != "nothing":
            continue
        box = aabb(node)
        if box is None or node.center is None:
            continue
        lo, hi = box
        x, y, z = node.center
        points = ((lo[0], y, z), (hi[0], y, z),
                  (x, y, lo[2]), (x, y, hi[2]))
        for point in points:
            key = tuple(round(float(value), 9) for value in point)
            if key not in seen:
                seen.add(key)
                candidates.append([float(value) for value in point])
    return candidates


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
    if isinstance(completion, Mapping) and not config.allow_parsed_mapping:
        parsed, parse_error = None, "completion must contain exactly one YAML code block"
    else:
        parsed, parse_error = _parse_completion(completion)
    observed_nodes = _nodes(observed_graph, observed=True)
    observed_ids = {n.id for n in observed_nodes}
    issues: List[ValidationIssue] = []
    if parse_error or not isinstance(parsed, Mapping):
        issues.append(ValidationIssue("parse", parse_error or "top-level YAML value must be a mapping", severity="reject"))
        return ValidationResult(_graph(observed_nodes, _edges(observed_graph), observed_graph), False, True, issues)

    raw_nodes, raw_edges = parsed.get("nodes", []), parsed.get("edges", [])
    if not isinstance(raw_nodes, list) or not all(isinstance(n, Mapping) for n in raw_nodes):
        issues.append(ValidationIssue("node_schema", "nodes must be a list of mappings", severity="reject"))
        return ValidationResult(_graph(observed_nodes, _edges(observed_graph), observed_graph), False, True, issues)
    if not isinstance(raw_edges, list) or not all(isinstance(e, Mapping) for e in raw_edges):
        issues.append(ValidationIssue("edge_schema", "edges must be a list of mappings", severity="reject"))
        return ValidationResult(_graph(observed_nodes, _edges(observed_graph), observed_graph), False, True, issues)
    if any(not _scalar_identifier(node.get("id")) for node in raw_nodes):
        issues.append(ValidationIssue("node_schema", "node identifiers must be non-empty scalar values", severity="reject"))
        return ValidationResult(_graph(observed_nodes, _edges(observed_graph), observed_graph), False, True, issues)

    parsed_nodes = _nodes(parsed, observed=False)
    parsed_ids = [node.id for node in parsed_nodes]
    if len(parsed_ids) != len(set(parsed_ids)):
        issues.append(ValidationIssue("unique_identifier", "completion contains duplicate node identifiers", severity="reject"))
        return ValidationResult(_graph(observed_nodes, _edges(observed_graph), observed_graph), False, True, issues)
    if not observed_ids.issubset({n.id for n in parsed_nodes}):
        missing = sorted(observed_ids - {n.id for n in parsed_nodes})
        issues.append(ValidationIssue("observed_preservation", "completion omitted observed node(s): " + ", ".join(missing), severity="reject"))
        return ValidationResult(_graph(observed_nodes, _edges(observed_graph), observed_graph), False, True, issues)
    # ASP responses may echo the partial graph.  Treat identifiers already in
    # the observed graph as preserved observations rather than predictions.
    predicted = [n for n in parsed_nodes if n.id not in observed_ids]
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
        # reference_match is deliberately left unset here: validate_completion
        # takes no reference-graph parameter at all (see label_against_reference
        # below), so there is nothing for a decision to leak from. Per
        # IMPLEMENTATION_RESEARCH.md section 4.1, ground truth is permitted
        # only for post-hoc labels, never for online validation decisions.
        issues.append(ValidationIssue(code, message, node.id, "remove", support, None))
        invalid.add(node.id)

    for node in predicted:
        if node.id in invalid:
            continue
        if node.type not in _PREDICTABLE:
            fail("node_schema", "new nodes may only be objects or rooms", node)
            continue
        if node.type == "room":
            # 2026-09-15 bug fix: rooms in this pipeline's own wire format
            # NEVER carry a `dimension` field - confirmed on real data,
            # including the pipeline's own observed/tracked graphs, not
            # just LLM predictions (rooms are centroid+label only,
            # matched everywhere else in this codebase by a 4.0 m
            # distance threshold, never by AABB overlap - see the
            # `threshold = 4.0 if node.type == "room"` line below, and
            # room_overlap/room_containment above, which both already
            # `continue`/skip gracefully when `aabb(room) is None` rather
            # than failing). Requiring an AABB for rooms here was an
            # inconsistency with the rest of this file, not a deliberate
            # check - it silently rejected every predicted room (and,
            # via object_parent, everything predicted inside one),
            # dominating any "filter-only" result with a missing-field
            # artifact rather than a real structural-quality signal.
            if node.center is None:
                fail("finite_geometry", "predicted room must have a finite center", node)
        elif node.center is None or (config.require_dimensions and node.dimensions is None) or aabb(node) is None:
            fail("finite_geometry", "predicted node must have finite center and non-negative dimensions", node)

    # Remove malformed/unknown edges and enforce the prompt's two edge forms.
    valid_edges: List[Edge] = list(_edges(observed_graph))
    for raw_edge, edge in zip(raw_edges, edges):
        def endpoint(names: Tuple[str, ...]) -> Any:
            for name in names:
                if name in raw_edge:
                    return raw_edge[name]
            return None

        source, target = endpoint(("source", "from", "u")), endpoint(("target", "to", "v"))
        if not _scalar_identifier(source) or not _scalar_identifier(target):
            issues.append(ValidationIssue("edge_schema", "edge endpoints must be non-empty scalar identifiers"))
            continue
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
    for node in [n for n in active if n.id not in observed_ids and n.type == "room"]:
        box = aabb(node)
        if box is None:
            continue
        for other in rooms.values():
            if other.id == node.id or other.id in invalid:
                continue
            other_box = aabb(other)
            if other_box is not None and overlaps(box, other_box, tolerance=config.overlap_tolerance):
                fail("room_overlap", "predicted room overlaps an existing room", node)
                break

    active = [n for n in active if n.id not in invalid]
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
    rooms = {n.id: n for n in active if n.type == "room"}
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
        structures = [n for n in active if n.type == "structure" and n.label.lower() not in {"door", "opening"} and (n.label.lower() in _IMPASSABLE or not n.label)]
        doors = [n for n in active if n.type == "door" or n.label.lower() in {"door", "opening"}]
        parent_by_node: Dict[str, str] = {}
        for node in active:
            if node.type not in {"object", "room"} or node.id in observed_ids:
                continue
            parent = node.room_id
            if parent is None:
                parent_edge = next((e for e in valid_edges if node.id in (e.source, e.target) and active_by_id.get(e.source if e.target == node.id else e.target, Node("", "")).type == "room"), None)
                if parent_edge is not None:
                    parent = parent_edge.source if parent_edge.target == node.id else parent_edge.target
            if parent in rooms:
                parent_by_node[node.id] = parent
        for node in [n for n in active if n.id not in observed_ids and n.type in {"object", "room"} and n.id in parent_by_node and n.center is not None]:
            room = rooms.get(parent_by_node[node.id])
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


def label_against_reference(
    completion: Any,
    issues: Iterable[ValidationIssue],
    reference_graph: Mapping[str, Any],
) -> List[ValidationIssue]:
    """Post-hoc analysis only: attach reference_match to already-decided
    issues from a prior validate_completion() call.

    This function - not validate_completion/validate_ensemble - is the only
    place a reference graph may appear anywhere in this module. It never
    changes a node's fate (removed/rejected is already decided by the time
    this runs); it only annotates the resulting issues for diagnostics, per
    IMPLEMENTATION_RESEARCH.md section 4.1's "reference ground truth is
    permitted only for post-hoc labels, never for online validation
    decisions." Call it after validate_completion, on its own issues list,
    with a reference graph the validator itself never saw.
    """
    if isinstance(completion, Mapping) and completion.get("nodes") is not None:
        parsed: Optional[Mapping[str, Any]] = completion
    else:
        parsed, parse_error = _parse_completion(completion)
        if parse_error or not isinstance(parsed, Mapping):
            return list(issues)
    predicted_by_id = {n.id: n for n in _nodes(parsed, observed=False)}
    reference_nodes = _nodes(reference_graph)

    # Match the hypotheses referenced by issues one-to-one, with the same
    # semantic/centroid rule used by the evaluator (case-insensitive labels).
    candidates = []
    for node_id, node in predicted_by_id.items():
        if node.center is None:
            continue
        threshold = 4.0 if node.type == "room" else 0.5
        for index, ref in enumerate(reference_nodes):
            if ref.center is None or ref.type != node.type or ref.label.strip().casefold() != node.label.strip().casefold():
                continue
            separation = sum((ref.center[i] - node.center[i]) ** 2 for i in range(3)) ** 0.5
            if separation <= threshold:
                candidates.append((separation, node_id, index))
    matched_nodes: Set[str] = set()
    matched_references: Set[int] = set()
    node_matches: Dict[str, bool] = {}
    for separation, node_id, index in sorted(candidates, key=lambda item: item[0]):
        if node_id in matched_nodes or index in matched_references:
            continue
        matched_nodes.add(node_id)
        matched_references.add(index)
        node_matches[node_id] = True

    labeled: List[ValidationIssue] = []
    for issue in issues:
        node = predicted_by_id.get(issue.node_id) if issue.node_id else None
        matched = node_matches.get(issue.node_id, False) if node is not None else issue.reference_match
        labeled.append(ValidationIssue(issue.code, issue.message, issue.node_id, issue.severity, issue.original_support, matched))
    return labeled


def validate_ensemble(
    completions: Iterable[Any],
    observed_graph: Mapping[str, Any],
    config: ValidationConfig = ValidationConfig(),
) -> List[ValidationResult]:
    """Validate K samples; if all fail, return one observed-graph fallback."""
    results = [validate_completion(c, observed_graph, config) for c in completions]
    if results and any(r.accepted for r in results):
        return results
    observed_nodes = _nodes(observed_graph, observed=True)
    fallback = _graph(observed_nodes, _edges(observed_graph), observed_graph)
    fallback["frontier_fallback"] = {
        "strategy": "geometric",
        "candidates": _geometric_frontier_candidates(observed_nodes),
    }
    issue = ValidationIssue("ensemble_fallback", "all completions failed; continuing with observed graph and geometric frontier fallback", severity="fallback")
    return results + [ValidationResult(fallback, True, False, [issue])]
