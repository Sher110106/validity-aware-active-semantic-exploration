import sys
import json
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from matrix_supervisor.policy import (  # noqa: E402
    ActionKind,
    Control,
    Observation,
    State,
    bootstrap_state,
    build_seed_major_plan,
    choose_action,
)


class MatrixSupervisorPolicyTests(unittest.TestCase):
    def test_plan_is_seed_major_and_names_all_twelve_runs(self):
        plan = build_seed_major_plan()

        self.assertEqual(12, len(plan))
        self.assertEqual(
            [
                ("00069", 42),
                ("00573", 42),
                ("00853", 42),
                ("00871", 42),
                ("00069", 43),
                ("00573", 43),
                ("00853", 43),
                ("00871", 43),
                ("00069", 44),
                ("00573", 44),
                ("00853", 44),
                ("00871", 44),
            ],
            [(run.scene, run.seed) for run in plan],
        )
        self.assertEqual("scene00069_seed42_matrix120m", plan[0].name)

    def test_human_visible_plan_matches_executable_plan(self):
        plan_file = Path(__file__).resolve().parents[1] / "matrix_plan.json"
        documented = json.loads(plan_file.read_text())["runs"]

        self.assertEqual(
            [(run.scene, run.seed) for run in build_seed_major_plan()],
            [(item["scene"], item["seed"]) for item in documented],
        )

    def test_bootstrap_adopts_live_run_and_counts_prior_failed_attempt(self):
        state = bootstrap_state(
            now=1000.0,
            active_index=0,
            active_pipeline=True,
            failed_attempts=1,
            observed_path_m=35.1,
            observed_calls=621,
        )

        self.assertEqual("running", state.phase)
        self.assertEqual(2, state.attempt)
        self.assertEqual(35.1, state.last_path_m)
        self.assertEqual(621, state.last_calls)

    def test_healthy_running_observation_is_a_noop(self):
        state = State.running(now=1000.0, attempt=2, path_m=35.1, calls=621)
        observation = Observation.healthy(now=1060.0, path_m=38.0, calls=680)

        decision = choose_action(state, observation, Control())

        self.assertEqual(ActionKind.NONE, decision.kind)
        self.assertEqual(1060.0, decision.state.last_progress_at)
        self.assertEqual(38.0, decision.state.last_path_m)

    def test_path_budget_stop_wins_even_when_automation_is_paused(self):
        state = State.running(now=1000.0, attempt=1, path_m=119.0, calls=2000)
        observation = Observation.healthy(now=1060.0, path_m=121.2, calls=2050)

        decision = choose_action(
            state,
            observation,
            Control(paused=True),
        )

        self.assertEqual(ActionKind.STOP_AT_BUDGET, decision.kind)

    def test_container_gpu_must_fail_twice_before_healing(self):
        state = State.running(now=1000.0, attempt=1, path_m=20.0, calls=400)
        first = Observation.healthy(now=1060.0, path_m=20.0, calls=400)
        first.container_gpu_ok = False

        decision1 = choose_action(state, first, Control())
        self.assertEqual(ActionKind.NONE, decision1.kind)
        self.assertEqual(1, decision1.state.container_gpu_failures)

        second = Observation.healthy(now=1120.0, path_m=20.0, calls=400)
        second.container_gpu_ok = False
        decision2 = choose_action(decision1.state, second, Control())
        self.assertEqual(ActionKind.HEAL_CONTAINER_GPU, decision2.kind)

    def test_host_gpu_failure_pauses_without_touching_container(self):
        state = State.running(now=1000.0, attempt=1, path_m=20.0, calls=400)
        observation = Observation.healthy(now=1060.0, path_m=20.0, calls=400)
        observation.host_gpu_ok = False
        observation.container_gpu_ok = False

        first = choose_action(state, observation, Control())
        self.assertEqual(ActionKind.NONE, first.kind)

        observation.now = 1120.0
        decision = choose_action(first.state, observation, Control())

        self.assertEqual(ActionKind.PAUSE, decision.kind)
        self.assertIn("host GPU", decision.reason)

    def test_clear_failure_retries_only_first_attempt(self):
        observation = Observation.healthy(now=1060.0, path_m=50.0, calls=900)
        observation.pipeline_pids = []

        first_attempt = State.running(
            now=1000.0, attempt=1, path_m=50.0, calls=900
        )
        retry = choose_action(first_attempt, observation, Control())
        self.assertEqual(ActionKind.RETRY_RUN, retry.kind)

        second_attempt = State.running(
            now=1000.0, attempt=2, path_m=50.0, calls=900
        )
        pause = choose_action(second_attempt, observation, Control())
        self.assertEqual(ActionKind.PAUSE, pause.kind)
        self.assertIn("retry limit", pause.reason)

    def test_low_disk_blocks_a_new_launch(self):
        state = State.ready(now=1000.0, attempt=1)
        observation = Observation.idle(now=1060.0, free_disk_gb=24.9)

        decision = choose_action(state, observation, Control(min_free_disk_gb=25.0))

        self.assertEqual(ActionKind.PAUSE, decision.kind)
        self.assertIn("disk", decision.reason)

    def test_ambiguous_stall_pauses_without_failure_or_retry(self):
        state = State.running(now=1000.0, attempt=1, path_m=20.0, calls=400)
        observation = Observation.healthy(now=2801.0, path_m=20.0, calls=400)

        decision = choose_action(
            state,
            observation,
            Control(ambiguous_stall_seconds=1800),
        )

        self.assertEqual(ActionKind.PAUSE, decision.kind)
        self.assertIn("ambiguous stall", decision.reason)

    def test_duplicate_pipeline_pauses_instead_of_killing(self):
        state = State.running(now=1000.0, attempt=1, path_m=20.0, calls=400)
        observation = Observation.healthy(now=1060.0, path_m=20.0, calls=400)
        observation.pipeline_pids = [101, 202]

        decision = choose_action(state, observation, Control())

        self.assertEqual(ActionKind.PAUSE, decision.kind)
        self.assertIn("multiple", decision.reason)

    def test_pipeline_for_another_run_pauses_instead_of_adopting_it(self):
        state = State.running(now=1000.0, attempt=1, path_m=20.0, calls=400)
        observation = Observation.healthy(now=1060.0, path_m=20.0, calls=400)
        observation.pipeline_matches_run = False
        observation.pipeline_log_dirs = ["/workspace/runs/some_other_run/prompts"]

        decision = choose_action(state, observation, Control())

        self.assertEqual(ActionKind.PAUSE, decision.kind)
        self.assertIn("different run", decision.reason)

    def test_operator_pause_blocks_retry_but_not_path_budget_stop(self):
        state = State.running(now=1000.0, attempt=1, path_m=50.0, calls=900)
        observation = Observation.healthy(now=1060.0, path_m=50.0, calls=900)
        observation.pipeline_pids = []

        decision = choose_action(state, observation, Control(paused=True))

        self.assertEqual(ActionKind.PAUSE, decision.kind)
        self.assertEqual("running", decision.state.phase)
        self.assertIn("operator", decision.reason)

    def test_failed_process_inspection_never_triggers_retry_or_container_restart(self):
        state = State.running(now=1000.0, attempt=1, path_m=50.0, calls=900)
        observation = Observation.healthy(now=1060.0, path_m=50.0, calls=900)
        observation.pipeline_pids = []
        observation.process_inspection_ok = False
        observation.inspection_errors = ["docker exec timed out"]

        decision = choose_action(state, observation, Control())

        self.assertEqual(ActionKind.NONE, decision.kind)
        self.assertIn("refusing process action", decision.reason)

    def test_failed_container_inspection_never_assumes_container_is_stopped(self):
        state = State.running(now=1000.0, attempt=1, path_m=50.0, calls=900)
        observation = Observation.healthy(now=1060.0, path_m=50.0, calls=900)
        observation.container_running = False
        observation.container_inspection_ok = False

        decision = choose_action(state, observation, Control())

        self.assertEqual(ActionKind.NONE, decision.kind)
        self.assertNotEqual(ActionKind.START_CONTAINER, decision.kind)


if __name__ == "__main__":
    unittest.main()
