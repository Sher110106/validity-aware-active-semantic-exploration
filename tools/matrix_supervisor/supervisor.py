#!/usr/bin/env python3
"""Persistent state machine for the ASP 12-run matrix."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from matrix_supervisor.host import HostPaths, HostRuntime, ValidationResult
    from matrix_supervisor.policy import (
        ActionKind,
        Control,
        Decision,
        State,
        bootstrap_state,
        build_seed_major_plan,
        choose_action,
    )
else:
    from .host import HostPaths, HostRuntime, ValidationResult
    from .policy import (
        ActionKind,
        Control,
        Decision,
        State,
        bootstrap_state,
        build_seed_major_plan,
        choose_action,
    )


@dataclass(frozen=True)
class SupervisorPaths:
    workspace: Path = Path("/home/sher/active-semantic-perception-workspace")
    runtime_dir: Path = Path(
        "/home/sher/active-semantic-perception-workspace/runs/matrix_supervisor"
    )
    control_file: Path = Path(
        "/home/sher/active-semantic-perception-workspace/"
        "tools/matrix_supervisor/CONTROL.json"
    )

    @property
    def state_file(self) -> Path:
        return self.runtime_dir / "state.json"

    @property
    def status_file(self) -> Path:
        return self.runtime_dir / "status.json"

    @property
    def event_file(self) -> Path:
        return self.runtime_dir / "events.jsonl"

    @property
    def lock_file(self) -> Path:
        return self.runtime_dir / "supervisor.lock"


@dataclass
class RuntimeControl(Control):
    display: int = 99
    reasoning_effort: str = "low"
    max_tokens: int = 16000
    startup_grace_seconds: int = 180
    graceful_stop_seconds: int = 180
    resume_generation: int = 0


@dataclass
class MatrixState:
    queue_index: int
    run_state: State
    completed: list[str]
    updated_at: float
    last_action: str = "none"
    last_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "queue_index": self.queue_index,
            "run_state": asdict(self.run_state),
            "completed": self.completed,
            "updated_at": self.updated_at,
            "last_action": self.last_action,
            "last_reason": self.last_reason,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "MatrixState":
        return cls(
            queue_index=int(value["queue_index"]),
            run_state=State(**value["run_state"]),
            completed=list(value.get("completed", [])),
            updated_at=float(value.get("updated_at", 0.0)),
            last_action=str(value.get("last_action", "none")),
            last_reason=str(value.get("last_reason", "")),
        )


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def load_control(path: Path) -> RuntimeControl:
    raw = json.loads(path.read_text())
    allowed = set(RuntimeControl.__dataclass_fields__)
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown CONTROL.json keys: {', '.join(unknown)}")
    control = RuntimeControl(**raw)
    if not isinstance(control.paused, bool):
        raise ValueError("paused must be a boolean")
    if not isinstance(control.resume_generation, int) or control.resume_generation < 0:
        raise ValueError("resume_generation must be a non-negative integer")
    if not 10 <= control.poll_seconds <= 60:
        raise ValueError("poll_seconds must be between 10 and 60")
    if control.max_attempts != 2:
        raise ValueError("approved max_attempts is exactly 2")
    if control.min_free_disk_gb < 25:
        raise ValueError("min_free_disk_gb cannot be lower than approved 25 GB")
    if not 60 <= control.ambiguous_stall_seconds <= 1800:
        raise ValueError("ambiguous_stall_seconds must be between 60 and 1800")
    if control.target_path_m != 120:
        raise ValueError("approved target_path_m is exactly 120")
    if control.future_max_calls != 3000:
        raise ValueError("approved future_max_calls is exactly 3000")
    if control.reasoning_effort != "low":
        raise ValueError("approved reasoning_effort is low")
    if control.max_tokens != 16000:
        raise ValueError("approved max_tokens is exactly 16000")
    if control.display != 99:
        raise ValueError("approved display is 99")
    if control.startup_grace_seconds != 180:
        raise ValueError("approved startup_grace_seconds is exactly 180")
    if control.graceful_stop_seconds != 180:
        raise ValueError("approved graceful_stop_seconds is exactly 180")
    return control


class MatrixSupervisor:
    def __init__(
        self,
        *,
        paths: SupervisorPaths | None = None,
        runtime=None,
        clock: Callable[[], float] = time.time,
    ):
        self.paths = paths or SupervisorPaths()
        self.runtime = runtime or HostRuntime(HostPaths(workspace=self.paths.workspace))
        self.clock = clock
        self.plan = build_seed_major_plan()

    def _load_state(self) -> MatrixState | None:
        try:
            return MatrixState.from_dict(json.loads(self.paths.state_file.read_text()))
        except FileNotFoundError:
            return None

    def _failed_attempts(self, run_name: str) -> int:
        runs = self.paths.workspace / "runs"
        return len(list(runs.glob(f"{run_name}_FAILED_ATTEMPT*")))

    def _first_unfinished_index(self) -> int:
        for index, spec in enumerate(self.plan):
            marker = self.runtime.run_path(spec) / "matrix_supervisor_complete.json"
            if not marker.exists():
                return index
        return len(self.plan)

    def _bootstrap(self, now: float):
        index = self._first_unfinished_index()
        completed = [spec.name for spec in self.plan[:index]]
        if index >= len(self.plan):
            return MatrixState(index, State.ready(now=now, attempt=1), completed, now), None
        spec = self.plan[index]
        observation = self.runtime.observe(spec, now=now)
        run_path = self.runtime.run_path(spec)
        failed = self._failed_attempts(spec.name)
        existing_attempt = run_path.exists()
        expected_running = bool(observation.pipeline_pids) or existing_attempt
        run_state = bootstrap_state(
            now=now,
            active_index=index,
            active_pipeline=expected_running,
            failed_attempts=failed,
            observed_path_m=observation.path_m,
            observed_calls=observation.calls,
        )
        return MatrixState(index, run_state, completed, now), observation

    def _event(self, *, now: float, event: str, details: dict) -> None:
        self.paths.runtime_dir.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": now, "event": event, **details}
        with self.paths.event_file.open("a") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _save(self, state: MatrixState, status: dict) -> None:
        _atomic_json(self.paths.state_file, state.to_dict())
        _atomic_json(self.paths.status_file, status)

    def _status(
        self,
        *,
        state: MatrixState,
        observation,
        decision: Decision,
        control: RuntimeControl,
        now: float,
    ) -> dict:
        active = self.plan[state.queue_index] if state.queue_index < len(self.plan) else None
        return {
            "timestamp": now,
            "next_check_at": now + control.poll_seconds,
            "matrix_complete": active is None,
            "queue_index": state.queue_index,
            "queue_total": len(self.plan),
            "active_run": active.name if active else None,
            "attempt": state.run_state.attempt,
            "phase": state.run_state.phase,
            "path_m": observation.path_m if observation else None,
            "calls": observation.calls if observation else None,
            "pipeline_pids": observation.pipeline_pids if observation else [],
            "pipeline_log_dirs": (
                observation.pipeline_log_dirs if observation else []
            ),
            "pipeline_matches_run": (
                observation.pipeline_matches_run if observation else None
            ),
            "ros_pids": observation.ros_pids if observation else [],
            "host_gpu_ok": observation.host_gpu_ok if observation else None,
            "container_running": observation.container_running if observation else None,
            "container_inspection_ok": (
                observation.container_inspection_ok if observation else None
            ),
            "container_gpu_ok": observation.container_gpu_ok if observation else None,
            "process_inspection_ok": (
                observation.process_inspection_ok if observation else None
            ),
            "inspection_errors": observation.inspection_errors if observation else [],
            "free_disk_gb": round(observation.free_disk_gb, 3) if observation else None,
            "proposed_action": decision.kind.value,
            "reason": decision.reason,
            "blocker": decision.state.blocker,
            "thresholds": {
                "target_path_m": control.target_path_m,
                "future_max_calls": control.future_max_calls,
                "min_free_disk_gb": control.min_free_disk_gb,
                "ambiguous_stall_seconds": control.ambiguous_stall_seconds,
                "max_attempts": control.max_attempts,
                "resume_generation": control.resume_generation,
            },
        }

    def _apply_explicit_resume(
        self,
        state: MatrixState,
        observation,
        control: RuntimeControl,
        now: float,
    ) -> MatrixState:
        run_state = state.run_state
        if run_state.phase != "paused":
            return state
        if control.resume_generation <= run_state.resume_generation_seen:
            return state

        run_exists = self.runtime.run_path(self.plan[state.queue_index]).exists()
        if len(observation.pipeline_pids) == 1 and observation.pipeline_matches_run:
            phase = "running"
        elif run_exists:
            # Let the normal policy validate completion or classify a failed
            # attempt on this same cycle.
            phase = "running"
        else:
            phase = "ready"
        return replace(
            state,
            run_state=replace(
                run_state,
                phase=phase,
                blocker=None,
                last_progress_at=now,
                resume_generation_seen=control.resume_generation,
            ),
            updated_at=now,
        )

    def _advance(self, state: MatrixState, now: float, completed_name: str) -> MatrixState:
        next_index = state.queue_index + 1
        completed = list(state.completed)
        if completed_name not in completed:
            completed.append(completed_name)
        return MatrixState(
            queue_index=next_index,
            run_state=replace(
                State.ready(now=now, attempt=1),
                resume_generation_seen=state.run_state.resume_generation_seen,
            ),
            completed=completed,
            updated_at=now,
            last_action="advance_queue",
            last_reason=f"completed {completed_name}",
        )

    @staticmethod
    def _infrastructure_failure(
        state: MatrixState,
        message: str,
    ) -> MatrixState:
        failures = state.run_state.infrastructure_recovery_failures + 1
        phase = "paused" if failures >= 5 else state.run_state.phase
        suffix = "retry limit reached" if phase == "paused" else "will retry"
        return replace(
            state,
            run_state=replace(
                state.run_state,
                phase=phase,
                infrastructure_recovery_failures=failures,
                blocker=f"{message}; {suffix}",
            ),
        )

    def _complete_current(
        self,
        state: MatrixState,
        observation,
        spec,
        control: RuntimeControl,
        now: float,
        *,
        stop_first: bool,
    ) -> MatrixState:
        if stop_first:
            stopped = self.runtime.graceful_stop(
                spec,
                display=control.display,
                timeout=control.graceful_stop_seconds,
            )
            if not stopped:
                return replace(
                    state,
                    run_state=replace(
                        state.run_state,
                        phase="paused",
                        blocker="pipeline did not stop cleanly at path budget",
                    ),
                    updated_at=now,
                )
        result: ValidationResult = self.runtime.validate_completed_run(spec)
        if not result.ok:
            return replace(
                state,
                run_state=replace(
                    state.run_state,
                    phase="paused",
                    blocker="completion validation failed: " + "; ".join(result.errors),
                ),
                updated_at=now,
            )
        self.runtime.write_completion_marker(
            spec,
            result,
            calls=observation.calls,
            now=now,
        )
        if not self.runtime.restart_container():
            return self._infrastructure_failure(
                replace(state, updated_at=now),
                "completed run but container cleanup/restart failed",
            )
        return self._advance(state, now, spec.name)

    def _apply(
        self,
        state: MatrixState,
        observation,
        decision: Decision,
        control: RuntimeControl,
        now: float,
    ) -> MatrixState:
        spec = self.plan[state.queue_index]
        action_run_state = decision.state
        if (
            decision.kind == ActionKind.LAUNCH_RUN
            and state.run_state.phase == "launching"
        ):
            action_run_state = state.run_state
        state = replace(
            state,
            run_state=action_run_state,
            updated_at=now,
            last_action=decision.kind.value,
            last_reason=decision.reason,
        )
        if decision.kind in (ActionKind.NONE, ActionKind.PAUSE):
            return state
        if decision.kind in (ActionKind.START_CONTAINER, ActionKind.HEAL_CONTAINER_GPU):
            ok = self.runtime.restart_container()
            if not ok:
                return self._infrastructure_failure(
                    state,
                    "container restart or GPU verification failed",
                )
            return replace(
                state,
                run_state=replace(
                    state.run_state,
                    container_gpu_failures=0,
                    infrastructure_recovery_failures=0,
                    blocker=None,
                ),
            )
        if decision.kind == ActionKind.STOP_AT_BUDGET:
            return self._complete_current(
                state, observation, spec, control, now, stop_first=True
            )
        if decision.kind == ActionKind.VALIDATE_COMPLETE:
            return self._complete_current(
                state, observation, spec, control, now, stop_first=False
            )
        if decision.kind == ActionKind.RETRY_RUN:
            if observation.pipeline_pids:
                self.runtime.graceful_stop(
                    spec,
                    display=control.display,
                    timeout=control.graceful_stop_seconds,
                )
            if not self.runtime.restart_container():
                return self._infrastructure_failure(
                    state,
                    "could not clean container before retry",
                )
            self.runtime.archive_failed_run(
                spec,
                attempt=state.run_state.attempt,
                reason=decision.reason,
                now=now,
            )
            return replace(
                state,
                run_state=replace(
                    State.ready(
                        now=now,
                        attempt=state.run_state.attempt + 1,
                    ),
                    resume_generation_seen=state.run_state.resume_generation_seen,
                ),
            )
        if decision.kind == ActionKind.LAUNCH_RUN:
            launched = self.runtime.launch_run(
                spec,
                display=control.display,
                reasoning_effort=control.reasoning_effort,
                max_tokens=control.max_tokens,
                max_calls=control.future_max_calls,
            )
            if not launched:
                return replace(
                    state,
                    run_state=replace(
                        state.run_state,
                        phase="paused",
                        blocker="launcher command failed",
                    ),
                )
            return replace(
                state,
                run_state=replace(
                    state.run_state,
                    phase="launching",
                    last_progress_at=now,
                    blocker=None,
                ),
            )
        return state

    def reconcile(self, *, dry_run: bool = False) -> dict:
        now = self.clock()
        control = load_control(self.paths.control_file)
        state = self._load_state()
        bootstrapped = state is None
        observation = None
        if state is None:
            state, observation = self._bootstrap(now)
        if state.queue_index >= len(self.plan):
            report = {
                "timestamp": now,
                "matrix_complete": True,
                "proposed_action": "none",
                "reason": "all runs complete",
            }
            if not dry_run:
                self._save(state, report)
            return report

        spec = self.plan[state.queue_index]
        if observation is None:
            observation = self.runtime.observe(spec, now=now)

        # A resume generation has meaning only while blocked. Consume any
        # generation written while healthy so it cannot silently auto-resume a
        # future, unrelated safety pause.
        if (
            state.run_state.phase != "paused"
            and control.resume_generation > state.run_state.resume_generation_seen
        ):
            state = replace(
                state,
                run_state=replace(
                    state.run_state,
                    resume_generation_seen=control.resume_generation,
                ),
            )

        state = self._apply_explicit_resume(state, observation, control, now)

        # If the service crashed after starting Docker exec but before saving
        # the launching state, safely re-adopt only a pipeline whose logger is
        # routed to the expected run directory.
        if (
            state.run_state.phase == "ready"
            and len(observation.pipeline_pids) == 1
            and observation.pipeline_matches_run
            and self.runtime.run_path(spec).exists()
        ):
            state = replace(
                state,
                run_state=replace(
                    state.run_state,
                    phase="running",
                    last_progress_at=now,
                    blocker=None,
                ),
            )

        # A launched run gets a grace period before absence becomes a failure.
        if state.run_state.phase == "launching":
            if observation.pipeline_pids:
                state = replace(
                    state,
                    run_state=replace(
                        state.run_state,
                        phase="running",
                        last_progress_at=now,
                        launch_recovery_attempts=0,
                    ),
                )
            elif observation.traceback_found or observation.hard_cap_exceeded:
                # A captured startup traceback is a clear failure, not an
                # ambiguous slow launch. Skip the grace delay so cleanup and
                # the bounded retry can begin on this cycle.
                state = replace(
                    state,
                    run_state=replace(state.run_state, phase="running"),
                )
            elif now - state.run_state.last_progress_at < control.startup_grace_seconds:
                decision = Decision(ActionKind.NONE, "launcher startup grace", state.run_state)
                report = self._status(
                    state=state,
                    observation=observation,
                    decision=decision,
                    control=control,
                    now=now,
                )
                if not dry_run:
                    state = replace(state, updated_at=now)
                    self._save(state, report)
                return report
            else:
                run_exists = self.runtime.run_path(spec).exists()
                if not run_exists and not observation.ros_pids:
                    launch_recoveries = state.run_state.launch_recovery_attempts
                    if launch_recoveries >= 1:
                        reason = "detached launcher produced no run after one recovery"
                        decision = Decision(
                            ActionKind.PAUSE,
                            reason,
                            replace(
                                state.run_state,
                                phase="paused",
                                blocker=reason,
                            ),
                        )
                        paused_state = replace(
                            state,
                            run_state=decision.state,
                            updated_at=now,
                            last_action=decision.kind.value,
                            last_reason=reason,
                        )
                        report = self._status(
                            state=paused_state,
                            observation=observation,
                            decision=decision,
                            control=control,
                            now=now,
                        )
                        if not dry_run:
                            state = paused_state
                            self._save(paused_state, report)
                            self._event(
                                now=now,
                                event="pause",
                                details={
                                    "run": spec.name,
                                    "attempt": state.run_state.attempt,
                                    "reason": reason,
                                    "phase": "paused",
                                },
                            )
                        return report
                    state = replace(
                        state,
                        run_state=replace(
                            state.run_state,
                            phase="ready",
                            launch_recovery_attempts=launch_recoveries + 1,
                            blocker="recovering interrupted detached launch",
                        ),
                    )
                else:
                    state = replace(
                        state,
                        run_state=replace(state.run_state, phase="running"),
                    )

        decision = choose_action(state.run_state, observation, control)
        report = self._status(
            state=state,
            observation=observation,
            decision=decision,
            control=control,
            now=now,
        )
        if dry_run:
            return report

        if decision.kind == ActionKind.LAUNCH_RUN:
            # Persist intent before the detached Docker command. If this host
            # process dies in the tiny launch window, the next service process
            # waits in `launching` instead of issuing a duplicate launch.
            prepared_run_state = replace(
                decision.state,
                phase="launching",
                last_progress_at=now,
                blocker=None,
            )
            state = replace(
                state,
                run_state=prepared_run_state,
                updated_at=now,
                last_action="prepare_launch",
                last_reason=f"prepared launch for {spec.name}",
            )
            prepared_decision = Decision(
                ActionKind.LAUNCH_RUN,
                "launch intent persisted",
                prepared_run_state,
            )
            self._save(
                state,
                self._status(
                    state=state,
                    observation=observation,
                    decision=prepared_decision,
                    control=control,
                    now=now,
                ),
            )
            self._event(
                now=now,
                event="launch_prepared",
                details={"run": spec.name, "attempt": state.run_state.attempt},
            )

        previous_phase = state.run_state.phase
        action_attempt = state.run_state.attempt
        state = self._apply(state, observation, decision, control, now)
        final_decision = Decision(decision.kind, decision.reason, state.run_state)
        status_observation = observation
        if state.queue_index != int(report["queue_index"]):
            status_observation = None
        final_status = self._status(
            state=state,
            observation=status_observation,
            decision=final_decision,
            control=control,
            now=now,
        )
        self._save(state, final_status)
        if bootstrapped:
            self._event(
                now=now,
                event="adopt_run" if observation.pipeline_pids else "bootstrap_queue",
                details={
                    "run": spec.name,
                    "attempt": action_attempt,
                    "path_m": observation.path_m,
                    "calls": observation.calls,
                    "phase": state.run_state.phase,
                },
            )
        if decision.kind != ActionKind.NONE or previous_phase != state.run_state.phase:
            self._event(
                now=now,
                event=decision.kind.value,
                details={
                    "run": spec.name,
                    "attempt": action_attempt,
                    "reason": decision.reason,
                    "phase": state.run_state.phase,
                },
            )
        return final_status

    def check(self) -> tuple[dict, int]:
        report = self.reconcile(dry_run=True)
        unsafe = (
            report.get("proposed_action") == ActionKind.PAUSE.value
            or bool(report.get("blocker"))
            or report.get("container_inspection_ok") is False
            or report.get("process_inspection_ok") is False
            or report.get("pipeline_matches_run") is False
        )
        return report, 1 if unsafe else 0

    def daemon(self) -> None:
        control = load_control(self.paths.control_file)
        while True:
            try:
                self.reconcile(dry_run=False)
            except Exception as exc:  # service must survive a bad cycle
                now = self.clock()
                self._event(
                    now=now,
                    event="cycle_exception",
                    details={"error": f"{type(exc).__name__}: {exc}"},
                )
            time.sleep(control.poll_seconds)
            control = load_control(self.paths.control_file)


def _print_report(report: dict) -> None:
    print(json.dumps(report, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="read-only health check")
    mode.add_argument("--once", action="store_true", help="run one reconciliation")
    mode.add_argument("--daemon", action="store_true", help="run continuously")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the proposed action without writing or executing it",
    )
    args = parser.parse_args(argv)
    if args.dry_run and not args.once:
        parser.error("--dry-run is only valid with --once")

    supervisor = MatrixSupervisor()
    if args.check:
        report, code = supervisor.check()
        _print_report(report)
        return code
    if args.once and args.dry_run:
        _print_report(supervisor.reconcile(dry_run=True))
        return 0

    supervisor.paths.runtime_dir.mkdir(parents=True, exist_ok=True)
    with supervisor.paths.lock_file.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another matrix supervisor holds the lock", file=sys.stderr)
            return 2
        if args.once:
            _print_report(supervisor.reconcile(dry_run=False))
            return 0
        supervisor.daemon()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
