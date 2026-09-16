"""Read-only host inspection and narrowly scoped process operations."""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import time
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol, Sequence

from .policy import Observation, RunSpec


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class Runner(Protocol):
    def run(self, argv: Sequence[str], *, timeout: int = 30) -> CommandResult: ...


class SubprocessRunner:
    def run(self, argv: Sequence[str], *, timeout: int = 30) -> CommandResult:
        try:
            completed = subprocess.run(
                list(argv),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return CommandResult(
                completed.returncode,
                completed.stdout,
                completed.stderr,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else exc.stdout or ""
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr or ""
            return CommandResult(124, stdout, stderr or "command timed out")


@dataclass(frozen=True)
class HostPaths:
    workspace: Path = Path("/home/sher/active-semantic-perception-workspace")
    container_workspace: Path = Path("/workspace")
    container: str = "asp-noetic"

    @property
    def runs(self) -> Path:
        return self.workspace / "runs"

    @property
    def supervisor(self) -> Path:
        return self.runs / "matrix_supervisor"


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]
    path_m: float
    final_stage: int | None


class HostRuntime:
    """Boundary around host/Docker inspection.

    `observe` is strictly read-only. Mutating operations are separate methods so
    `--check` and `--dry-run` cannot accidentally affect the experiment.
    """

    DOCKER = "/usr/bin/docker"
    NVIDIA_SMI = "/usr/bin/nvidia-smi"
    PIPELINE_PATTERN = "^python exploration_pipeline.py$"
    READ_LLM_LOG_DIR_SCRIPT = (
        "from pathlib import Path; import sys; "
        "p=Path('/proc')/sys.argv[1]/'environ'; prefix=b'ASP_LLM_LOG_DIR='; "
        "print(next((x[len(prefix):].decode(errors='replace') for x in "
        "p.read_bytes().split(b'\\0') if x.startswith(prefix)), ''))"
    )
    WRITE_JSON_ATOMIC_SCRIPT = (
        "from pathlib import Path; import base64, os, sys; "
        "p=Path(sys.argv[1]); t=p.with_name(f'.{p.name}.{os.getpid()}.tmp'); "
        "t.write_bytes(base64.b64decode(sys.argv[2])); os.replace(t, p)"
    )
    CLEAN_DISPLAY_SCRIPT = (
        "from pathlib import Path; import sys; "
        "[Path(value).unlink(missing_ok=True) for value in sys.argv[1:]]"
    )
    ROS_PROCESS_PATTERN = (
        "roslaunch clio_ros realsense.launch|rosmaster|hydra_ros_node|"
        "clio_ros/app/task_server|segmenter_yoso.py|openset_detection_node|"
        "nvblox_node|Xvfb :"
    )

    def __init__(
        self,
        paths: HostPaths | None = None,
        runner: Runner | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.paths = paths or HostPaths()
        self.runner = runner or SubprocessRunner()
        self.sleeper = sleeper

    def run_path(self, spec: RunSpec) -> Path:
        return self.paths.runs / spec.name

    def _run(self, *argv: str, timeout: int = 30) -> CommandResult:
        return self.runner.run(argv, timeout=timeout)

    @staticmethod
    def _parse_pids(text: str) -> list[int]:
        result = []
        for value in text.split():
            try:
                result.append(int(value))
            except ValueError:
                continue
        return sorted(set(result))

    def _container_status(self) -> tuple[bool, bool, str | None]:
        result = self._run(
            self.DOCKER,
            "inspect",
            "-f",
            "{{.State.Running}}",
            self.paths.container,
        )
        if result.returncode != 0:
            return False, False, result.stderr.strip() or "docker inspect failed"
        value = result.stdout.strip()
        if value not in ("true", "false"):
            return False, False, f"unexpected docker inspect output: {value!r}"
        return value == "true", True, None

    def _container_pids(self, pattern: str) -> list[int]:
        result = self._run(
            self.DOCKER,
            "exec",
            self.paths.container,
            "pgrep",
            "-f",
            pattern,
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr.strip() or "container pgrep failed")
        return self._parse_pids(result.stdout)

    def _pipeline_log_dirs(self, pids: list[int]) -> tuple[list[str], bool]:
        values: list[str] = []
        for pid in pids:
            result = self._run(
                self.DOCKER,
                "exec",
                self.paths.container,
                "python3",
                "-c",
                self.READ_LLM_LOG_DIR_SCRIPT,
                str(pid),
            )
            if result.returncode == 0 and result.stdout.strip():
                values.append(result.stdout.strip())
        return values, len(values) == len(pids)

    @staticmethod
    def _max_path(run_path: Path) -> float:
        paths = []
        for nav in run_path.glob("stages/*/navigation_stats.json"):
            try:
                value = float(json.loads(nav.read_text())["total_path_length_meters"])
                paths.append(value)
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                continue
        return max(paths, default=0.0)

    @staticmethod
    def _calls(run_path: Path) -> int:
        try:
            return int((run_path / "prompts" / "_call_counter").read_text().strip())
        except (OSError, ValueError):
            return 0

    @staticmethod
    def _pipeline_log(run_path: Path) -> str:
        try:
            return (run_path / "logs" / "exploration_pipeline.log").read_text(
                errors="replace"
            )
        except OSError:
            return ""

    @staticmethod
    def _fatal_traceback(log: str) -> bool:
        """A raw Python traceback is fatal unless rospy's own callback
        wrapper logged it: rospy catches exceptions raised inside a
        subscriber/timer callback, logs a "bad callback: <bound method
        ...>" line immediately before the traceback, and keeps the node
        (and this pipeline) running afterward - the same fail-soft
        tolerance class this project already documents for ensemble-
        member LLM drops, just for navigation callbacks. A traceback with
        no such marker on the line right before it is uncaught and
        therefore fatal.
        """
        lines = log.splitlines()
        for index, line in enumerate(lines):
            if "Traceback (most recent call last)" not in line:
                continue
            preceding = lines[index - 1] if index > 0 else ""
            if "bad callback:" not in preceding:
                return True
        return False

    def observe(self, spec: RunSpec, *, now: float) -> Observation:
        run_path = self.run_path(spec)
        host_gpu = self._run(self.NVIDIA_SMI, "-L")
        host_gpu_ok = host_gpu.returncode == 0 and bool(host_gpu.stdout.strip())
        container_running, container_inspection_ok, container_error = (
            self._container_status()
        )
        inspection_errors = [container_error] if container_error else []
        process_inspection_ok = container_inspection_ok

        if container_running:
            container_gpu = self._run(
                self.DOCKER,
                "exec",
                self.paths.container,
                "nvidia-smi",
                "-L",
            )
            container_gpu_ok = (
                container_gpu.returncode == 0 and bool(container_gpu.stdout.strip())
            )
            try:
                pipeline_pids = self._container_pids(self.PIPELINE_PATTERN)
                ros_pids = self._container_pids(self.ROS_PROCESS_PATTERN)
                pipeline_log_dirs, env_ok = self._pipeline_log_dirs(pipeline_pids)
                if not env_ok:
                    process_inspection_ok = False
                    inspection_errors.append("could not read active pipeline log route")
            except RuntimeError as exc:
                pipeline_pids = []
                ros_pids = []
                pipeline_log_dirs = []
                process_inspection_ok = False
                inspection_errors.append(str(exc))
        else:
            container_gpu_ok = False
            pipeline_pids = []
            ros_pids = []
            pipeline_log_dirs = []
            if container_inspection_ok:
                process_inspection_ok = True

        log = self._pipeline_log(run_path)
        usage = shutil.disk_usage(self.paths.workspace)
        free_disk_gb = usage.free / (1024**3)
        expected_log_dir = str(
            self.paths.container_workspace / "runs" / spec.name / "prompts"
        )
        return Observation(
            now=now,
            container_running=container_running,
            host_gpu_ok=host_gpu_ok,
            container_gpu_ok=container_gpu_ok,
            pipeline_pids=pipeline_pids,
            ros_pids=ros_pids,
            path_m=self._max_path(run_path),
            calls=self._calls(run_path),
            free_disk_gb=free_disk_gb,
            hard_cap_exceeded=(
                "ASP_LLM_MAX_CALLS hard cap" in log and "exceeded on call" in log
            ),
            traceback_found=self._fatal_traceback(log),
            pipeline_log_dirs=pipeline_log_dirs,
            pipeline_matches_run=(
                not pipeline_pids
                or pipeline_log_dirs == [expected_log_dir]
            ),
            container_inspection_ok=container_inspection_ok,
            process_inspection_ok=process_inspection_ok,
            inspection_errors=inspection_errors,
        )

    def validate_completed_run(self, spec: RunSpec) -> ValidationResult:
        run_path = self.run_path(spec)
        errors: list[str] = []
        completed: list[tuple[int, float, Path]] = []
        for nav in run_path.glob("stages/*/navigation_stats.json"):
            try:
                stage = int(nav.parent.name)
                path_m = float(json.loads(nav.read_text())["total_path_length_meters"])
                completed.append((stage, path_m, nav.parent))
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                continue

        if not completed:
            return ValidationResult(False, ("no completed stages",), 0.0, None)
        stage_number, path_m, stage_path = max(completed, key=lambda item: item[1])
        if path_m < 120.0:
            errors.append(f"final path is only {path_m:.3f} m")

        for graph_index in (0, 1):
            graph = stage_path / f"habitat_scene_graph_original_graph{graph_index}.yaml"
            if not graph.exists() or graph.stat().st_size == 0:
                errors.append(f"missing or empty graph{graph_index} in stage {stage_number}")

        completions = list(stage_path.glob("habitat_scene_graph_new_graph_*.yaml"))
        if not any(path.stat().st_size > 0 for path in completions):
            errors.append(f"no non-empty completion in stage {stage_number}")

        for relative in (
            "config/pipeline_config.yaml",
            "config/commit.txt",
            "config/run_manifest.txt",
        ):
            path = run_path / relative
            if not path.exists() or path.stat().st_size == 0:
                errors.append(f"missing required artifact {relative}")

        if self._fatal_traceback(self._pipeline_log(run_path)):
            errors.append("uncaptured traceback in pipeline log")

        return ValidationResult(not errors, tuple(errors), path_m, stage_number)

    def restart_container(self) -> bool:
        """Perform a full stop/start and require working container GPU access."""
        # `docker stop` may return nonzero when the container is already stopped;
        # `docker start` is the authoritative recovery result.
        self._run(self.DOCKER, "stop", "-t", "30", self.paths.container, timeout=45)
        started = self._run(
            self.DOCKER,
            "start",
            self.paths.container,
            timeout=45,
        )
        if started.returncode != 0:
            return False
        self.sleeper(5)
        gpu = self._run(
            self.DOCKER,
            "exec",
            self.paths.container,
            "nvidia-smi",
            "-L",
            timeout=30,
        )
        return gpu.returncode == 0 and bool(gpu.stdout.strip())

    def graceful_stop(self, spec: RunSpec, *, display: int, timeout: int) -> bool:
        """Use the author's keyboard shutdown path before targeted escalation."""
        del spec  # The active process is unique; spec is retained for API clarity.
        escape = (
            self.DOCKER,
            "exec",
            self.paths.container,
            "env",
            f"DISPLAY=:{display}",
            "xdotool",
            "key",
            "Escape",
        )
        self._run(*escape)
        self.sleeper(0.25)
        self._run(*escape)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            pids = self._container_pids(self.PIPELINE_PATTERN)
            if not pids:
                return True
            self.sleeper(2)

        pids = self._container_pids(self.PIPELINE_PATTERN)
        if pids:
            self._run(
                self.DOCKER,
                "exec",
                self.paths.container,
                "kill",
                "-TERM",
                *(str(pid) for pid in pids),
            )
            self.sleeper(10)
        pids = self._container_pids(self.PIPELINE_PATTERN)
        if pids:
            self._run(
                self.DOCKER,
                "exec",
                self.paths.container,
                "kill",
                "-KILL",
                *(str(pid) for pid in pids),
            )
            self.sleeper(2)
        return not self._container_pids(self.PIPELINE_PATTERN)

    def archive_failed_run(
        self,
        spec: RunSpec,
        *,
        attempt: int,
        reason: str,
        now: float,
    ) -> Path:
        source = self.run_path(spec)
        slug = re.sub(r"[^a-z0-9]+", "_", reason.lower()).strip("_")[:64]
        timestamp = datetime.fromtimestamp(now, timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = source.with_name(
            f"{source.name}_FAILED_ATTEMPT{attempt}_{slug}_{timestamp}"
        )
        if not source.exists():
            existing = sorted(
                source.parent.glob(f"{source.name}_FAILED_ATTEMPT{attempt}_*")
            )
            if existing:
                return existing[-1]
            destination.mkdir(parents=True)
            (destination / "matrix_supervisor_failure.json").write_text(
                json.dumps(
                    {
                        "scene": spec.scene,
                        "seed": spec.seed,
                        "attempt": attempt,
                        "reason": reason,
                        "recorded_at": now,
                        "source_directory_missing": True,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            return destination
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite archived run: {destination}")
        source.rename(destination)
        return destination

    def cleanup_display(self, display: int) -> bool:
        """Remove stale X lock/socket only when no server owns the display."""
        try:
            active = self._container_pids(f"^Xvfb :{display}( |$)")
        except RuntimeError:
            return False
        if active:
            return False
        result = self._run(
            self.DOCKER,
            "exec",
            self.paths.container,
            "python3",
            "-c",
            self.CLEAN_DISPLAY_SCRIPT,
            f"/tmp/.X{display}-lock",
            f"/tmp/.X11-unix/X{display}",
        )
        return result.returncode == 0

    def launch_run(
        self,
        spec: RunSpec,
        *,
        display: int,
        reasoning_effort: str,
        max_tokens: int,
        max_calls: int,
    ) -> bool:
        """Launch one run asynchronously after all preconditions are checked."""
        if self.run_path(spec).exists():
            return False
        if not self.cleanup_display(display):
            return False
        launcher_dir = self.paths.supervisor / "launchers"
        launcher_dir.mkdir(parents=True, exist_ok=True)
        container_log = (
            self.paths.container_workspace
            / "runs"
            / "matrix_supervisor"
            / "launchers"
            / f"{spec.name}.log"
        )
        args = [
            "/workspace/run_llm_pipeline_scene.sh",
            spec.scene_path,
            str(spec.scene_number),
            spec.name,
            str(display),
            reasoning_effort,
            str(max_tokens),
            str(max_calls),
            str(spec.seed),
        ]
        command = "exec " + " ".join(shlex.quote(value) for value in args)
        command += f" >> {shlex.quote(str(container_log))} 2>&1"
        result = self._run(
            self.DOCKER,
            "exec",
            "-d",
            self.paths.container,
            "bash",
            "-lc",
            command,
            timeout=30,
        )
        return result.returncode == 0

    def write_completion_marker(
        self,
        spec: RunSpec,
        result: ValidationResult,
        *,
        calls: int,
        now: float,
    ) -> None:
        payload = {
            "scene": spec.scene,
            "seed": spec.seed,
            "path_m": result.path_m,
            "final_stage": result.final_stage,
            "calls": calls,
            "completed_at": now,
            "validation_errors": list(result.errors),
        }
        encoded = base64.b64encode(
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
        ).decode()
        marker = (
            self.paths.container_workspace
            / "runs"
            / spec.name
            / "matrix_supervisor_complete.json"
        )
        # Run directories are created by Docker as root:root. Write through
        # the container boundary rather than changing ownership of evidence.
        result_command = self._run(
            self.DOCKER,
            "exec",
            self.paths.container,
            "python3",
            "-c",
            self.WRITE_JSON_ATOMIC_SCRIPT,
            str(marker),
            encoded,
        )
        if result_command.returncode != 0:
            raise RuntimeError(
                "could not write completion marker through container: "
                + (result_command.stderr.strip() or "unknown docker exec error")
            )
