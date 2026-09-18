"""Validated, JSON-compatible records for prospective motion evaluation."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

Vec3 = Tuple[float, float, float]
POSITION_TOLERANCE_M = 1e-4
ROTATION_TOLERANCE = 1e-4
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


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


class ControllerMode(str, Enum):
    PASSIVE = "passive"
    COLLISION_AWARE_EXPERIMENT = "collision_aware_experiment"


class Classification(str, Enum):
    SUPPORTED = "supported"
    REFERENCE_UNMATCHED = "reference_unmatched"
    UNKNOWN = "unknown"
    CONFIRMED_FALSE_POSITIVE = "confirmed_false_positive"


def _finite(value: float, name: str, *, nonnegative: bool = False) -> float:
    value = float(value)
    if not math.isfinite(value) or (nonnegative and value < 0):
        raise ValueError(f"{name} must be finite" + (" and non-negative" if nonnegative else ""))
    return value


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{name} must be a non-empty stable identifier")
    return value


def _timestamp(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("timestamp must be a non-empty ISO timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO formatted") from exc
    return value


def _vec(value: Sequence[float]) -> Vec3:
    if len(value) != 3:
        raise ValueError("pose must have three coordinates")
    result = tuple(_finite(float(x), "pose coordinate") for x in value)
    return result  # type: ignore[return-value]


@dataclass(frozen=True)
class Pose:
    position: Vec3
    rotation: Optional[Tuple[float, ...]] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "position", _vec(self.position))
        if self.rotation is not None:
            rotation = tuple(_finite(float(x), "rotation") for x in self.rotation)
            if not rotation:
                raise ValueError("rotation cannot be empty")
            object.__setattr__(self, "rotation", rotation)

    def as_dict(self) -> Dict[str, Any]:
        return {"position": list(self.position), "rotation": list(self.rotation) if self.rotation is not None else None}


def position_error(a: Pose, b: Pose) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a.position, b.position)))


def rotation_error(a: Pose, b: Pose) -> float:
    if a.rotation is None or b.rotation is None:
        return 0.0 if a.rotation == b.rotation else math.inf
    if len(a.rotation) != len(b.rotation):
        return math.inf
    return max(abs(x - y) for x, y in zip(a.rotation, b.rotation))


def pose_distance(a: Pose, b: Pose) -> float:
    return position_error(a, b)


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
    requested_distance_m: float
    actual_displacement_m: Optional[float]
    target_position_error_m: Optional[float]
    target_rotation_error: Optional[float]
    clipping_delta_m: Optional[float]
    outcome: MotionOutcome
    taxonomy: EventTaxonomy
    planner_outcome: str
    reachability_outcome: str
    passive_navmesh_admissible: Optional[bool]
    reset: bool = False
    teleport: bool = False
    rotation_only: bool = False
    controller_mode: ControllerMode = ControllerMode.PASSIVE
    observation_hash: Optional[str] = None
    command_hash: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("event_id", "stage_id", "segment_id", "command_id"):
            _identifier(getattr(self, name), name)
        _timestamp(self.timestamp)
        _finite(self.requested_distance_m, "requested_distance_m", nonnegative=True)
        for name in ("actual_displacement_m", "target_position_error_m", "target_rotation_error", "clipping_delta_m"):
            value = getattr(self, name)
            if value is not None:
                _finite(value, name, nonnegative=True)
        if isinstance(self.controller_mode, str):
            object.__setattr__(self, "controller_mode", ControllerMode(self.controller_mode))
        if self.controller_mode == ControllerMode.PASSIVE and self.taxonomy in {EventTaxonomy.PHYSICAL_CONTACT, EventTaxonomy.BLOCKED_MOTION}:
            raise ValueError("passive mode cannot assert contact or blocked motion")
        if self.taxonomy == EventTaxonomy.PHYSICAL_CONTACT and self.controller_mode != ControllerMode.COLLISION_AWARE_EXPERIMENT:
            raise ValueError("physical contact requires altered mode")

    def as_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        raw["controller_mode"] = self.controller_mode.value
        raw["outcome"] = self.outcome.value
        raw["taxonomy"] = self.taxonomy.value
        return raw


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class EvidenceReceipt:
    receipt_id: str
    kind: str
    payload: Mapping[str, Any]
    payload_hash: str
    receipt_hash: str

    @classmethod
    def issue(cls, receipt_id: str, kind: str, payload: Mapping[str, Any]) -> "EvidenceReceipt":
        _identifier(receipt_id, "receipt_id")
        _identifier(kind, "kind")
        payload_hash = stable_hash(payload)
        receipt_hash = stable_hash({"receipt_id": receipt_id, "kind": kind, "payload_hash": payload_hash})
        return cls(receipt_id, kind, dict(payload), payload_hash, receipt_hash)

    def verify(self) -> bool:
        return (
            _ID.fullmatch(self.receipt_id) is not None
            and _ID.fullmatch(self.kind) is not None
            and self.payload_hash == stable_hash(self.payload)
            and self.receipt_hash == stable_hash({"receipt_id": self.receipt_id, "kind": self.kind, "payload_hash": self.payload_hash})
        )


class AppendOnlyLog:
    """Contained, owner-only, chained JSONL log with reader verification."""

    def __init__(self, path: str, *, root: str) -> None:
        import fcntl
        self.path = Path(path).resolve()
        self.root = Path(root).resolve()
        if self.root not in self.path.parents:
            raise ValueError("log path must be contained by root")
        self.root.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.is_symlink():
            raise ValueError("refusing symlink log")
        self.path.touch(exist_ok=True, mode=0o600)
        os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
        self._fcntl = fcntl

    def append(self, record: Mapping[str, Any]) -> str:
        with self.path.open("a+", encoding="utf-8") as stream:
            self._fcntl.flock(stream.fileno(), self._fcntl.LOCK_EX)
            stream.seek(0)
            previous = "0" * 64
            sequence = 0
            for line in stream:
                if line.strip():
                    old = json.loads(line)
                    sequence = old["sequence"]
                    previous = old["record_sha256"]
            payload = dict(record)
            payload.update({"sequence": sequence + 1, "previous_sha256": previous})
            payload["record_sha256"] = stable_hash(payload)
            stream.seek(0, os.SEEK_END)
            stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            self._fcntl.flock(stream.fileno(), self._fcntl.LOCK_UN)
            return payload["record_sha256"]

    def verify(self) -> bool:
        previous, sequence = "0" * 64, 0
        with self.path.open(encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                if record["sequence"] != sequence + 1 or record["previous_sha256"] != previous:
                    return False
                digest = record.pop("record_sha256")
                if digest != stable_hash(record):
                    return False
                previous, sequence = digest, sequence + 1
        return True
