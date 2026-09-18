from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.prospective_eval.auditor import PassiveNavmeshAuditor, RealizedMotion, taxonomy_for_realized_motion
from tools.prospective_eval.classification import EvidencePolicy, classify_reference
from tools.prospective_eval.detour import InterventionRecord, evaluate_detour
from tools.prospective_eval.instrumentation import PassiveMotionRecorder
from tools.prospective_eval.runner import BranchRunner, fixed_stage_samples
from tools.prospective_eval.schema import Classification, EventTaxonomy, Pose


class Pathfinder:
    def __init__(self, navigable=True, distance=2.0): self.navigable, self.distance = navigable, distance
    def is_navigable(self, position): return self.navigable
    def try_find_path(self, start, goal): return self.distance


class Snapshot:
    def __init__(self, exact=True): self.exact, self.value = exact, 0
    def snapshot(self): return self.value
    def restore(self, snapshot): self.value = snapshot; return self.exact
    def state_hash(self): return str(self.value)


class ProspectiveTests(unittest.TestCase):
    def test_passive_audit_never_calls_execution_and_rejects_navmesh(self):
        result = PassiveNavmeshAuditor(Pathfinder(False)).audit(Pose((0, 0, 0)), Pose((1, 0, 0)))
        self.assertEqual(result.taxonomy, EventTaxonomy.NAVMESH_AUDIT_REJECTION)
        self.assertFalse(result.admissible)

    def test_passive_cannot_assert_contact_and_overlap_is_not_contact(self):
        motion = RealizedMotion(Pose((0, 0, 0)), Pose((0, 0, 0)), None, None, "none")
        self.assertEqual(taxonomy_for_realized_motion(motion, "passive"), EventTaxonomy.UNKNOWN)

    def test_passive_instrumentation_does_not_change_fixture_command_result_or_observation(self):
        previous = Pose((0, 0, 0))
        requested = Pose((1, 0, 0))
        result = Pose((1, 0, 0))
        command = {"type": "move", "target": [1, 0, 0]}
        observation = {"rgb_hash": "fixture", "objects": []}
        baseline = (command.copy(), result.as_dict(), observation.copy())
        recorder = PassiveMotionRecorder(PassiveNavmeshAuditor(Pathfinder(True)))
        event = recorder.record(event_id="1", stage_id="s", segment_id="g", command_id="c", previous_pose=previous, requested_pose=requested, result_pose=result, command=command, observation=observation)
        self.assertEqual((command, result.as_dict(), observation), baseline)
        self.assertEqual(event.controller_mode, "passive")

    def test_reference_mismatch_is_not_absence(self):
        self.assertEqual(classify_reference(reference_match=False, physical_evidence=None, policy=EvidencePolicy()), Classification.REFERENCE_UNMATCHED)

    def test_detour_requires_all_preregistered_gates(self):
        record = InterventionRecord("same", {}, {}, "target", True, [[0]], [[0]], 5, 3, "done", "done", True, False, Classification.CONFIRMED_FALSE_POSITIVE, True)
        self.assertEqual(evaluate_detour(record, EvidencePolicy()), "tradeoff")
        record = InterventionRecord("same", {}, {}, "target", True, [[0]], [[0]], 5, 3, "done", "done", True, True, Classification.CONFIRMED_FALSE_POSITIVE, True)
        self.assertEqual(evaluate_detour(record, EvidencePolicy()), "false_positive_detour")

    def test_branch_runner_fails_closed_without_exact_restore(self):
        with self.assertRaises(RuntimeError): BranchRunner(Snapshot(False)).run_pair(lambda: 1, lambda: 2)

    def test_sampling_is_fixed_and_missingness_visible(self):
        samples = fixed_stage_samples(["a", "b", "c"], stride=2)
        self.assertEqual([s.eligible for s in samples], [True, False, True])

    def test_append_only_log_has_checksum(self):
        from tools.prospective_eval.schema import AppendOnlyLog
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            digest = AppendOnlyLog(str(path)).append({"event_id": "1"})
            self.assertEqual(len(digest), 64)
            self.assertIn("record_sha256", path.read_text())


if __name__ == "__main__": unittest.main()
