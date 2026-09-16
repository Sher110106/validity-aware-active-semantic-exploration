import json
import base64
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from matrix_supervisor.host import (  # noqa: E402
    CommandResult,
    HostPaths,
    HostRuntime,
    ValidationResult,
)
from matrix_supervisor.policy import build_seed_major_plan  # noqa: E402


class FakeRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def run(self, argv, *, timeout=30):
        key = tuple(argv)
        self.calls.append((key, timeout))
        return self.responses.get(key, CommandResult(1, "", "not configured"))


class SequenceRunner:
    def __init__(self, responses):
        self.responses = {key: list(values) for key, values in responses.items()}
        self.calls = []

    def run(self, argv, *, timeout=30):
        key = tuple(argv)
        self.calls.append((key, timeout))
        values = self.responses.get(key, [])
        if values:
            return values.pop(0)
        return CommandResult(1, "", "not configured")


class SuccessRunner:
    def __init__(self):
        self.calls = []

    def run(self, argv, *, timeout=30):
        self.calls.append((tuple(argv), timeout))
        return CommandResult(0, "", "")


class HostRuntimeObservationTests(unittest.TestCase):
    def test_observe_reads_live_health_and_artifacts_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run = workspace / "runs" / "scene00069_seed42_matrix120m"
            stage = run / "stages" / "10"
            stage.mkdir(parents=True)
            (stage / "navigation_stats.json").write_text(
                json.dumps(
                    {
                        "total_path_length_meters": 35.1,
                        "total_navigation_time_seconds": 220.0,
                    }
                )
            )
            (run / "prompts").mkdir()
            (run / "prompts" / "_call_counter").write_text("621")
            (run / "logs").mkdir()
            (run / "logs" / "exploration_pipeline.log").write_text("healthy\n")

            responses = {
                ("/usr/bin/nvidia-smi", "-L"): CommandResult(0, "GPU 0\n", ""),
                (
                    "/usr/bin/docker",
                    "inspect",
                    "-f",
                    "{{.State.Running}}",
                    "asp-noetic",
                ): CommandResult(0, "true\n", ""),
                (
                    "/usr/bin/docker",
                    "exec",
                    "asp-noetic",
                    "nvidia-smi",
                    "-L",
                ): CommandResult(0, "GPU 0\n", ""),
                (
                    "/usr/bin/docker",
                    "exec",
                    "asp-noetic",
                    "pgrep",
                    "-f",
                    "^python exploration_pipeline.py$",
                ): CommandResult(0, "933\n", ""),
                (
                    "/usr/bin/docker",
                    "exec",
                    "asp-noetic",
                    "pgrep",
                    "-f",
                    HostRuntime.ROS_PROCESS_PATTERN,
                ): CommandResult(0, "93\n121\n", ""),
                (
                    "/usr/bin/docker",
                    "exec",
                    "asp-noetic",
                    "python3",
                    "-c",
                    HostRuntime.READ_LLM_LOG_DIR_SCRIPT,
                    "933",
                ): CommandResult(
                    0,
                    "/workspace/runs/scene00069_seed42_matrix120m/prompts\n",
                    "",
                ),
            }
            runtime = HostRuntime(
                HostPaths(workspace=workspace),
                runner=FakeRunner(responses),
            )

            observation = runtime.observe(build_seed_major_plan()[0], now=1000.0)

            self.assertTrue(observation.host_gpu_ok)
            self.assertTrue(observation.container_gpu_ok)
            self.assertEqual([933], observation.pipeline_pids)
            self.assertTrue(observation.pipeline_matches_run)
            self.assertEqual(
                ["/workspace/runs/scene00069_seed42_matrix120m/prompts"],
                observation.pipeline_log_dirs,
            )
            self.assertEqual([93, 121], observation.ros_pids)
            self.assertEqual(35.1, observation.path_m)
            self.assertEqual(621, observation.calls)
            self.assertFalse(observation.hard_cap_exceeded)
            self.assertFalse(observation.traceback_found)
            self.assertFalse((workspace / "runs" / "matrix_supervisor").exists())

    def test_observe_recognizes_actual_cap_error_not_install_banner(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run = workspace / "runs" / "scene00069_seed42_matrix120m"
            (run / "logs").mkdir(parents=True)
            (run / "logs" / "exploration_pipeline.log").write_text(
                "installed with hard cap 2500\n"
                "ASP_LLM_MAX_CALLS hard cap (2500) exceeded on call #2501\n"
            )
            runtime = HostRuntime(
                HostPaths(workspace=workspace),
                runner=FakeRunner({}),
            )

            observation = runtime.observe(build_seed_major_plan()[0], now=1000.0)

            self.assertTrue(observation.hard_cap_exceeded)

    def test_observe_does_not_flag_rospy_bad_callback_traceback_as_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run = workspace / "runs" / "scene00573_seed42_matrix120m"
            (run / "logs").mkdir(parents=True)
            (run / "logs" / "exploration_pipeline.log").write_text(
                "[INFO] stage 12 starting\n"
                "[ERROR] bad callback: <bound method "
                "ExplorationPipeline.mid_path_callback of "
                "<exploration_pipeline.ExplorationPipeline object>>\n"
                "Traceback (most recent call last):\n"
                "  File \"exploration_pipeline.py\", line 471, in "
                "_set_navigation_path_from_world_path\n"
                "    waypoint = self.local_path[i]\n"
                "TypeError: 'NoneType' object is not subscriptable\n"
                "[INFO] stage 12 complete\n"
                "[INFO] stage 13 starting\n"
            )
            runtime = HostRuntime(
                HostPaths(workspace=workspace),
                runner=FakeRunner({}),
            )

            observation = runtime.observe(build_seed_major_plan()[1], now=1000.0)

            self.assertFalse(observation.traceback_found)

    def test_observe_flags_uncaught_traceback_with_no_bad_callback_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run = workspace / "runs" / "scene00069_seed42_matrix120m"
            (run / "logs").mkdir(parents=True)
            (run / "logs" / "exploration_pipeline.log").write_text(
                "[INFO] stage 12 starting\n"
                "Traceback (most recent call last):\n"
                "  File \"exploration_pipeline.py\", line 900, in main\n"
                "    run()\n"
                "RuntimeError: unrecoverable\n"
            )
            runtime = HostRuntime(
                HostPaths(workspace=workspace),
                runner=FakeRunner({}),
            )

            observation = runtime.observe(build_seed_major_plan()[0], now=1000.0)

            self.assertTrue(observation.traceback_found)

    def test_observe_marks_docker_inspection_error_as_unknown_not_stopped(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            responses = {
                ("/usr/bin/nvidia-smi", "-L"): CommandResult(0, "GPU 0\n", ""),
                (
                    "/usr/bin/docker",
                    "inspect",
                    "-f",
                    "{{.State.Running}}",
                    "asp-noetic",
                ): CommandResult(124, "", "docker inspect timed out"),
            }
            runner = FakeRunner(responses)
            runtime = HostRuntime(
                HostPaths(workspace=workspace),
                runner=runner,
            )

            observation = runtime.observe(build_seed_major_plan()[0], now=1000.0)

            self.assertFalse(observation.container_inspection_ok)
            self.assertFalse(observation.process_inspection_ok)
            self.assertIn("timed out", " ".join(observation.inspection_errors))
            self.assertFalse(
                any(call[0][1:3] == ("exec", "asp-noetic") for call in runner.calls)
            )

    def test_validate_completed_run_rejects_missing_or_empty_graphs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run = workspace / "runs" / "scene00069_seed42_matrix120m"
            stage = run / "stages" / "20"
            stage.mkdir(parents=True)
            (stage / "navigation_stats.json").write_text(
                json.dumps({"total_path_length_meters": 120.5})
            )
            (stage / "habitat_scene_graph_original_graph0.yaml").write_text("x")
            (stage / "habitat_scene_graph_original_graph1.yaml").write_text("")
            runtime = HostRuntime(
                HostPaths(workspace=workspace),
                runner=FakeRunner({}),
            )

            result = runtime.validate_completed_run(build_seed_major_plan()[0])

            self.assertFalse(result.ok)
            self.assertIn("graph1", " ".join(result.errors))

    def test_restart_container_requires_gpu_to_return(self):
        responses = {
            ("/usr/bin/docker", "stop", "-t", "30", "asp-noetic"): CommandResult(
                0, "asp-noetic\n", ""
            ),
            ("/usr/bin/docker", "start", "asp-noetic"): CommandResult(
                0, "asp-noetic\n", ""
            ),
            (
                "/usr/bin/docker",
                "exec",
                "asp-noetic",
                "nvidia-smi",
                "-L",
            ): CommandResult(0, "GPU 0\n", ""),
        }
        runner = FakeRunner(responses)
        runtime = HostRuntime(runner=runner, sleeper=lambda _: None)

        self.assertTrue(runtime.restart_container())
        self.assertEqual(
            [
                ("/usr/bin/docker", "stop", "-t", "30", "asp-noetic"),
                ("/usr/bin/docker", "start", "asp-noetic"),
                ("/usr/bin/docker", "exec", "asp-noetic", "nvidia-smi", "-L"),
            ],
            [call[0] for call in runner.calls],
        )

    def test_graceful_stop_uses_double_escape_before_any_signal(self):
        escape = (
            "/usr/bin/docker",
            "exec",
            "asp-noetic",
            "env",
            "DISPLAY=:99",
            "xdotool",
            "key",
            "Escape",
        )
        pgrep = (
            "/usr/bin/docker",
            "exec",
            "asp-noetic",
            "pgrep",
            "-f",
            "^python exploration_pipeline.py$",
        )
        runner = SequenceRunner(
            {
                escape: [CommandResult(0, "", ""), CommandResult(0, "", "")],
                pgrep: [CommandResult(1, "", "")],
            }
        )
        runtime = HostRuntime(runner=runner, sleeper=lambda _: None)

        stopped = runtime.graceful_stop(
            build_seed_major_plan()[0], display=99, timeout=10
        )

        self.assertTrue(stopped)
        self.assertEqual([escape, escape, pgrep], [call[0] for call in runner.calls])

    def test_archive_failed_run_never_overwrites_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = build_seed_major_plan()[0]
            run = workspace / "runs" / spec.name
            run.mkdir(parents=True)
            (run / "evidence.txt").write_text("keep")
            runtime = HostRuntime(
                HostPaths(workspace=workspace),
                runner=FakeRunner({}),
            )

            archived = runtime.archive_failed_run(
                spec,
                attempt=1,
                reason="pipeline exited / host reboot",
                now=1000.0,
            )

            self.assertFalse(run.exists())
            self.assertEqual("keep", (archived / "evidence.txt").read_text())
            self.assertIn("FAILED_ATTEMPT1_pipeline_exited_host_reboot", archived.name)

    def test_archive_is_idempotent_if_crash_happened_after_rename(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = build_seed_major_plan()[0]
            archived = (
                workspace
                / "runs"
                / f"{spec.name}_FAILED_ATTEMPT1_pipeline_exited_19700101T001640Z"
            )
            archived.mkdir(parents=True)
            (archived / "evidence.txt").write_text("keep")
            runtime = HostRuntime(
                HostPaths(workspace=workspace),
                runner=FakeRunner({}),
            )

            recovered = runtime.archive_failed_run(
                spec,
                attempt=1,
                reason="pipeline exited",
                now=1000.0,
            )

            self.assertEqual(archived, recovered)
            self.assertEqual("keep", (recovered / "evidence.txt").read_text())

    def test_archive_records_failure_even_if_launcher_never_made_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = build_seed_major_plan()[0]
            runtime = HostRuntime(
                HostPaths(workspace=workspace),
                runner=FakeRunner({}),
            )

            archived = runtime.archive_failed_run(
                spec,
                attempt=1,
                reason="launcher exited",
                now=1000.0,
            )

            evidence = json.loads(
                (archived / "matrix_supervisor_failure.json").read_text()
            )
            self.assertTrue(evidence["source_directory_missing"])
            self.assertEqual("launcher exited", evidence["reason"])

    def test_launch_refuses_to_mix_with_existing_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = build_seed_major_plan()[0]
            (workspace / "runs" / spec.name).mkdir(parents=True)
            runner = FakeRunner({})
            runtime = HostRuntime(HostPaths(workspace=workspace), runner=runner)

            launched = runtime.launch_run(
                spec,
                display=99,
                reasoning_effort="low",
                max_tokens=16000,
                max_calls=3000,
            )

            self.assertFalse(launched)
            self.assertEqual([], runner.calls)

    def test_launch_uses_frozen_science_config_and_approved_call_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = build_seed_major_plan()[4]  # scene 00069, seed 43
            expected_prefix = (
                "/usr/bin/docker",
                "exec",
                "-d",
                "asp-noetic",
                "bash",
                "-lc",
            )
            display_pgrep = (
                "/usr/bin/docker",
                "exec",
                "asp-noetic",
                "pgrep",
                "-f",
                "^Xvfb :99( |$)",
            )
            display_cleanup = (
                "/usr/bin/docker",
                "exec",
                "asp-noetic",
                "python3",
                "-c",
                HostRuntime.CLEAN_DISPLAY_SCRIPT,
                "/tmp/.X99-lock",
                "/tmp/.X11-unix/X99",
            )
            runner = FakeRunner(
                {
                    display_pgrep: CommandResult(1, "", ""),
                    display_cleanup: CommandResult(0, "", ""),
                    expected_prefix
                    + (
                        "exec /workspace/run_llm_pipeline_scene.sh "
                        "/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/"
                        "train/00069-Y8Y6ukxGMvn/Y8Y6ukxGMvn.basis.glb 69 "
                        "scene00069_seed43_matrix120m 99 low 16000 3000 43 >> "
                        "/workspace/runs/matrix_supervisor/launchers/"
                        "scene00069_seed43_matrix120m.log 2>&1",
                    ): CommandResult(0, "", "")
                }
            )
            runtime = HostRuntime(HostPaths(workspace=workspace), runner=runner)

            launched = runtime.launch_run(
                spec,
                display=99,
                reasoning_effort="low",
                max_tokens=16000,
                max_calls=3000,
            )

            self.assertTrue(launched)
            self.assertEqual(
                [display_pgrep, display_cleanup, expected_prefix + (runner.calls[-1][0][-1],)],
                [call[0] for call in runner.calls],
            )

    def test_display_cleanup_refuses_to_remove_live_x_server_socket(self):
        pgrep = (
            "/usr/bin/docker",
            "exec",
            "asp-noetic",
            "pgrep",
            "-f",
            "^Xvfb :99( |$)",
        )
        runner = FakeRunner({pgrep: CommandResult(0, "929\n", "")})
        runtime = HostRuntime(runner=runner)

        cleaned = runtime.cleanup_display(99)

        self.assertFalse(cleaned)
        self.assertEqual([pgrep], [call[0] for call in runner.calls])

    def test_completion_marker_is_written_through_root_container_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = build_seed_major_plan()[0]
            run = workspace / "runs" / spec.name
            run.mkdir(parents=True)
            runner = SuccessRunner()
            runtime = HostRuntime(HostPaths(workspace=workspace), runner=runner)

            runtime.write_completion_marker(
                spec,
                ValidationResult(True, (), 125.325, 27),
                calls=1922,
                now=1000.0,
            )

            argv = runner.calls[0][0]
            self.assertEqual(
                (
                    "/usr/bin/docker",
                    "exec",
                    "asp-noetic",
                    "python3",
                    "-c",
                    HostRuntime.WRITE_JSON_ATOMIC_SCRIPT,
                ),
                argv[:6],
            )
            self.assertEqual(
                "/workspace/runs/scene00069_seed42_matrix120m/"
                "matrix_supervisor_complete.json",
                argv[6],
            )
            payload = json.loads(base64.b64decode(argv[7]))
            self.assertEqual(125.325, payload["path_m"])
            self.assertEqual(1922, payload["calls"])
            self.assertFalse((run / "matrix_supervisor_complete.json").exists())


if __name__ == "__main__":
    unittest.main()
