from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from asp_offline.calibration import IsotonicCalibrator, fit_leave_one_scene_out
from asp_offline.evaluator import area_under_curve, evaluate_graph, evaluate_run
from asp_offline.scoring import score_viewpoint
from asp_offline.validator import validate_completion, validate_ensemble


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

    def test_forbidden_new_structure_is_removed(self):
        result = validate_completion(completion([{"id": "newwall", "type": "structure", "label": "wall", "center": [0, 0, 0], "dimensions": [1, 1, 1]}]), OBSERVED)
        self.assertEqual(result.removed_nodes, ["newwall"])


class CalibrationAndScoreTests(unittest.TestCase):
    def test_isotonic_map_is_monotone(self):
        calibrator = IsotonicCalibrator([0.0, 0.5, 1.0], [1, 0, 1])
        self.assertLessEqual(calibrator(0), calibrator(0.5))
        self.assertLessEqual(calibrator(0.5), calibrator(1))

    def test_leave_one_scene_out_uses_other_scenes(self):
        folds = fit_leave_one_scene_out({"a": [(0.0, 0), (1.0, 1)], "b": [(0.5, 1)], "c": [(0.2, 0)]})
        self.assertEqual(set(folds), {"a", "b", "c"})
        self.assertEqual(len(folds["b"].predictions), 1)

    def test_risk_is_mean_and_zero_for_no_visible_predictions(self):
        no_risk = score_viewpoint(object_gain=1, room_gain=0, distance_m=0, visible_predictions=[], beta=3)
        risk = score_viewpoint(object_gain=1, room_gain=0, distance_m=0, visible_predictions=[0.0, 1.0], beta=2)
        self.assertEqual(no_risk, 1.0)
        self.assertEqual(risk, 0.0)


class EvaluatorTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
