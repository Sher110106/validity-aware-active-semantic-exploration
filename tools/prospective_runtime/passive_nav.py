from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence


class PoseController(Protocol):
    def get_state(self) -> Any: ...
    def set_state(self, state: Any) -> Any: ...
    def observe(self) -> Any: ...


def _position(state: Any) -> Optional[Sequence[float]]:
    value = getattr(state, "position", None)
    if value is None and isinstance(state, Mapping): value = state.get("position")
    return tuple(float(x) for x in value) if value is not None and len(value) == 3 else None


@dataclass
class HabitatPassiveAdapter:
    """Passive Habitat-Sim audit using only ShortestPath/find_path and agent state."""
    agent: PoseController
    simulator: Any
    logger: Optional[Callable[[Mapping[str, Any]], None]] = None
    requested_m: float = 0.0
    realized_m: float = 0.0

    def _geodesic(self, start: Optional[Sequence[float]], end: Optional[Sequence[float]]) -> Optional[float]:
        if start is None or end is None: return None
        try:
            import habitat_sim  # type: ignore
            path = habitat_sim.ShortestPath()
            path.requested_start = start
            path.requested_end = end
            if not self.simulator.pathfinder.find_path(path): return None
            value = path.geodesic_distance
            return float(value) if value is not None and value >= 0 else None
        except Exception:
            return None

    def command(self, requested_state: Any, *, stage: str, segment: str, command_id: str,
                event: str = "pose_command") -> Any:
        before = copy.deepcopy(self.agent.get_state())
        before_position = _position(before)
        requested_position = _position(requested_state)
        requested_segment = self._geodesic(before_position, requested_position)
        # Exactly one state mutation; this adapter never clips, teleports, or claims contact.
        result = self.agent.set_state(requested_state)
        after = copy.deepcopy(self.agent.get_state())
        after_position = _position(after)
        realized_segment = self._geodesic(before_position, after_position)
        if requested_segment is not None: self.requested_m += requested_segment
        if realized_segment is not None: self.realized_m += realized_segment
        record = {"stage": stage, "segment": segment, "command_id": command_id,
                  "event": event, "previous_pose": before_position,
                  "requested_pose": requested_position, "result_pose": after_position,
                  "pathfinder_admissible": requested_segment is not None,
                  "shortest_path_length": requested_segment,
                  "realized_segment_path_length": realized_segment,
                  "requested_cumulative_path_m": self.requested_m,
                  "realized_cumulative_path_m": self.realized_m,
                  "planner_outcome": "delegated", "contact": None}
        if self.logger: self.logger(record)
        return result

    def observe(self) -> Any:
        return self.agent.observe()

    def lifecycle_event(self, name: str, *, stage: str, command_id: str) -> None:
        if name not in {"rotation", "reset", "teleport", "planner_abort", "planner_success"}:
            raise ValueError("unsupported lifecycle event")
        if self.logger: self.logger({"stage": stage, "command_id": command_id, "event": name, "contact": None})
