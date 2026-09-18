from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence


class PoseController(Protocol):
    def set_pose(self, pose: Any) -> Any: ...
    def observe(self) -> Any: ...


@dataclass
class PassiveNavAudit:
    controller: PoseController
    pathfinder: Any = None
    logger: Optional[Callable[[Mapping[str, Any]], None]] = None
    requested_m: float = 0.0
    realized_m: float = 0.0

    def command(self, pose: Sequence[float], *, stage: str, segment: str, command_id: str,
                previous_pose: Optional[Sequence[float]] = None) -> Any:
        previous = list(previous_pose) if previous_pose is not None else None
        requested = list(pose)
        admissible = None
        geodesic = None
        if self.pathfinder is not None and previous is not None:
            if hasattr(self.pathfinder, "is_navigable"): admissible = bool(self.pathfinder.is_navigable(requested))
            if hasattr(self.pathfinder, "geodesic_distance"): geodesic = self.pathfinder.geodesic_distance(previous, requested)
        if geodesic is None and previous is not None:
            geodesic = math.dist(previous[:3], requested[:3])
        self.requested_m += float(geodesic or 0.0)
        result = self.controller.set_pose(pose)  # exactly one delegated state command
        record = {"stage": stage, "segment": segment, "command_id": command_id,
                  "previous_pose": previous, "requested_pose": requested,
                  "result_pose": result, "pathfinder_admissible": admissible,
                  "shortest_path_length": geodesic, "requested_cumulative_path_m": self.requested_m,
                  "realized_cumulative_path_m": self.realized_m,
                  "planner_outcome": "pose_command_delegated", "contact": False}
        if self.logger: self.logger(record)
        return result

    def observe(self) -> Any:
        return self.controller.observe()  # passive wrapper never changes observations


class HabitatPassiveAdapter(PassiveNavAudit):
    """Habitat-Sim integration point; only documented read-only pathfinder calls are used."""

    def __init__(self, controller: PoseController, simulator: Any, **kwargs: Any) -> None:
        pathfinder = getattr(simulator, "pathfinder", None)
        super().__init__(controller, pathfinder=pathfinder, **kwargs)

    def lifecycle_event(self, name: str, *, stage: str, command_id: str) -> None:
        if name not in {"rotation", "reset", "teleport", "planner_abort", "planner_success"}:
            raise ValueError("unsupported lifecycle event")
        if self.logger:
            self.logger({"stage": stage, "command_id": command_id, "event": name,
                         "planner_outcome": name, "contact": False})
