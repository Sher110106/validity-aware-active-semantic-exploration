"""Read-only navmesh audit and receipt-gated altered execution taxonomy."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Protocol

from .schema import ControllerMode, EventTaxonomy, Pose, _timestamp, _identifier, _finite


class PathfinderAdapter(Protocol):
    """Habitat adapter contract: query-only, no set_state/step/RNG mutation."""

    def is_navigable(self, position: tuple[float, float, float]) -> bool: ...
    def try_find_path(self, start: tuple[float, float, float], goal: tuple[float, float, float]) -> Optional[float]: ...


@dataclass(frozen=True)
class AuditResult:
    admissible: Optional[bool]
    path_distance_m: Optional[float]
    taxonomy: EventTaxonomy
    reason: str


class PassiveNavmeshAuditor:
    def __init__(self, adapter: PathfinderAdapter) -> None:
        self.adapter = adapter

    def audit(self, previous: Pose, requested: Pose) -> AuditResult:
        try:
            if self.adapter.is_navigable(requested.position) is not True:
                return AuditResult(False, None, EventTaxonomy.NAVMESH_AUDIT_REJECTION, "goal_not_navigable")
            distance = self.adapter.try_find_path(previous.position, requested.position)
            if distance is None:
                return AuditResult(False, None, EventTaxonomy.NAVMESH_AUDIT_REJECTION, "no_path")
            distance = _finite(distance, "path_distance_m", nonnegative=True)
            return AuditResult(True, distance, EventTaxonomy.UNKNOWN, "admissible")
        except (Exception, ValueError, TypeError):
            return AuditResult(None, None, EventTaxonomy.UNKNOWN, "pathfinder_unavailable_or_invalid")


@dataclass(frozen=True)
class EngineEventReceipt:
    source: str
    event_type: str
    execution_id: str
    timestamp: str
    provenance_hash: str
    contact: bool = False
    blocked: bool = False

    ALLOWED_SOURCES = frozenset({"habitat_sim", "habitat_physics", "engine_contact_sensor"})
    ALLOWED_TYPES = frozenset({"contact", "blocked_motion"})

    def valid_for(self, execution_id: str, *, require: str) -> bool:
        try:
            _identifier(execution_id, "execution_id")
            _timestamp(self.timestamp)
            _identifier(self.source, "source")
            _identifier(self.event_type, "event_type")
        except ValueError:
            return False
        if self.source not in self.ALLOWED_SOURCES or self.event_type not in self.ALLOWED_TYPES:
            return False
        if self.execution_id != execution_id or not self.provenance_hash:
            return False
        return (require == "contact" and self.contact and self.event_type == "contact") or (require == "blocked" and self.blocked and self.event_type == "blocked_motion")


@dataclass(frozen=True)
class RealizedMotion:
    requested: Pose
    realized: Optional[Pose]
    execution_id: str
    engine_receipt: Optional[EngineEventReceipt] = None


def taxonomy_for_realized_motion(motion: RealizedMotion, mode: ControllerMode) -> EventTaxonomy:
    mode = ControllerMode(mode)
    if mode != ControllerMode.COLLISION_AWARE_EXPERIMENT or motion.realized is None:
        return EventTaxonomy.UNKNOWN
    if motion.engine_receipt and motion.engine_receipt.valid_for(motion.execution_id, require="contact"):
        return EventTaxonomy.PHYSICAL_CONTACT
    if motion.engine_receipt and motion.engine_receipt.valid_for(motion.execution_id, require="blocked"):
        return EventTaxonomy.BLOCKED_MOTION
    return EventTaxonomy.UNKNOWN
