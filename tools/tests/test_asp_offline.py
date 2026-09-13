from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from asp_offline.calibration import IsotonicCalibrator, fit_leave_one_scene_out
from asp_offline.author_io import normalize_author_graph
from asp_offline.evaluator import area_under_curve, evaluate_graph, evaluate_run
from asp_offline.models import ValidationIssue
from asp_offline.scoring import score_viewpoint
from asp_offline.validator import ValidationConfig, label_against_reference, validate_completion, validate_ensemble


OBSERVED = {
    "nodes": [
        {"id": "room0", "type": "room", "label": "living", "center": [0, 0, 0], "dimensions": [10, 3, 10], "observed": True},
        {"id": "wall0", "type": "structure", "label": "wall", "center": [4, 0, 0], "dimensions": [0.2, 3, 10], "observed": True},
    ],
    "edges": [],
}


def completion(nodes, edges=()):
    return "```yaml\n" + json.dumps({"nodes": OBSERVED["nodes"] + list(nodes), "edges": list(edges)}) + "\n```"


class ValidatorTests(unittest.TestCase):
    def test_valid_graph_is_accepted(self):
        result = validate_completion(completion([{"id": "chair", "type": "object", "label": "chair", "center": [0, 0, 0], "dimensions": [1, 1, 1], "room_id": "room0"}]), OBSERVED)
        self.assertTrue(result.accepted)
        self.assertEqual(result.removed_nodes, [])

    def test_invalid_prediction_is_removed_without_losing_observed_graph(self):
        result = validate_completion(completion([{"id": "chair", "type": "object", "label": "chair", "center": [4, 0, 0], "dimensions": [1, 1, 1], "room_id": "room0"}]), OBSERVED)
        self.assertTrue(result.accepted)
        self.assertEqual(result.removed_nodes, ["chair"])
        self.assertEqual({n["id"] for n in result.graph["nodes"]}, {"room0", "wall0"})

    def test_parse_failure_is_rejected_and_ensemble_falls_back(self):
        result = validate_completion("no fenced block", OBSERVED)
        self.assertTrue(result.rejected)
        ensemble = validate_ensemble(["no fenced block"], OBSERVED)
        self.assertTrue(ensemble[-1].accepted)
        self.assertEqual({n["id"] for n in ensemble[-1].graph["nodes"]}, {"room0", "wall0"})
        self.assertEqual(ensemble[-1].graph["frontier_fallback"]["strategy"], "geometric")

    def test_parsed_mapping_requires_explicit_opt_in(self):
        parsed = {"nodes": OBSERVED["nodes"], "edges": []}
        self.assertTrue(validate_completion(parsed, OBSERVED).rejected)
        self.assertTrue(validate_completion(parsed, OBSERVED, ValidationConfig(allow_parsed_mapping=True)).accepted)

    def test_duplicate_observed_node_is_rejected(self):
        duplicate = completion([OBSERVED["nodes"][0]])
        result = validate_completion(duplicate, OBSERVED)
        self.assertTrue(result.rejected)
        self.assertTrue(any(issue.code == "unique_identifier" for issue in result.issues))

    def test_null_node_identifier_is_rejected_before_normalization(self):
        malformed = "```yaml\n" + json.dumps({
            "nodes": [{"id": None, "type": "object", "label": "chair", "center": [0, 0, 0], "dimensions": [1, 1, 1]}],
            "edges": [],
        }) + "\n```"
        result = validate_completion(malformed, {"nodes": [], "edges": []})
        self.assertTrue(result.rejected)
        self.assertTrue(any(issue.code == "node_schema" for issue in result.issues))

    def test_room_overlap_is_removed(self):
        result = validate_completion(completion([{"id": "room1", "type": "room", "label": "bedroom", "center": [1, 0, 0], "dimensions": [2, 2, 2]}]), OBSERVED)
        self.assertEqual(result.removed_nodes, ["room1"])
        self.assertTrue(any(issue.code == "room_overlap" for issue in result.issues))

    def test_edge_derived_parent_is_checked_for_impassable_crossing(self):
        result = validate_completion(
            completion(
                [{"id": "chair", "type": "object", "label": "chair", "center": [4.6, 0, 0], "dimensions": [0.2, 0.2, 0.2]}],
                [{"source": "chair", "target": "room0"}],
            ),
            OBSERVED,
        )
        self.assertEqual(result.removed_nodes, ["chair"])
        self.assertTrue(any(issue.code == "impassable_crossing" for issue in result.issues))

    def test_room_edge_is_checked_for_impassable_crossing(self):
        observed = {
            "nodes": [
                {"id": "room0", "type": "room", "label": "living", "center": [0, 0, 0], "dimensions": [6, 3, 10], "observed": True},
                {"id": "wall0", "type": "structure", "label": "wall", "center": [4, 0, 0], "dimensions": [0.2, 3, 10], "observed": True},
            ],
            "edges": [],
        }
        text = "```yaml\n" + json.dumps({
            "nodes": observed["nodes"] + [{"id": "bedroom", "type": "room", "label": "bedroom", "center": [4.6, 0, 0], "dimensions": [1, 2, 1]}],
            "edges": [{"source": "bedroom", "target": "room0"}],
        }) + "\n```"
        result = validate_completion(
            text,
            observed,
        )
        self.assertEqual(result.removed_nodes, ["bedroom"])
        self.assertTrue(any(issue.code == "impassable_crossing" for issue in result.issues))

    def test_structure_labeled_door_opens_impassable_crossing(self):
        observed = {
            "nodes": OBSERVED["nodes"] + [{"id": "door0", "type": "structure", "label": "door", "center": [4, 0, 2], "dimensions": [0.5, 3, 1], "observed": True}],
            "edges": [],
        }
        text = "```yaml\n" + json.dumps({
            "nodes": observed["nodes"] + [{"id": "chair", "type": "object", "label": "chair", "center": [4.6, 0, 2], "dimensions": [0.2, 0.2, 0.2], "room_id": "room0"}],
            "edges": [],
        }) + "\n```"
        result = validate_completion(text, observed)
        self.assertEqual(result.removed_nodes, [])

    def test_frontier_fallback_exposes_free_space_faces(self):
        observed = {
            "nodes": OBSERVED["nodes"] + [{"id": "free0", "type": "nothing", "label": "free", "center": [0, 0, 0], "dimensions": [2, 2, 4], "observed": True}],
            "edges": [],
        }
        fallback = validate_ensemble(["bad"], observed)[-1].graph["frontier_fallback"]
        self.assertEqual(fallback["strategy"], "geometric")
        self.assertEqual(len(fallback["candidates"]), 4)

    def test_forbidden_new_structure_is_removed(self):
        result = validate_completion(completion([{"id": "newwall", "type": "structure", "label": "wall", "center": [0, 0, 0], "dimensions": [1, 1, 1]}]), OBSERVED)
        self.assertEqual(result.removed_nodes, ["newwall"])

    def test_validator_functions_never_take_a_reference_graph(self):
        """Structural guard, not discipline: fails the moment anyone adds a
        reference/ground-truth/gt parameter to either validation entry
        point, per IMPLEMENTATION_RESEARCH.md section 4.1's "reference
        ground truth is permitted only for post-hoc labels, never for
        online validation decisions." Post-hoc labeling has its own
        explicit function (label_against_reference) below - if a reference
        graph is ever needed inside validate_completion/validate_ensemble
        itself, that is the leak this test exists to catch."""
        banned_substrings = ("reference", "ground_truth", "gt_graph", " gt", "_gt")
        for fn in (validate_completion, validate_ensemble):
            params = list(inspect.signature(fn).parameters)
            offending = [p for p in params if any(b in p.lower() for b in banned_substrings)]
            self.assertEqual(offending, [], f"{fn.__name__} must not accept a reference-graph-shaped parameter: {offending}")

    def test_label_against_reference_is_post_hoc_and_does_not_change_the_result(self):
        result = validate_completion(completion([{"id": "chair", "type": "object", "label": "chair", "center": [0, 0, 0], "dimensions": [1, 1, 1], "room_id": "room0"}]), OBSERVED)
        self.assertEqual(result.removed_nodes, [])  # unaffected by any reference graph

        # The rejected node below sits at [4, 0, 0] (that's why it's rejected -
        # it overlaps wall0) - "close" must be close to that position, not to
        # the unrelated accepted-completion fixture above.
        reference_close = {"nodes": [{"id": "ref_chair", "type": "object", "label": "chair", "center": [4.1, 0, 0], "dimensions": [1, 1, 1]}], "edges": []}
        reference_far = {"nodes": [{"id": "ref_chair", "type": "object", "label": "chair", "center": [50, 0, 0], "dimensions": [1, 1, 1]}], "edges": []}

        # No issues were raised for an accepted completion, so labeling is a no-op here -
        # exercise it against a rejecting completion instead, where issues exist to label.
        rejecting = completion([{"id": "chair", "type": "object", "label": "chair", "center": [4, 0, 0], "dimensions": [1, 1, 1], "room_id": "room0"}])
        rejected_result = validate_completion(rejecting, OBSERVED)
        self.assertEqual(rejected_result.removed_nodes, ["chair"])

        labeled_close = label_against_reference(rejecting, rejected_result.issues, reference_close)
        labeled_far = label_against_reference(rejecting, rejected_result.issues, reference_far)
        self.assertTrue(any(i.reference_match for i in labeled_close))
        self.assertFalse(any(i.reference_match for i in labeled_far))
        # Confirm the original (pre-labeling) issues were never mutated in place.
        self.assertTrue(all(i.reference_match is None for i in rejected_result.issues))

    def test_reference_labels_are_one_to_one_and_case_insensitive(self):
        text = completion([
            {"id": "chair_a", "type": "object", "label": "Chair", "center": [4, 0, 0], "dimensions": [1, 1, 1], "room_id": "room0"},
            {"id": "chair_b", "type": "object", "label": "chair", "center": [4.2, 0, 0], "dimensions": [1, 1, 1], "room_id": "room0"},
        ])
        reference = {"nodes": [{"id": "ref", "type": "object", "label": "chair", "center": [4.1, 0, 0], "dimensions": [1, 1, 1]}], "edges": []}
        issues = [ValidationIssue("aabb_conflict", "x", "chair_a"), ValidationIssue("aabb_conflict", "x", "chair_b")]
        labeled = label_against_reference(text, issues, reference)
        self.assertEqual(sum(bool(issue.reference_match) for issue in labeled), 1)


class CalibrationAndScoreTests(unittest.TestCase):
    def test_isotonic_map_is_monotone(self):
        calibrator = IsotonicCalibrator([0.0, 0.5, 1.0], [1, 0, 1])
        self.assertLessEqual(calibrator(0), calibrator(0.5))
        self.assertLessEqual(calibrator(0.5), calibrator(1))

    def test_leave_one_scene_out_uses_other_scenes(self):
        folds = fit_leave_one_scene_out({"a": [(0.0, 0), (1.0, 1)], "b": [(0.5, 1)], "c": [(0.2, 0)]})
        self.assertEqual(set(folds), {"a", "b", "c"})
        self.assertEqual(len(folds["b"].predictions), 1)

    def test_held_out_scene_never_tunes_its_own_calibrator(self):
        """Per IMPLEMENTATION_RESEARCH.md section 4.5: each reported scene's
        calibrator is fit on the OTHER three scenes only. With only two
        scenes it's easy to get this subtly backwards (e.g. by fitting on
        everything, or on the held-out scene by accident) - construct
        samples where scene 'a' and scene 'b' would produce very different
        calibrators if either saw its own data, and confirm each fold's
        calibrator matches training on the OTHER scene only."""
        samples = {
            "a": [(0.0, 0), (0.1, 0), (0.2, 0)],  # if leaked in, would pull the map toward 0
            "b": [(0.0, 1), (0.1, 1), (0.2, 1)],  # if leaked in, would pull the map toward 1
        }
        folds = fit_leave_one_scene_out(samples)
        expected_for_a = IsotonicCalibrator(*zip(*samples["b"]))
        expected_for_b = IsotonicCalibrator(*zip(*samples["a"]))
        for x in (0.0, 0.1, 0.2):
            self.assertEqual(folds["a"].calibrator(x), expected_for_a(x))
            self.assertEqual(folds["b"].calibrator(x), expected_for_b(x))
        # And the held-out scene's own labels must differ from what its
        # "leaked" calibrator would have predicted, or this test wouldn't
        # actually be distinguishing the two cases.
        self.assertNotEqual(folds["a"].calibrator(0.0), IsotonicCalibrator(*zip(*samples["a"]))(0.0))

    def test_risk_is_mean_and_zero_for_no_visible_predictions(self):
        no_risk = score_viewpoint(object_gain=1, room_gain=0, distance_m=0, visible_predictions=[], beta=3)
        risk = score_viewpoint(object_gain=1, room_gain=0, distance_m=0, visible_predictions=[0.0, 1.0], beta=2)
        self.assertEqual(no_risk, 1.0)
        self.assertEqual(risk, 0.0)


class EvaluatorTests(unittest.TestCase):
    def test_author_graph_adapter_normalizes_vectors_and_parent_edges(self):
        graph = normalize_author_graph({
            "nodes": [
                {"id": 1, "node_type": "room", "name": "living", "position": "[0, 0, 0]", "is_predicted": False},
                {"id": 2, "node_type": "object", "name": "chair", "position": "[1, 0, 0]", "dimension": "[1, 1, 1]", "is_predicted": True},
            ],
            "edges": [[2, 1]],
        })
        self.assertEqual(graph["nodes"][1]["id"], 2)
        self.assertEqual(graph["nodes"][1]["center"], [1.0, 0.0, 0.0])
        self.assertEqual(graph["nodes"][1]["room_id"], 1)
        self.assertEqual(graph["edges"], [{"source": 2, "target": 1}])

    def test_matching_thresholds_and_normalized_ged(self):
        reference = {"nodes": [{"id": "r", "type": "room", "label": "living", "center": [0, 0, 0], "dimensions": [5, 3, 5]}, {"id": "o", "type": "object", "label": "chair", "center": [1, 0, 0], "dimensions": [1, 1, 1]}], "edges": [{"source": "o", "target": "r"}]}
        predicted = {"nodes": [{"id": "r2", "type": "room", "label": "living", "center": [3, 0, 0], "dimensions": [5, 3, 5]}, {"id": "o2", "type": "object", "label": "chair", "center": [1.2, 0, 0], "dimensions": [1, 1, 1]}], "edges": [{"source": "o2", "target": "r2"}]}
        metrics = evaluate_graph(predicted, reference)
        self.assertEqual(metrics["object_f1"], 1.0)
        self.assertEqual(metrics["ged"], 0.0)

    def test_run_reads_checkpoint_graphs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "graphs").mkdir()
            graph = {"nodes": [], "edges": []}
            (root / "graphs" / "000.json").write_text(json.dumps({"path_m": 0, "graph": graph}))
            self.assertEqual(evaluate_run(root, graph)[0]["checkpoint"], 0)

    def test_path_auc_is_budget_normalized(self):
        rows = [{"path_m": 0, "object_f1": 0.0}, {"path_m": 10, "object_f1": 1.0}, {"path_m": 20, "object_f1": 1.0}]
        self.assertAlmostEqual(area_under_curve(rows, "object_f1", budget_m=20), 0.75)

    def test_path_auc_ignores_rows_beyond_budget(self):
        rows = [{"path_m": 0, "object_f1": 0.0}, {"path_m": 120, "object_f1": 1.0}, {"path_m": 240, "object_f1": 1.0}]
        self.assertAlmostEqual(area_under_curve(rows, "object_f1", budget_m=120), 0.5)


if __name__ == "__main__":
    unittest.main()
