import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from matrix_supervisor.host import ValidationResult  # noqa: E402
from matrix_supervisor.policy import Observation, build_seed_major_plan  # noqa: E402
from matrix_supervisor.supervisor import (  # noqa: E402
    MatrixSupervisor,
    SupervisorPaths,
    load_control,
)


class FakeRuntime:
    def __init__(self, workspace: Path, observation: Observation):
        self.workspace = workspace
        self.observation = observation
        self.calls = []
        self.validation = ValidationResult(True, (), observation.path_m, 10)

    def run_path(self, spec):
        return self.workspace / "runs" / spec.name

    def observe(self, spec, *, now):
        self.calls.append(("observe", spec.name))
        self.observation.now = now
        return self.observation

    def validate_completed_run(self, spec):
        self.calls.append(("validate", spec.name))
        return self.validation

    def graceful_stop(self, spec, *, display, timeout):
        self.calls.append(("graceful_stop", spec.name, display, timeout))
        self.observation.pipeline_pids = []
        return True

    def restart_container(self):
        self.calls.append(("restart_container",))
        self.observation.container_running = True
        self.observation.container_gpu_ok = True
        self.observation.pipeline_pids = []
        self.observation.ros_pids = []
        return True

    def archive_failed_run(self, spec, *, attempt, reason, now):
        self.calls.append(("archive", spec.name, attempt, reason))
        return self.run_path(spec).with_name(self.run_path(spec).name + "_archived")

    def launch_run(self, spec, *, display, reasoning_effort, max_tokens, max_calls):
        self.calls.append(
            (
                "launch",
                spec.name,
                display,
                reasoning_effort,
                max_tokens,
                max_calls,
            )
        )
        return True

    def write_completion_marker(self, spec, result, *, calls, now):
        self.calls.append(("marker", spec.name, result.path_m, calls))


class MatrixSupervisorTests(unittest.TestCase):
    def _paths(self, root: Path) -> SupervisorPaths:
        return SupervisorPaths(
            workspace=root,
            runtime_dir=root / "runs" / "matrix_supervisor",
            control_file=root / "tools" / "matrix_supervisor" / "CONTROL.json",
        )

    def _write_control(self, paths: SupervisorPaths):
        paths.control_file.parent.mkdir(parents=True)
        paths.control_file.write_text(
            json.dumps(
                {
                    "paused": False,
                    "poll_seconds": 60,
                    "min_free_disk_gb": 25,
                    "ambiguous_stall_seconds": 1800,
                    "max_attempts": 2,
                    "future_max_calls": 3000,
                    "target_path_m": 120,
                    "display": 99,
                    "reasoning_effort": "low",
                    "max_tokens": 16000,
                    "startup_grace_seconds": 180,
                    "graceful_stop_seconds": 180,
                    "resume_generation": 0,
                }
            )
        )

    def test_dry_run_adopts_current_run_without_writing_or_acting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._paths(root)
            self._write_control(paths)
            run = root / "runs" / build_seed_major_plan()[0].name
            run.mkdir(parents=True)
            (root / "runs" / (run.name + "_FAILED_ATTEMPT1_hostreboot")).mkdir()
            runtime = FakeRuntime(
                root,
                Observation.healthy(now=1000.0, path_m=35.1, calls=621),
            )
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1000.0)

            report = supervisor.reconcile(dry_run=True)

            self.assertEqual("none", report["proposed_action"])
            self.assertEqual(2, report["attempt"])
            self.assertFalse(paths.runtime_dir.exists())
            self.assertEqual([("observe", run.name)], runtime.calls)

    def test_first_live_cycle_persists_adoption_as_attempt_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._paths(root)
            self._write_control(paths)
            run = root / "runs" / build_seed_major_plan()[0].name
            run.mkdir(parents=True)
            (root / "runs" / (run.name + "_FAILED_ATTEMPT1_hostreboot")).mkdir()
            runtime = FakeRuntime(
                root,
                Observation.healthy(now=1000.0, path_m=35.1, calls=621),
            )
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1000.0)

            supervisor.reconcile(dry_run=False)

            state = json.loads(paths.state_file.read_text())
            status = json.loads(paths.status_file.read_text())
            self.assertEqual(2, state["run_state"]["attempt"])
            self.assertEqual("running", state["run_state"]["phase"])
            self.assertEqual(run.name, status["active_run"])
            self.assertEqual(35.1, status["path_m"])
            self.assertNotIn("launch", [call[0] for call in runtime.calls])
            events = [json.loads(line) for line in paths.event_file.read_text().splitlines()]
            self.assertEqual("adopt_run", events[0]["event"])
            self.assertEqual(run.name, events[0]["run"])
            self.assertEqual(2, events[0]["attempt"])

    def test_budget_completion_advances_queue_only_after_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._paths(root)
            self._write_control(paths)
            first = build_seed_major_plan()[0]
            (root / "runs" / first.name).mkdir(parents=True)
            (root / "runs" / (first.name + "_FAILED_ATTEMPT1_hostreboot")).mkdir()
            runtime = FakeRuntime(
                root,
                Observation.healthy(now=1000.0, path_m=120.5, calls=2100),
            )
            runtime.validation = ValidationResult(True, (), 120.5, 40)
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1000.0)

            report = supervisor.reconcile(dry_run=False)

            state = json.loads(paths.state_file.read_text())
            status = json.loads(paths.status_file.read_text())
            self.assertEqual("stop_at_budget", report["proposed_action"])
            self.assertEqual(1, state["queue_index"])
            self.assertEqual("ready", state["run_state"]["phase"])
            self.assertEqual(build_seed_major_plan()[1].name, status["active_run"])
            self.assertIsNone(status["path_m"])
            self.assertIsNone(status["calls"])
            self.assertIn(("marker", first.name, 120.5, 2100), runtime.calls)
            self.assertIn(("restart_container",), runtime.calls)
            events = [json.loads(line) for line in paths.event_file.read_text().splitlines()]
            completion = next(event for event in events if event["event"] == "stop_at_budget")
            self.assertEqual(2, completion["attempt"])

    def test_clear_first_attempt_failure_archives_then_retries_next_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._paths(root)
            self._write_control(paths)
            first = build_seed_major_plan()[0]
            (root / "runs" / first.name).mkdir(parents=True)
            runtime = FakeRuntime(
                root,
                Observation.healthy(now=1000.0, path_m=50.0, calls=900),
            )
            runtime.observation.pipeline_pids = []
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1000.0)

            supervisor.reconcile(dry_run=False)

            state = json.loads(paths.state_file.read_text())
            self.assertEqual("ready", state["run_state"]["phase"])
            self.assertEqual(2, state["run_state"]["attempt"])
            self.assertIn("archive", [call[0] for call in runtime.calls])

            runtime.observation = Observation.idle(now=1060.0, free_disk_gb=100)
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1060.0)
            supervisor.reconcile(dry_run=False)
            self.assertIn("launch", [call[0] for call in runtime.calls])

    def test_safety_pause_requires_explicit_resume_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._paths(root)
            self._write_control(paths)
            first = build_seed_major_plan()[0]
            (root / "runs" / first.name).mkdir(parents=True)
            runtime = FakeRuntime(
                root,
                Observation.healthy(now=1000.0, path_m=20.0, calls=400),
            )
            runtime.observation.host_gpu_ok = False
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1000.0)
            supervisor.reconcile(dry_run=False)
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1060.0)
            supervisor.reconcile(dry_run=False)
            self.assertEqual(
                "paused",
                json.loads(paths.state_file.read_text())["run_state"]["phase"],
            )

            runtime.observation.host_gpu_ok = True
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1120.0)
            supervisor.reconcile(dry_run=False)
            self.assertEqual(
                "paused",
                json.loads(paths.state_file.read_text())["run_state"]["phase"],
            )

            control = json.loads(paths.control_file.read_text())
            control["resume_generation"] = 1
            paths.control_file.write_text(json.dumps(control))
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1180.0)
            supervisor.reconcile(dry_run=False)
            state = json.loads(paths.state_file.read_text())["run_state"]
            self.assertEqual("running", state["phase"])
            self.assertEqual(1, state["resume_generation_seen"])

    def test_failed_container_repair_is_retried_instead_of_immediately_pausing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._paths(root)
            self._write_control(paths)
            first = build_seed_major_plan()[0]
            (root / "runs" / first.name).mkdir(parents=True)
            observation = Observation.healthy(now=1000.0, path_m=20.0, calls=400)
            observation.container_running = False
            observation.container_gpu_ok = False
            runtime = FakeRuntime(root, observation)
            runtime.restart_container = lambda: False
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1000.0)

            supervisor.reconcile(dry_run=False)

            state = json.loads(paths.state_file.read_text())["run_state"]
            self.assertEqual("running", state["phase"])
            self.assertEqual(1, state["infrastructure_recovery_failures"])
            self.assertIn("will retry", state["blocker"])

    def test_ready_state_re_adopts_matching_pipeline_after_crash_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._paths(root)
            self._write_control(paths)
            first = build_seed_major_plan()[0]
            (root / "runs" / first.name).mkdir(parents=True)
            paths.runtime_dir.mkdir(parents=True)
            paths.state_file.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "queue_index": 0,
                        "run_state": {
                            "phase": "ready",
                            "attempt": 1,
                            "last_path_m": 0,
                            "last_calls": 0,
                            "last_progress_at": 900,
                            "container_gpu_failures": 0,
                            "blocker": None
                        },
                        "completed": [],
                        "updated_at": 900,
                    }
                )
            )
            observation = Observation.healthy(now=1000.0, path_m=1.0, calls=20)
            observation.pipeline_matches_run = True
            runtime = FakeRuntime(root, observation)
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1000.0)

            supervisor.reconcile(dry_run=False)

            state = json.loads(paths.state_file.read_text())["run_state"]
            self.assertEqual("running", state["phase"])
            self.assertNotIn("launch", [call[0] for call in runtime.calls])

    def test_launch_is_write_ahead_so_a_supervisor_crash_cannot_duplicate_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._paths(root)
            self._write_control(paths)
            runtime = FakeRuntime(
                root,
                Observation.idle(now=1000.0, free_disk_gb=100),
            )

            def assert_prepared_then_launch(*args, **kwargs):
                del args, kwargs
                state = json.loads(paths.state_file.read_text())["run_state"]
                self.assertEqual("launching", state["phase"])
                return True

            runtime.launch_run = assert_prepared_then_launch
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 1000.0)

            supervisor.reconcile(dry_run=False)

            state = json.loads(paths.state_file.read_text())["run_state"]
            self.assertEqual("launching", state["phase"])

    def test_control_rejects_resource_limits_looser_than_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._paths(root)
            self._write_control(paths)
            baseline = json.loads(paths.control_file.read_text())
            unsafe_changes = {
                "poll_seconds": 61,
                "min_free_disk_gb": 24.9,
                "ambiguous_stall_seconds": 1801,
                "future_max_calls": 3001,
                "target_path_m": 121,
                "max_attempts": 3,
                "reasoning_effort": "high",
                "max_tokens": 32000,
            }
            for key, value in unsafe_changes.items():
                with self.subTest(key=key):
                    candidate = dict(baseline)
                    candidate[key] = value
                    paths.control_file.write_text(json.dumps(candidate))
                    with self.assertRaises(ValueError):
                        load_control(paths.control_file)

    def test_interrupted_detached_launch_gets_only_one_automatic_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._paths(root)
            self._write_control(paths)
            paths.runtime_dir.mkdir(parents=True)
            paths.state_file.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "queue_index": 0,
                        "run_state": {
                            "phase": "launching",
                            "attempt": 1,
                            "last_path_m": 0,
                            "last_calls": 0,
                            "last_progress_at": 0,
                            "container_gpu_failures": 0,
                            "blocker": None,
                        },
                        "completed": [],
                        "updated_at": 0,
                    }
                )
            )
            runtime = FakeRuntime(root, Observation.idle(now=200.0))
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 200.0)

            supervisor.reconcile(dry_run=False)
            state = json.loads(paths.state_file.read_text())["run_state"]
            self.assertEqual("launching", state["phase"])
            self.assertEqual(1, state["launch_recovery_attempts"])
            self.assertIn("launch", [call[0] for call in runtime.calls])

            runtime.calls.clear()
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 400.0)
            supervisor.reconcile(dry_run=False)
            state = json.loads(paths.state_file.read_text())["run_state"]
            status = json.loads(paths.status_file.read_text())
            self.assertEqual("paused", state["phase"])
            self.assertEqual("paused", status["phase"])
            self.assertNotIn("launch", [call[0] for call in runtime.calls])

    def test_clear_startup_traceback_skips_launcher_grace_period(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._paths(root)
            self._write_control(paths)
            first = build_seed_major_plan()[0]
            (root / "runs" / first.name).mkdir(parents=True)
            paths.runtime_dir.mkdir(parents=True)
            paths.state_file.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "queue_index": 0,
                        "run_state": {
                            "phase": "launching",
                            "attempt": 1,
                            "last_path_m": 0,
                            "last_calls": 0,
                            "last_progress_at": 0,
                            "container_gpu_failures": 0,
                            "blocker": None,
                        },
                        "completed": [],
                        "updated_at": 0,
                    }
                )
            )
            observation = Observation.idle(now=60.0)
            observation.traceback_found = True
            runtime = FakeRuntime(root, observation)
            supervisor = MatrixSupervisor(paths=paths, runtime=runtime, clock=lambda: 60.0)

            report = supervisor.reconcile(dry_run=True)

            self.assertEqual("retry_run", report["proposed_action"])
            self.assertIn("traceback", report["reason"])


if __name__ == "__main__":
    unittest.main()
