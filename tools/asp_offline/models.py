from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

Vec3 = Tuple[float, float, float]


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    label: str = ""
    center: Optional[Vec3] = None
    dimensions: Optional[Vec3] = None
    room_id: Optional[str] = None
    observed: bool = False
    data: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any], *, observed: bool = False) -> "Node":
        center = raw.get("center", raw.get("position", raw.get("translation")))
        dims = raw.get("dimensions", raw.get("size", raw.get("extent")))
        def vec(v: Any) -> Optional[Vec3]:
            if isinstance(v, Mapping):
                v = [v.get("x"), v.get("y"), v.get("z")]
            if not isinstance(v, (list, tuple)) or len(v) != 3:
                return None
            try:
                return (float(v[0]), float(v[1]), float(v[2]))
            except (TypeError, ValueError):
                return None
        room_id = raw.get("room_id", raw.get("parent_room", raw.get("parent")))
        return cls(str(raw.get("id", "")), str(raw.get("type", "")),
                   str(raw.get("label", raw.get("category", ""))), vec(center),
                   vec(dims), str(room_id) if room_id is not None else None,
                   bool(raw.get("observed", observed)), dict(raw))

    def as_dict(self) -> Dict[str, Any]:
        result = dict(self.data)
        result.update({"id": self.id, "type": self.type})
        if self.label:
            result["label"] = self.label
        if self.center is not None:
            result["center"] = list(self.center)
        if self.dimensions is not None:
            result["dimensions"] = list(self.dimensions)
        if self.room_id is not None:
            result["room_id"] = self.room_id
        return result


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    type: str = ""

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "Edge":
        source = raw.get("source", raw.get("from", raw.get("u", "")))
        target = raw.get("target", raw.get("to", raw.get("v", "")))
        return cls(str(source), str(target), str(raw.get("type", raw.get("relation", ""))))

    def as_dict(self) -> Dict[str, str]:
        result = {"source": self.source, "target": self.target}
        if self.type:
            result["type"] = self.type
        return result


Graph = Dict[str, Any]


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    node_id: Optional[str] = None
    severity: str = "remove"
    original_support: Optional[float] = None
    reference_match: Optional[bool] = None

    def as_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message,
                "node_id": self.node_id, "severity": self.severity,
                "original_support": self.original_support,
                "reference_match": self.reference_match}


@dataclass
class ValidationResult:
    graph: Graph
    accepted: bool
    rejected: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    removed_nodes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {"graph": self.graph, "accepted": self.accepted,
                "rejected": self.rejected,
                "issues": [i.as_dict() for i in self.issues],
                "removed_nodes": self.removed_nodes}


@dataclass(frozen=True)
class Hypothesis:
    label: str
    parent_room: Optional[str]
    center: Vec3
    support: float = 0.0
    calibrated_support: Optional[float] = None
    node_id: Optional[str] = None
    kind: str = "object"
