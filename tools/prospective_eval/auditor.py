"""Read-only navmesh auditing and the explicitly separate altered-mode contract."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol

from .schema import EventTaxonomy, MotionOutcome, Pose


class PathfinderAdapter(Protocol):
    """Small Habitat adapter; implementations must not mutate simulator state."""

    def is_navigable(self, position: tuple[float, float, float]) -> bool: ...

    def try_find_path(self, start: tuple[float, float, float], goal: tuple[float, float, float]) -> Optional[float]: ...


@dataclass(frozen=True)
class AuditResult:
    admissible: Optional[bool]
    path_distance_m: Optional[float]
    taxonomy: EventTaxonomy
    reason: str


class PassiveNavmeshAuditor:
    """Audits a request without calling set_state, stepping, or changing RNG."""

    def __init__(self, adapter: PathfinderAdapter) -> None:
        self.adapter = adapter

    def audit(self, previous: Pose, requested: Pose) -> AuditResult:
        if not self.adapter.is_navigable(requested.position):
            return AuditResult(False, None, EventTaxonomy.NAVMESH_AUDIT_REJECTION, "goal_not_navigable")
        distance = self.adapter.try_find_path(previous.position, requested.position)
        if distance is None:
            return AuditResult(False, None, EventTaxonomy.NAVMESH_AUDIT_REJECTION, "no_path")
        return AuditResult(True, distance, EventTaxonomy.UNKNOWN, "admissible")


@dataclass(frozen=True)
class RealizedMotion:
    requested: Pose
    realized: Optional[Pose]
    contact: Optional[bool]
    blocked: Optional[bool]
    engine_signal: str


class CollisionAwareExecutor(Protocol):
    """Optional controller-altering experiment; never enabled by default."""

    enabled: bool

    def execute(self, requested: Pose) -> RealizedMotion: ...


def validate_controller_mode(mode: str) -> None:
    if mode not in {"passive", "collision_aware_experiment"}:
        raise ValueError(f"unsupported controller mode: {mode}")
    if mode == "collision_aware_experiment":
        # This function is intentionally only a contract guard, not an executor.
        return


def taxonomy_for_realized_motion(motion: RealizedMotion, mode: str) -> EventTaxonomy:
    validate_controller_mode(mode)
    if mode != "collision_aware_experiment":
        return EventTaxonomy.UNKNOWN
    if motion.contact is True:
        return EventTaxonomy.PHYSICAL_CONTACT
    if motion.blocked is True:
        return EventTaxonomy.BLOCKED_MOTION
    return EventTaxonomy.UNKNOWN
