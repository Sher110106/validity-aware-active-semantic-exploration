"""Minimal paired-run state machine with no outcome-based transitions."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .control import Control, EventLog, atomic_json, can_continue, validate_artifacts, write_completion_marker
from .interfaces import MotionDetourRunner


class Phase(str, Enum):
    READY = "ready"
    RESERVED = "reserved"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


@dataclass
class RunState:
    phase: Phase = Phase.READY
    attempt: int = 1
    reason: str = ""


class CampaignSupervisor:
    def __init__(self, status_path: Path, event_log: EventLog, runner: MotionDetourRunner):
        self.status_path, self.events, self.runner = status_path, event_log, runner
        self.state = RunState()

    def _save(self) -> None:
        atomic_json(self.status_path, {"phase": self.state.phase.value, "attempt": self.state.attempt,
                                       "reason": self.state.reason})

    def start(self, run_path: Path, *, scene: str, seed: int, policy: str, horizon: int,
              control: Control) -> bool:
        if self.state.phase not in (Phase.READY, Phase.RESERVED):
            return False
        okay, reason = can_continue(connectivity_ok=self.runner.connectivity_ok(), disk_gb=100,
                                     stalled=False, runtime_exceeded=False, control=control)
        if not okay:
            self.state = RunState(Phase.PAUSED, self.state.attempt, reason)
            self._save(); self.events.append("paused", reason=reason)
            return False
        self.state = RunState(Phase.RUNNING, self.state.attempt)
        self._save(); self.events.append("launch_intent", path=str(run_path))
        self.runner.launch(run_path, scene=scene, seed=seed, policy=policy, horizon=horizon)
        return True

    def finish(self, run_path: Path, required: tuple[str, ...]) -> bool:
        if self.state.phase != Phase.RUNNING or not self.runner.stop(run_path):
            self.state = RunState(Phase.INCOMPLETE, self.state.attempt, "stop or state failed")
            self._save(); self.events.append("incomplete", reason=self.state.reason)
            return False
        ok, reason = validate_artifacts(run_path, required)
        if not ok:
            self.state = RunState(Phase.INCOMPLETE, self.state.attempt, reason)
            self._save(); self.events.append("incomplete", reason=reason)
            return False
        write_completion_marker(run_path, required=required)
        self.state = RunState(Phase.COMPLETE, self.state.attempt, "validated")
        self._save(); self.events.append("complete", path=str(run_path))
        return True
