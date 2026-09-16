"""Pure decision policy for the ASP matrix supervisor.

This module deliberately knows nothing about Docker or the host filesystem.
That keeps resource-affecting decisions testable without touching a live run.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import List


@dataclass(frozen=True)
class RunSpec:
    scene: str
    scene_number: int
    scene_path: str
    seed: int

    @property
    def name(self) -> str:
        return f"scene{self.scene}_seed{self.seed}_matrix120m"


SCENES = (
    (
        "00069",
        69,
        "/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/"
        "train/00069-Y8Y6ukxGMvn/Y8Y6ukxGMvn.basis.glb",
    ),
    (
        "00573",
        573,
        "/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/"
        "train/00573-1zDbEdygBeW/1zDbEdygBeW.basis.glb",
    ),
    (
        "00853",
        853,
        "/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/"
        "val/00853-5cdEh9F2hJL/5cdEh9F2hJL.basis.glb",
    ),
    (
        "00871",
        871,
        "/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/"
        "val/00871-VBzV5z6i1WS/VBzV5z6i1WS.basis.glb",
    ),
)


def build_seed_major_plan() -> List[RunSpec]:
    return [
        RunSpec(scene, scene_number, scene_path, seed)
        for seed in (42, 43, 44)
        for scene, scene_number, scene_path in SCENES
    ]


@dataclass
class Control:
    paused: bool = False
    target_path_m: float = 120.0
    min_free_disk_gb: float = 25.0
    ambiguous_stall_seconds: int = 30 * 60
    max_attempts: int = 2
    future_max_calls: int = 3000
    poll_seconds: int = 60


@dataclass
class State:
    phase: str
    attempt: int
    last_path_m: float
    last_calls: int
    last_progress_at: float
    container_gpu_failures: int = 0
    blocker: str | None = None
    resume_generation_seen: int = 0
    infrastructure_recovery_failures: int = 0
    launch_recovery_attempts: int = 0
    host_gpu_failures: int = 0

    @classmethod
    def running(
        cls,
        *,
        now: float,
        attempt: int,
        path_m: float,
        calls: int,
    ) -> "State":
        return cls("running", attempt, path_m, calls, now)

    @classmethod
    def ready(cls, *, now: float, attempt: int) -> "State":
        return cls("ready", attempt, 0.0, 0, now)


@dataclass
class Observation:
    now: float
    container_running: bool
    host_gpu_ok: bool
    container_gpu_ok: bool
    pipeline_pids: list[int]
    ros_pids: list[int]
    path_m: float
    calls: int
    free_disk_gb: float
    hard_cap_exceeded: bool = False
    traceback_found: bool = False
    pipeline_log_dirs: list[str] = field(default_factory=list)
    pipeline_matches_run: bool = True
    container_inspection_ok: bool = True
    process_inspection_ok: bool = True
    inspection_errors: list[str] = field(default_factory=list)

    @classmethod
    def healthy(cls, *, now: float, path_m: float, calls: int) -> "Observation":
        return cls(
            now=now,
            container_running=True,
            host_gpu_ok=True,
            container_gpu_ok=True,
            pipeline_pids=[100],
            ros_pids=[200],
            path_m=path_m,
            calls=calls,
            free_disk_gb=100.0,
        )

    @classmethod
    def idle(cls, *, now: float, free_disk_gb: float = 100.0) -> "Observation":
        return cls(
            now=now,
            container_running=True,
            host_gpu_ok=True,
            container_gpu_ok=True,
            pipeline_pids=[],
            ros_pids=[],
            path_m=0.0,
            calls=0,
            free_disk_gb=free_disk_gb,
        )


class ActionKind(str, Enum):
    NONE = "none"
    PAUSE = "pause"
    START_CONTAINER = "start_container"
    HEAL_CONTAINER_GPU = "heal_container_gpu"
    STOP_AT_BUDGET = "stop_at_budget"
    RETRY_RUN = "retry_run"
    LAUNCH_RUN = "launch_run"
    VALIDATE_COMPLETE = "validate_complete"


@dataclass(frozen=True)
class Decision:
    kind: ActionKind
    reason: str
    state: State


def bootstrap_state(
    *,
    now: float,
    active_index: int,
    active_pipeline: bool,
    failed_attempts: int,
    observed_path_m: float,
    observed_calls: int,
) -> State:
    """Create initial state without taking an action on the live process."""
    del active_index  # Queue position is persisted by the runtime state wrapper.
    attempt = max(1, failed_attempts + 1)
    if active_pipeline:
        return State.running(
            now=now,
            attempt=attempt,
            path_m=observed_path_m,
            calls=observed_calls,
        )
    return State.ready(now=now, attempt=attempt)


def _progressed(state: State, observation: Observation) -> State:
    if (
        observation.path_m > state.last_path_m + 1e-9
        or observation.calls > state.last_calls
    ):
        return replace(
            state,
            last_path_m=observation.path_m,
            last_calls=observation.calls,
            last_progress_at=observation.now,
            blocker=None,
        )
    return replace(
        state,
        last_path_m=max(state.last_path_m, observation.path_m),
        last_calls=max(state.last_calls, observation.calls),
    )


def _failure_decision(state: State, control: Control, reason: str) -> Decision:
    if state.attempt < control.max_attempts:
        return Decision(ActionKind.RETRY_RUN, reason, state)
    blocked = replace(state, phase="paused", blocker=f"{reason}; retry limit reached")
    return Decision(ActionKind.PAUSE, blocked.blocker or reason, blocked)


def choose_action(
    state: State,
    observation: Observation,
    control: Control,
) -> Decision:
    """Select at most one resource-affecting action for this cycle."""
    state = _progressed(state, observation)
    if not control.paused and state.blocker == "automation paused by operator":
        state = replace(state, blocker=None)

    if not observation.container_inspection_ok or not observation.process_inspection_ok:
        reason = "health inspection unavailable; refusing process action"
        return Decision(ActionKind.NONE, reason, replace(state, blocker=reason))
    if state.blocker and state.blocker.startswith("health inspection unavailable"):
        state = replace(state, blocker=None)

    # The path budget remains enforceable even when queue automation is paused.
    if observation.path_m >= control.target_path_m:
        if observation.pipeline_pids:
            return Decision(
                ActionKind.STOP_AT_BUDGET,
                f"path {observation.path_m:.3f} m reached target",
                state,
            )
        return Decision(
            ActionKind.VALIDATE_COMPLETE,
            f"stopped run reached {observation.path_m:.3f} m",
            state,
        )

    if not observation.host_gpu_ok:
        failures = state.host_gpu_failures + 1
        state = replace(state, host_gpu_failures=failures)
        if failures < 2:
            return Decision(
                ActionKind.NONE,
                "host GPU failed first check; waiting for confirmation",
                state,
            )
        blocked = replace(state, phase="paused", blocker="host GPU is unhealthy")
        return Decision(ActionKind.PAUSE, blocked.blocker or "host GPU", blocked)
    state = replace(state, host_gpu_failures=0)

    if not observation.container_running:
        return Decision(
            ActionKind.START_CONTAINER,
            "container is not running",
            state,
        )

    if not observation.container_gpu_ok:
        failures = state.container_gpu_failures + 1
        state = replace(state, container_gpu_failures=failures)
        if failures >= 2:
            return Decision(
                ActionKind.HEAL_CONTAINER_GPU,
                "container GPU failed two consecutive checks",
                state,
            )
        return Decision(
            ActionKind.NONE,
            "container GPU failed first check; waiting for confirmation",
            state,
        )
    cleared_blocker = state.blocker
    if cleared_blocker and cleared_blocker.startswith(
        "container restart or GPU verification failed"
    ):
        cleared_blocker = None
    state = replace(
        state,
        container_gpu_failures=0,
        infrastructure_recovery_failures=0,
        blocker=cleared_blocker,
    )

    if len(observation.pipeline_pids) > 1:
        blocked = replace(state, phase="paused", blocker="multiple pipeline processes")
        return Decision(ActionKind.PAUSE, blocked.blocker or "multiple pipelines", blocked)

    if observation.pipeline_pids and not observation.pipeline_matches_run:
        reason = "active pipeline belongs to a different run"
        blocked = replace(state, phase="paused", blocker=reason)
        return Decision(ActionKind.PAUSE, reason, blocked)

    # Operator pause blocks launches and retries, but intentionally does not
    # disable the path budget or infrastructure/GPU safety checks above.
    if control.paused:
        blocked = replace(state, blocker="automation paused by operator")
        return Decision(ActionKind.PAUSE, blocked.blocker or "paused", blocked)

    if observation.hard_cap_exceeded:
        return _failure_decision(state, control, "LLM hard cap exceeded")

    if observation.traceback_found:
        return _failure_decision(state, control, "uncaptured traceback found")

    if state.phase == "running" and not observation.pipeline_pids:
        return _failure_decision(state, control, "pipeline exited before path target")

    if state.phase == "running":
        stalled_for = observation.now - state.last_progress_at
        if stalled_for >= control.ambiguous_stall_seconds:
            reason = f"ambiguous stall for {int(stalled_for)} seconds"
            blocked = replace(state, phase="paused", blocker=reason)
            return Decision(ActionKind.PAUSE, reason, blocked)

    if state.phase == "ready":
        if observation.free_disk_gb < control.min_free_disk_gb:
            reason = (
                f"free disk {observation.free_disk_gb:.1f} GB is below "
                f"{control.min_free_disk_gb:.1f} GB floor"
            )
            blocked = replace(state, phase="paused", blocker=reason)
            return Decision(ActionKind.PAUSE, reason, blocked)
        if observation.pipeline_pids or observation.ros_pids:
            reason = "process cleanup incomplete before launch"
            blocked = replace(state, phase="paused", blocker=reason)
            return Decision(ActionKind.PAUSE, reason, blocked)
        return Decision(ActionKind.LAUNCH_RUN, "ready to launch", state)

    return Decision(ActionKind.NONE, "healthy", state)
