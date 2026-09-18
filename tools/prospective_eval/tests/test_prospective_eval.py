from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from prospective_eval.auditor import (
    EngineEventReceipt,
    PassiveNavmeshAuditor,
    RealizedMotion,
    taxonomy_for_realized_motion,
)
from prospective_eval.classification import EvidencePolicy, classify_reference, import_confirmed_false_positive
from prospective_eval.detour import BranchEvidence, InterventionEvidence, PathSample, evaluate_intervention, paired_policy_comparison
from prospective_eval.instrumentation import PassiveMotionRecorder
from prospective_eval.runner import AdapterCapabilities, BranchRunner, SnapshotManifest
from prospective_eval.schema import (
    AppendOnlyLog, Classification, ControllerMode, EvidenceReceipt, EventTaxonomy, MotionEvent, MotionOutcome, Pose,
)


class Pathfinder:
    def __init__(self, navigable=True, distance=2.0): self.navigable, self.distance = navigable, distance
    def is_navigable(self, position): return self.navigable
    def try_find_path(self, start, goal): return self.distance


class BadPathfinder(Pathfinder):
    def try_find_path(self, start, goal): return float("nan")


class FakeAdapter:
    def __init__(self, mutate=False):
        self.mutate, self.external, self.restore_count = mutate, "external", 0
        self.manifest = SnapshotManifest.create(manifest_id="m", simulator_hash="s", agent_hash="a", mapping_hash="map", controller_hash="c", rng_hash="r", filesystem_hash="f", inputs_hash="i", state_hash="state")
    def capabilities(self): return AdapterCapabilities(True, True, True, True, True)
    def snapshot_manifest(self): return self.manifest
    def restore(self, manifest):
        self.restore_count += 1
        branch = ["original", "counterfactual", "cleanup"][min(self.restore_count - 1, 2)]
        return EvidenceReceipt.issue("restore-" + manifest.manifest_id + str(self.restore_count), "restore", {"branch": branch})
    def current_manifest_hash(self): return self.manifest.manifest_hash
    def external_hashes(self): return {"external": self.external}


def receipt(receipt_id, kind, **payload): return EvidenceReceipt.issue(receipt_id, kind, payload)


def complete_evidence():
    manifest_payload = {"manifest_hash": "manifest", "state_hash": "state"}
    manifest = receipt("manifest", "snapshot_manifest", **manifest_payload)
    label = receipt("fp", "false_positive_label", label="confirmed_false_positive", reviewer_id="reviewer", provenance_hash="prov", reference_criterion="exhaustive-reference")
    def branch(name, distance):
        execution_id = name + "-exec"
        samples = [PathSample("2026-01-01T00:00:00+00:00", "seg1", Pose((0, 0, 0))), PathSample("2026-01-01T00:00:01+00:00", "seg1", Pose((distance, 0, 0)))]
        return BranchEvidence(name, execution_id, receipt(name + "-restore", "restore", branch=name, snapshot_manifest_hash="manifest"), receipt(name + "-execution", "execution", execution_id=execution_id, snapshot_manifest_hash="manifest", policy_attribution="fp-removed", fp_removed=name == "alternative", cumulative_distance_m=distance), receipt(name + "-reach", "reachability", execution_id=execution_id, reachable=True), "target", samples, receipt(name + "-completion", "completion", completed=True, abort_reason=""), receipt(name + "-useful", "useful_observation", criterion_met=True), "state", "after-" + name, {"rng": "same", "observation": "same", "filesystem": "same"})
    return InterventionEvidence(manifest, label, branch("original", 5), branch("alternative", 3), "fp-removed", "target", "fp-removed")


class Tests(unittest.TestCase):
    def test_reached_uses_target_pose_not_equal_radius(self):
        recorder = PassiveMotionRecorder(PassiveNavmeshAuditor(Pathfinder()))
        event = recorder.record(event_id="e", stage_id="s", segment_id="g", command_id="c", previous_pose=Pose((0, 0, 0), (0, 0, 0, 1)), requested_pose=Pose((2, 0, 0), (0, 0, 0, 1)), result_pose=Pose((0, 2, 0), (0, 0, 0, 1)))
        self.assertEqual(event.outcome, MotionOutcome.PARTIAL)
        self.assertAlmostEqual(event.target_position_error_m, math.sqrt(8))

    def test_rotation_mismatch_is_partial(self):
        recorder = PassiveMotionRecorder(PassiveNavmeshAuditor(Pathfinder()))
        event = recorder.record(event_id="e", stage_id="s", segment_id="g", command_id="c", previous_pose=Pose((0, 0, 0), (0, 0, 0, 1)), requested_pose=Pose((1, 0, 0), (0, 0, 0, 1)), result_pose=Pose((1, 0, 0), (0, 0, 1, 0)))
        self.assertEqual(event.outcome, MotionOutcome.PARTIAL)

    def test_invalid_numbers_identifiers_and_mode_rejected(self):
        with self.assertRaises(ValueError): Pose((float("inf"), 0, 0))
        with self.assertRaises(ValueError): MotionEvent("bad id!", "2026-01-01T00:00:00+00:00", "s", "g", "c", Pose((0, 0, 0)), Pose((0, 0, 0)), None, 0, None, None, None, None, MotionOutcome.UNKNOWN, EventTaxonomy.UNKNOWN, "x", "x", None)
        with self.assertRaises(ValueError): ControllerMode("invalid")

    def test_fake_contact_and_blocked_receipts_are_unknown(self):
        motion = RealizedMotion(Pose((0, 0, 0)), Pose((0, 0, 0)), "exec", None)
        self.assertEqual(taxonomy_for_realized_motion(motion, ControllerMode.COLLISION_AWARE_EXPERIMENT), EventTaxonomy.UNKNOWN)
        fake = EngineEventReceipt("fake", "contact", "other", "2026-01-01T00:00:00+00:00", "prov", contact=True)
        self.assertEqual(taxonomy_for_realized_motion(RealizedMotion(Pose((0, 0, 0)), Pose((0, 0, 0)), "exec", fake), ControllerMode.COLLISION_AWARE_EXPERIMENT), EventTaxonomy.UNKNOWN)

    def test_bad_pathfinder_is_unknown_not_collision(self):
        result = PassiveNavmeshAuditor(BadPathfinder()).audit(Pose((0, 0, 0)), Pose((1, 0, 0)))
        self.assertEqual(result.taxonomy, EventTaxonomy.UNKNOWN)
        self.assertIsNone(result.admissible)

    def test_external_fp_receipt_is_hashed_and_unmatched_stays_unknown(self):
        policy = EvidencePolicy(allowed_reviewers=frozenset({"reviewer"}))
        self.assertEqual(import_confirmed_false_positive(complete_evidence().fp_label_receipt, policy), Classification.CONFIRMED_FALSE_POSITIVE)
        self.assertEqual(classify_reference(reference_match=False, physical_evidence=None, policy=policy), Classification.REFERENCE_UNMATCHED)

    def test_intervention_recomputes_paths_and_requires_receipts(self):
        self.assertEqual(evaluate_intervention(complete_evidence(), EvidencePolicy(allowed_reviewers=frozenset({"reviewer"}))), "false_positive_detour")
        evidence = complete_evidence()
        bad = evidence.original.path_samples[1]
        tampered = BranchEvidence(**{**evidence.original.__dict__, "path_samples": [evidence.original.path_samples[0], PathSample(bad.timestamp, bad.segment_id, Pose((99, 0, 0)))]})
        with self.assertRaises(ValueError): evaluate_intervention(InterventionEvidence(evidence.snapshot_manifest, evidence.fp_label_receipt, tampered, evidence.alternative, evidence.common_policy_attribution, evidence.expected_target_id, evidence.expected_attribution), EvidencePolicy(allowed_reviewers=frozenset({"reviewer"})))

    def test_independent_policy_paths_are_not_causal_detours(self):
        path = [PathSample("2026-01-01T00:00:00+00:00", "s", Pose((0, 0, 0))), PathSample("2026-01-01T00:00:01+00:00", "s", Pose((1, 0, 0)))]
        self.assertEqual(paired_policy_comparison(path, path, removed_nodes=["x"])["result"], "not_identifiable")

    def test_branch_runner_declares_capabilities_and_catches_external_mutation(self):
        adapter = FakeAdapter()
        with self.assertRaises(RuntimeError): BranchRunner(adapter).run_pair(lambda: setattr(adapter, "external", "changed"), lambda: None)

    def test_append_log_refuses_symlink_even_when_target_is_inside_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "other.jsonl"
            real.write_text("")
            link = root / "events.jsonl"
            link.symlink_to(real)
            with self.assertRaises(ValueError):
                AppendOnlyLog(str(link), root=directory)

    def test_append_log_chain_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            log = AppendOnlyLog(str(path), root=directory)
            log.append({"event_id": "e"}); log.append({"event_id": "f"})
            self.assertTrue(log.verify())
            rows = path.read_text().splitlines(); rows[0] = rows[0].replace('"event_id":"e"', '"event_id":"tampered"'); path.write_text("\n".join(rows) + "\n")
            self.assertFalse(log.verify())


if __name__ == "__main__": unittest.main()
