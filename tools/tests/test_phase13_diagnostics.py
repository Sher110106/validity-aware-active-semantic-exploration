from __future__ import annotations

import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

from phase13_diagnostics import (
    brier_score,
    build_calibration_diagnostics,
    calibration_metrics,
    collect_validation_diagnostics,
    aggregate_validation_diagnostics,
    evaluate_guardrails,
    pairwise_jaccard_diversity,
    parse_live_run_diagnostics,
    reliability_bins,
    render_reliability_svg,
)


class CalibrationMetricTests(unittest.TestCase):
    def test_brier_score_matches_known_example(self):
        self.assertAlmostEqual(
            brier_score([0.0, 0.25, 0.75, 1.0], [0, 1, 0, 1]),
            (0.0 + 0.75**2 + 0.75**2 + 0.0) / 4,
        )

    def test_reliability_bins_use_fixed_width_and_include_one_in_last_bin(self):
        bins = reliability_bins([0.0, 0.1, 0.999, 1.0], [0, 1, 1, 0], n_bins=10)
        self.assertEqual(bins[0]["count"], 1)
        self.assertEqual(bins[1]["count"], 1)
        self.assertEqual(bins[9]["count"], 2)
        self.assertAlmostEqual(bins[9]["mean_prediction"], 0.9995)
        self.assertAlmostEqual(bins[9]["fraction_positive"], 0.5)

    def test_calibration_metrics_report_standard_weighted_ece(self):
        metrics = calibration_metrics([0.05, 0.15, 0.95], [0, 1, 1], n_bins=10)
        expected_ece = (abs(0.05 - 0.0) + abs(0.15 - 1.0) + abs(0.95 - 1.0)) / 3
        self.assertAlmostEqual(metrics["ece"], expected_ece)
        self.assertEqual(metrics["n"], 3)
        self.assertEqual(metrics["positives"], 2)

    def test_empty_calibration_subset_is_explicitly_unavailable(self):
        metrics = calibration_metrics([], [], n_bins=10)
        self.assertEqual(metrics["status"], "unavailable_no_samples")
        self.assertIsNone(metrics["brier"])
        self.assertIsNone(metrics["ece"])

    def test_training_prevalence_baseline_uses_only_other_scenes(self):
        diagnostics = build_calibration_diagnostics(
            {
                "positive_scene": [(0.5, 1, "object"), (1.0, 1, "object")],
                "negative_scene": [(0.5, 0, "object"), (1.0, 0, "object")],
            }
        )
        positive_fold = diagnostics["per_scene"]["positive_scene"]["subsets"]["object"]
        negative_fold = diagnostics["per_scene"]["negative_scene"]["subsets"]["object"]
        self.assertEqual(positive_fold["training_prevalence"], 0.0)
        self.assertEqual(negative_fold["training_prevalence"], 1.0)
        self.assertEqual(positive_fold["training_prevalence_baseline"]["brier"], 1.0)
        self.assertEqual(negative_fold["training_prevalence_baseline"]["brier"], 1.0)


class DiversityTests(unittest.TestCase):
    def test_pairwise_jaccard_diversity_uses_semantic_sets(self):
        sets = [{("object", "chair"), ("object", "table")}, {("object", "chair")}, set()]
        # Pair distances: 1/2, 1, 1.
        self.assertAlmostEqual(pairwise_jaccard_diversity(sets), 5 / 6)

    def test_aggregate_diversity_weights_only_defined_tracks(self):
        def scene(mean_before, mean_after, defined):
            return {
                "aggregate": {
                    "defined_diversity_tracks_before": defined,
                    "defined_diversity_tracks_after": defined,
                    "mean_pairwise_semantic_jaccard_diversity_before": mean_before,
                    "mean_pairwise_semantic_jaccard_diversity_after": mean_after,
                },
                "issue_counts": {},
                "stage_tracks": 1000,
            }

        result = aggregate_validation_diagnostics(
            {"a": scene(0.2, 0.4, 1), "b": scene(0.8, 0.6, 3)}
        )
        self.assertAlmostEqual(result["aggregate"]["mean_pairwise_semantic_jaccard_diversity_before"], 0.65)
        self.assertAlmostEqual(result["aggregate"]["mean_pairwise_semantic_jaccard_diversity_after"], 0.55)
        self.assertEqual(result["aggregate"]["defined_diversity_tracks_before"], 4)
        self.assertEqual(result["aggregate"]["defined_diversity_tracks_after"], 4)

    @unittest.skipUnless(importlib.util.find_spec("yaml"), "real author-artifact adapter requires PyYAML")
    def test_validation_diagnostics_keep_missing_slots_in_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / "run" / "stages" / "0"
            stage.mkdir(parents=True)
            observed = {
                "nodes": [
                    {
                        "id": 1,
                        "node_type": "room",
                        "name": "living",
                        "position": "[0, 0, 0]",
                    }
                ],
                "edges": [],
            }
            reference = {
                "nodes": observed["nodes"]
                + [
                    {
                        "id": 2,
                        "node_type": "object",
                        "name": "chair",
                        "position": "[1, 0, 0]",
                        "dimension": "[1, 1, 1]",
                    }
                ],
                "edges": [[2, 1]],
            }
            completion = {
                "nodes": observed["nodes"]
                + [
                    {
                        "id": 10,
                        "node_type": "object",
                        "name": "chair",
                        "position": "[1.1, 0, 0]",
                        "dimension": "[1, 1, 1]",
                        "is_predicted": True,
                    },
                    {
                        "id": 11,
                        "node_type": "object",
                        "name": "lamp",
                        "position": "[2, 0, 0]",
                        "is_predicted": True,
                    },
                ],
                "edges": [[10, 1], [11, 1]],
            }
            (stage / "habitat_scene_graph_original_graph0.yaml").write_text(json.dumps(observed))
            (stage / "habitat_scene_graph_new_graph_0.yaml").write_text(json.dumps(completion))
            (stage / "path_log.json").write_text(json.dumps({"final_path": [[0, 0, 0]]}))
            (stage / "navigation_stats.json").write_text(
                json.dumps({"total_path_length_meters": 1.0})
            )
            reference_path = root / "reference.yaml"
            reference_path.write_text(json.dumps(reference))

            result = collect_validation_diagnostics(root / "run", reference_path)

            aggregate = result["aggregate"]
        self.assertEqual(aggregate["expected_completions"], 4)
        self.assertEqual(aggregate["available_completions"], 1)
        self.assertEqual(aggregate["missing_completions"], 3)
        self.assertEqual(aggregate["predicted_nodes"], 2)
        self.assertEqual(aggregate["surviving_predicted_nodes"], 1)
        self.assertEqual(aggregate["object_true_positive_retention"], 1.0)
        self.assertEqual(aggregate["object_false_positive_removal_rate"], 1.0)
        self.assertEqual(aggregate["accepted_completion_rate_of_expected"], 0.25)

    @unittest.skipUnless(importlib.util.find_spec("yaml"), "real author-artifact adapter requires PyYAML")
    def test_validation_recomputes_matching_after_removing_closest_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / "run" / "stages" / "0"
            stage.mkdir(parents=True)
            observed = {"nodes": [{"id": 1, "node_type": "room", "name": "living", "position": "[0, 0, 0]"}], "edges": []}
            reference = {"nodes": observed["nodes"] + [{"id": 2, "node_type": "object", "name": "chair", "position": "[1, 0, 0]", "dimension": "[1, 1, 1]"}], "edges": [[2, 1]]}
            completion = {
                "nodes": observed["nodes"] + [
                    # Closest duplicate: invalid because its dimension is absent.
                    {"id": 10, "node_type": "object", "name": "chair", "position": "[1, 0, 0]", "is_predicted": True},
                    # Valid duplicate remains within the evaluator's matching radius.
                    {"id": 11, "node_type": "object", "name": "chair", "position": "[1.4, 0, 0]", "dimension": "[1, 1, 1]", "is_predicted": True},
                ],
                "edges": [[10, 1], [11, 1]],
            }
            (stage / "habitat_scene_graph_original_graph0.yaml").write_text(json.dumps(observed))
            (stage / "habitat_scene_graph_new_graph_0.yaml").write_text(json.dumps(completion))
            (stage / "path_log.json").write_text(json.dumps({"final_path": [[0, 0, 0]]}))
            (stage / "navigation_stats.json").write_text(json.dumps({"total_path_length_meters": 1.0}))
            reference_path = root / "reference.yaml"
            reference_path.write_text(json.dumps(reference))
            result = collect_validation_diagnostics(root / "run", reference_path)

        aggregate = result["aggregate"]
        self.assertEqual(aggregate["object_true_positives_before"], 1)
        self.assertEqual(aggregate["object_true_positives_after"], 1)
        self.assertEqual(aggregate["object_true_positive_retention"], 1.0)
        self.assertEqual(aggregate["object_predicted_nodes_before"], 2)
        self.assertEqual(aggregate["object_predicted_nodes_after"], 1)
        self.assertEqual(aggregate["object_false_positives_before"], 1)
        self.assertEqual(aggregate["object_false_positives_after"], 0)
        self.assertEqual(aggregate["object_false_positive_removal_rate"], 1.0)


class GuardrailTests(unittest.TestCase):
    def test_guardrail_passes_static_thresholds_but_fails_closed_without_detours(self):
        static_results = {
            "00069": {
                "path_normalized_auc_capped_budget_m": 120.0,
                "path_normalized_auc_capped": {
                    "official": {"object_f1": 0.50, "normalized_ged": 1.00},
                    "filter_plus_support_threshold_calibrated_tau_1.0": {
                        "object_f1": 0.48,
                        "normalized_ged": 1.09,
                    },
                },
            }
        }
        validation = {"aggregate": {"structurally_invalid_predicted_nodes": 4}}
        result = evaluate_guardrails(static_results, validation)

        self.assertTrue(result["static_quality_gate"]["passed"])
        self.assertTrue(result["invalid_hypothesis_gate"]["passed"])
        self.assertEqual(result["false_positive_detour_gate"]["status"], "not_identifiable")
        self.assertFalse(result["combined_usefulness_claim"]["passed"])
        self.assertEqual(
            result["combined_usefulness_claim"]["status"],
            "not_established_missing_required_trajectory_outcome",
        )

    def test_guardrail_thresholds_are_inclusive_and_checked_per_scene(self):
        static_results = {
            "a": {
                "path_normalized_auc_capped_budget_m": 120.0,
                "path_normalized_auc_capped": {
                    "official": {"object_f1": 0.50, "normalized_ged": 1.00},
                    "filter_plus_support_threshold_calibrated_tau_1.0": {
                        "object_f1": 0.45,
                        "normalized_ged": 1.10,
                    },
                },
            },
            "b": {
                "path_normalized_auc_capped_budget_m": 120.0,
                "path_normalized_auc_capped": {
                    "official": {"object_f1": 0.50, "normalized_ged": 1.00},
                    "filter_plus_support_threshold_calibrated_tau_1.0": {
                        "object_f1": 0.449,
                        "normalized_ged": 1.00,
                    },
                },
            },
        }
        result = evaluate_guardrails(
            static_results,
            {"aggregate": {"structurally_invalid_predicted_nodes": 1}},
        )
        self.assertTrue(result["per_scene"]["a"]["f1_passed"])
        self.assertTrue(result["per_scene"]["a"]["ged_passed"])
        self.assertFalse(result["per_scene"]["b"]["f1_passed"])
        self.assertFalse(result["static_quality_gate"]["passed"])


class LiveArtifactTests(unittest.TestCase):
    def test_planner_failures_are_not_mislabeled_as_robot_collisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "logs").mkdir()
            (run / "prompts").mkdir()
            (run / "stages" / "0").mkdir(parents=True)
            (run / "logs" / "exploration_pipeline.log").write_text(
                "A* search failed to find a mid path.\n"
                "Received empty mid-level path.\n"
                "LLM says collision_count = 2.\n"
            )
            (run / "prompts" / "_call_counter").write_text("7\n")
            (run / "prompts" / "prompts_responses.jsonl").write_text(
                json.dumps({"duration_s": 2.5}) + "\n" + json.dumps({"duration_s": 1.0}) + "\n"
            )
            (run / "stages" / "0" / "navigation_stats.json").write_text(
                json.dumps({"total_path_length_meters": 3.5})
            )

            result = parse_live_run_diagnostics(run)

        self.assertEqual(result["planner_failures"]["astar_failed"], 1)
        self.assertEqual(result["planner_failures"]["empty_mid_level_path"], 1)
        self.assertEqual(result["robot_collisions"]["status"], "not_instrumented")
        self.assertIsNone(result["robot_collisions"]["count"])
        self.assertEqual(result["api_calls"]["counter"], 7)
        self.assertEqual(result["api_calls"]["logged_records"], 2)
        self.assertEqual(result["api_calls"]["aggregate_request_seconds"], 3.5)

    def test_reliability_svg_is_deterministic_and_labels_both_series(self):
        panels = {
            "pooled": {
                "raw": calibration_metrics([0.2, 0.8], [0, 1]),
                "calibrated": calibration_metrics([0.1, 0.9], [0, 1]),
            }
        }
        first = render_reliability_svg(panels, title="Test reliability")
        second = render_reliability_svg(panels, title="Test reliability")
        self.assertEqual(first, second)
        self.assertIn("Raw support", first)
        self.assertIn("LOSO calibrated", first)
        self.assertIn("Perfect calibration", first)


if __name__ == "__main__":
    unittest.main()
