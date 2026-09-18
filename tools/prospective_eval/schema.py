"""JSON-compatible records for prospective motion evaluation.

The schema intentionally uses ``unknown`` rather than inferring physical facts
from planner output, object geometry, or a controller's bookkeeping.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

Vec3 = Tuple[float, float, float]


class EventTaxonomy(str, Enum):
    PLANNER_FAILURE = "planner_failure"
    OBJECT_BOX_OVERLAP = "object_box_overlap"
    NAVMESH_AUDIT_REJECTION = "navmesh_audit_rejection"
    NAVMESH_AUDIT_CLIPPING = "navmesh_audit_clipping"
    PHYSICAL_CONTACT = "physical_contact"
    BLOCKED_MOTION = "blocked_motion"
    UNKNOWN = "unknown"


class MotionOutcome(str, Enum):
    REACHED = "reached"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    PLANNER_FAILED = "planner_failed"
    UNKNOWN = "unknown"


class Classification(str, Enum):
    SUPPORTED = "supported"
    REFERENCE_UNMATCHED = "reference_unmatched"
    UNKNOWN = "unknown"
    CONFIRMED_FALSE_POSITIVE = "confirmed_false_positive"


def _vec(value: Sequence[float]) -> Vec3:
    if len(value) != 3:
        raise ValueError("pose must have three coordinates")
    result = tuple(float(x) for x in value)
    if not all(math.isfinite(x) for x in result):
        raise ValueError("pose coordinates must be finite")
    return result  # type: ignore[return-value]


@dataclass(frozen=True)
class Pose:
    position: Vec3
    rotation: Optional[Tuple[float, ...]] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "position", _vec(self.position))
        if self.rotation is not None:
            rotation = tuple(float(x) for x in self.rotation)
            if not all(math.isfinite(x) for x in rotation):
                raise ValueError("rotation must be finite")
            object.__setattr__(self, "rotation", rotation)

    def as_dict(self) -> Dict[str, Any]:
        return {"position": list(self.position), "rotation": list(self.rotation) if self.rotation else None}


def pose_distance(a: Pose, b: Pose) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a.position, b.position)))


@dataclass(frozen=True)
class MotionEvent:
    event_id: str
    timestamp: str
    stage_id: str
    segment_id: str
    command_id: str
    previous_pose: Pose
    requested_pose: Pose
    result_pose: Optional[Pose]
    nominal_distance_m: float
    pose_derived_distance_m: Optional[float]
    outcome: MotionOutcome
    taxonomy: EventTaxonomy
    planner_outcome: str
    reachability_outcome: str
    passive_navmesh_admissible: Optional[bool]
    clipping_delta_m: Optional[float]
    reset: bool = False
    teleport: bool = False
    rotation_only: bool = False
    controller_mode: str = "passive"
    observation_hash: Optional[str] = None
    command_hash: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.nominal_distance_m < 0 or not math.isfinite(self.nominal_distance_m):
            raise ValueError("nominal distance must be finite and non-negative")
        if self.controller_mode == "passive" and self.taxonomy == EventTaxonomy.PHYSICAL_CONTACT:
            raise ValueError("passive mode cannot assert physical contact")

    def as_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        raw.update({"outcome": self.outcome.value, "taxonomy": self.taxonomy.value})
        return raw


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


class AppendOnlyLog:
    """JSONL logger with a checksum per record; never rewrites prior records."""

    def __init__(self, path: str) -> None:
        self.path = path

    def append(self, record: Mapping[str, Any]) -> str:
        payload = dict(record)
        payload["record_sha256"] = stable_hash(payload)
        line = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with open(self.path, "a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        return payload["record_sha256"]
