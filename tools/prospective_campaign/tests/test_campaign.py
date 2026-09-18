import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from prospective_campaign.budget import FakeBudgetBroker
from prospective_campaign.claims import claim_gate
from prospective_campaign.contract import EXPERIMENTAL, MODEL, THINKING_LEVEL
from prospective_campaign.control import (Control, EventLog, atomic_json, can_continue,
                                           isolated_attempt, validate_artifacts, validate_control,
                                           write_completion_marker)
from prospective_campaign.manifest import build_manifest
from prospective_campaign.queue import Pair, PairAdmissionController, deterministic_queue, choose_horizon
from prospective_campaign.scope import decide_scope
from prospective_campaign.state import CampaignSupervisor, Phase


class FakeRunner:
    def __init__(self): self.launched = False
    def connectivity_ok(self): return True
    def technical_health(self): return True
    def launch(self, *args, **kwargs): self.launched = True
    def stop(self, run_path): return True
    def detour_metrics(self, run_path): return None


class Unhealthy:
    def healthy(self): return False


class Healthy:
    def healthy(self): return True


class CampaignTests(unittest.TestCase):
    def test_queue_is_preregistered_in_exact_order(self):
        self.assertEqual([(p.seed, p.scene, p.order) for p in deterministic_queue()], [
            (42, "00069", "O→E"), (42, "00573", "E→O"), (42, "00853", "O→E"),
            (43, "00573", "E→O"), (43, "00853", "O→E"), (43, "00069", "E→O"),
            (44, "00853", "O→E"), (44, "00069", "E→O"), (44, "00573", "O→E")])

    def test_pair_reservation_is_full_pair_and_outcome_blind(self):
        broker = FakeBudgetBroker(10)
        controller = PairAdmissionController(broker, Healthy(), cost_per_120m=8)
        result = controller.admit_pair(Pair("00069", 42, "O→E", 120))
        self.assertTrue(result.admitted)
        self.assertEqual(8, result.amount)
        self.assertFalse(controller.admit_pair(Pair("00573", 42, "E→O", 120)).admitted)
        self.assertFalse(PairAdmissionController(broker, Unhealthy(), cost_per_120m=1)
                         .admit_pair(Pair("00853", 42, "O→E", 25)).admitted)

    def test_horizon_ladder_is_descending_and_selected_before_results(self):
        self.assertEqual(choose_horizon(10, 8), 120)
        self.assertEqual(choose_horizon(4, 8), 50)
        self.assertIsNone(choose_horizon(0.1, 8))

    def test_control_rejects_unknown_or_wrong_hashes(self):
        with self.assertRaises(ValueError):
            validate_control({"paused": False, "approved_hashes": ("wrong",)}, ("right",))
        with self.assertRaises(ValueError):
            validate_control({"paused": False, "approved_hashes": (), "extra": 1}, ())

    def test_atomic_status_and_append_only_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "status.json"
            atomic_json(path, {"phase": "ready"})
            self.assertEqual(json.loads(path.read_text())["phase"], "ready")
            log = EventLog(Path(tmp) / "events.jsonl")
            log.append("ready")
            log.append("paused", reason="technical")
            self.assertEqual(len((Path(tmp) / "events.jsonl").read_text().splitlines()), 2)

    def test_connectivity_and_limits_fail_closed(self):
        control = Control(approved_hashes=())
        self.assertEqual(can_continue(connectivity_ok=False, disk_gb=100, stalled=False,
                                      runtime_exceeded=False, control=control)[0], False)
        self.assertEqual(can_continue(connectivity_ok=True, disk_gb=24, stalled=False,
                                      runtime_exceeded=False, control=control)[0], False)
        self.assertEqual(can_continue(connectivity_ok=True, disk_gb=100, stalled=False,
                                      runtime_exceeded=False, spend_known=False, control=control)[0], False)

    def test_supervisor_pause_and_completion_state_machine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); runner = FakeRunner()
            supervisor = CampaignSupervisor(root / "status.json", EventLog(root / "events.jsonl"), runner)
            paused = Control(paused=True, approved_hashes=())
            self.assertFalse(supervisor.start(root / "run", scene="00069", seed=42,
                                              policy=EXPERIMENTAL, horizon=25, control=paused))
            self.assertEqual(supervisor.state.phase, Phase.PAUSED)
            supervisor.state = supervisor.state.__class__(Phase.READY, 1, "")
            run = root / "run"; run.mkdir()
            self.assertTrue(supervisor.start(run, scene="00069", seed=42, policy=EXPERIMENTAL,
                                             horizon=25, control=Control(approved_hashes=())))
            self.assertTrue(runner.launched)

    def test_retries_use_new_isolated_attempt_and_partial_is_not_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = isolated_attempt(root, "paired_v5", "00069", 42, "official_asp", 1)
            second = isolated_attempt(root, "paired_v5", "00069", 42, "official_asp", 2)
            self.assertNotEqual(first, second)
            (first / "trajectory.json").write_text("partial")
            self.assertFalse(validate_artifacts(first, ("trajectory.json",))[0])

    def test_completion_marker_requires_hash_validated_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            artifact = run / "trajectory.json"
            artifact.write_text("complete")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            (run / "ARTIFACTS.sha256").write_text(f"{digest}  trajectory.json\n")
            write_completion_marker(run, required=("trajectory.json",))
            self.assertTrue((run / "COMPLETE.json").exists())

    def test_manifest_redacts_secret_values_and_records_contract(self):
        manifest = build_manifest(source_tag="v5", author_commit="abc", environment={"api_key": "do-not-write"},
                                  hashes={name: "h" for name in ("scene", "reference", "navmesh", "calibrator", "prompt", "policy")}, model=MODEL, thinking_level=THINKING_LEVEL,
                                  seed=42, start_state="s", budget_ledger_id="ledger", controller_mode="dry",
                                  audit_mode="strict")
        self.assertEqual(manifest["environment"]["api_key"], "[REDACTED]")
        self.assertEqual(manifest["model"], "gemini-3.8-flash")
        self.assertNotIn("do-not-write", json.dumps(manifest))

    def test_claim_gates(self):
        self.assertEqual(claim_gate(complete_pairs=2, complete_block=False, invalid_hypothesis_ok=True,
                                    fp_detour_reduction=.2, baseline_detour=1, f1_loss=0, ged_increase=0)["status"], "descriptive_only")
        self.assertEqual(claim_gate(complete_pairs=6, complete_block=True, invalid_hypothesis_ok=True,
                                    fp_detour_reduction=None, baseline_detour=1, f1_loss=0, ged_increase=0)["status"], "not_identifiable")
        self.assertEqual(claim_gate(complete_pairs=6, complete_block=True, invalid_hypothesis_ok=True,
                                    fp_detour_reduction=.2, baseline_detour=1, f1_loss=.05, ged_increase=.1)["status"], "established")

    def test_scope_decision_is_cost_adaptive_and_terminal(self):
        decision = decide_scope(pilot_cost=18, available_after_pilot=162,
                                worst_case_pair_cost=40, horizon=120)
        self.assertTrue(decision.seed42_block_fits)
        self.assertFalse(decision.seed43_block_fits)
        self.assertEqual(decision.terminal_reason, "seed42 then complete seed blocks only while each block fits")


if __name__ == "__main__":
    unittest.main()
