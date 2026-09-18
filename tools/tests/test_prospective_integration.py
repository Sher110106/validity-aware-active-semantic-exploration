"""Cross-package integration tests tying the four prospective branches
together: gemini_campaign's real ledger, prospective_campaign's block/pair
lifecycle, prospective_eval's motion instrumentation, and
prospective_runtime's policy engine. Nothing here is a live/paid run -- the
Gemini transport itself is out of scope until its BudgetBroker protocol is
reconciled with the real ledger's reserve/settle shape (tracked separately;
see the handoff notes)."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from gemini_campaign.errors import AccountingHalt
from gemini_campaign.ledger import Ledger

from prospective_campaign.contract import BASELINE, EXPERIMENTAL
from prospective_campaign.control import Control, EventLog, Telemetry
from prospective_campaign.queue import PairAdmissionController, deterministic_queue, validate_block
from prospective_campaign.state import CampaignSupervisor, Phase, PairState

from prospective_eval.auditor import PassiveNavmeshAuditor
from prospective_eval.instrumentation import PassiveMotionRecorder
from prospective_eval.schema import AppendOnlyLog, Pose
from prospective_eval.summary import summarize_jsonl

from prospective_runtime.policy import apply_unanimity_policy

from prospective_integration.campaign_ledger_adapter import CampaignLedgerAdapter


class Health:
    def healthy(self) -> bool:
        return True


class Pathfinder:
    def is_navigable(self, position):
        return True

    def try_find_path(self, start, goal):
        return sum(abs(a - b) for a, b in zip(start, goal))


def write_artifact(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "trajectory.json"
    artifact.write_text("ok")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (run_dir / "ARTIFACTS.sha256").write_text(f"{digest}  trajectory.json\n")


OBSERVED = {"nodes": [{"id": "room0", "type": "room", "label": "room", "center": [0, 0, 0]}], "edges": []}


def member(name: str):
    return {"nodes": OBSERVED["nodes"] + [{"id": name, "type": "object", "label": name,
            "center": [1, 0, 0], "dimensions": [1, 1, 1], "room_id": "room0"}], "edges": []}


class CompleteFakePairTests(unittest.TestCase):
    def test_admits_certifies_both_members_and_records_motion_and_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = Ledger(str(root / "ledger.sqlite"))
            adapter = CampaignLedgerAdapter(ledger, campaign_id="paired_v5")

            pairs = deterministic_queue(25)[:3]
            validate_block(pairs, 42, 25)
            admission = PairAdmissionController(adapter, Health(), worst_block_micro_usd=64_820_000).admit_block(
                pairs, allocation_id="block-42-25m")
            self.assertTrue(admission.admitted)

            pair = pairs[0]
            self.assertEqual(pair.policies, (BASELINE, EXPERIMENTAL))

            events = EventLog(root / "events.jsonl")
            pair_slug = f"{pair.scene}-seed{pair.seed}-{pair.horizon_m}m"  # pair.id has a non-slug arrow
            state = PairState(2, "paired_v5", "block-42-25m", pair_slug, "run-1", 1, "block-42-25m",
                              "a" * 64, "b" * 64, pair.policies, (), Phase.READY.value, 0)
            supervisor = CampaignSupervisor(root / "status.json", events, runner=None)
            telemetry = Telemetry(True, True, 100, 0, 0, True)
            self.assertTrue(supervisor.start(state, telemetry=telemetry, control=Control()))
            self.assertEqual(supervisor.state.phase, Phase.RUNNING.value)

            motion_log = AppendOnlyLog(str(root / "motion.jsonl"), root=str(root))
            recorder = PassiveMotionRecorder(PassiveNavmeshAuditor(Pathfinder()))

            for index, policy in enumerate(pair.policies):
                run_dir = root / "runs" / policy
                write_artifact(run_dir)
                event = recorder.record(event_id=f"{policy}-e0", stage_id="0", segment_id="s0",
                                        command_id=f"{policy}-c0", previous_pose=Pose((0, 0, 0)),
                                        requested_pose=Pose((1, 0, 0)), result_pose=Pose((1, 0, 0)))
                motion_log.append({"event_id": event.event_id, "policy": policy,
                                   "taxonomy": event.taxonomy.value,
                                   "controller_mode": event.controller_mode.value,
                                   "passive_navmesh_admissible": event.passive_navmesh_admissible})
                self.assertTrue(adapter.draw("block-42-25m", f"{pair_slug}:{policy}", 100_000))
                certified = supervisor.certify_member(run_dir, ("trajectory.json",), policy)
                self.assertTrue(certified)
                expected_phase = Phase.COMPLETE if index == 1 else Phase.RESERVED
                self.assertEqual(supervisor.state.phase, expected_phase.value)

            self.assertEqual(supervisor.state.completed_members, pair.policies)
            self.assertTrue(motion_log.verify())
            summary = summarize_jsonl(str(root / "motion.jsonl"))
            self.assertEqual(summary["events"], 2)

            experimental_graph = apply_unanimity_policy(
                OBSERVED, [member("chair")] * 4, track_id="graph0",
                member_ids=["m0", "m1", "m2", "m3"],
            )
            self.assertIn("chair", {n["id"] for n in experimental_graph["nodes"]})

            event_lines = (root / "events.jsonl").read_text().splitlines()
            self.assertEqual(len(event_lines), 3)  # launch_intent + 2 complete, no duplicates

            ledger.close()


class CrashRecoveryTests(unittest.TestCase):
    def test_reopening_the_ledger_preserves_allocation_and_draws(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "ledger.sqlite")
            ledger = Ledger(path)
            adapter = CampaignLedgerAdapter(ledger, campaign_id="paired_v5")
            self.assertTrue(adapter.reserve_block("block-1", 1_000))
            self.assertTrue(adapter.draw("block-1", "req-1", 400))
            ledger.close()  # simulate a crash between draws

            reopened = Ledger(path)
            reopened_adapter = CampaignLedgerAdapter(reopened, campaign_id="paired_v5")
            # A retry of the same request_id must not double-draw.
            self.assertFalse(reopened_adapter.draw("block-1", "req-1", 400))
            # The prior 400 is still counted against the 1000 ceiling.
            self.assertFalse(reopened_adapter.draw("block-1", "req-2", 700))
            self.assertTrue(reopened_adapter.draw("block-1", "req-2", 600))
            # A second block with the same id can never be re-allocated (idempotent).
            self.assertFalse(reopened_adapter.reserve_block("block-1", 1))
            reopened.close()


class UnknownSpendTests(unittest.TestCase):
    def test_unsettled_request_keeps_its_reservation_and_blocks_further_draws(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger(str(Path(tmp) / "ledger.sqlite"))
            allocation = ledger.allocate(campaign_id="c", phase_id="probe", amount_microusd=300_000)
            reservation = ledger.reserve(
                allocation_id=allocation.allocation_id, campaign_id="c", phase_id="probe",
                run_id="run", stage_id="stage", member_id="member", tool_turn_id="turn",
                attempt_id="attempt", model="gemini-3.8-flash", thinking_level="medium",
                max_output_tokens=65_536, input_bound=1,
            )
            ledger.mark_dispatched(reservation.request_id)
            # The provider response never arrives (timeout/unknown): no settle() call,
            # and no hidden retry either -- the reservation simply stays outstanding.
            summary = ledger.summary()
            self.assertEqual(summary["unresolved_requests"], 1)
            self.assertGreater(summary["reserved_microusd"], 0)
            # A second reservation attempt on the SAME allocation still has to share
            # the space the unresolved first one occupies -- an unknown/timed-out
            # request is never silently freed to make room for more spend.
            with self.assertRaises(AccountingHalt):
                ledger.reserve(
                    allocation_id=allocation.allocation_id, campaign_id="c", phase_id="probe",
                    run_id="run", stage_id="stage", member_id="member", tool_turn_id="turn",
                    attempt_id="attempt-2", model="gemini-3.8-flash", thinking_level="medium",
                    max_output_tokens=65_536, input_bound=1,
                )
            ledger.close()


if __name__ == "__main__":
    unittest.main()
