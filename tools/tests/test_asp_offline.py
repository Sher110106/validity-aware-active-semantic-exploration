from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from asp_offline.calibration import IsotonicCalibrator, fit_leave_one_scene_out, label_hypotheses_against_reference
from asp_offline.author_io import normalize_author_graph
from asp_offline.evaluator import area_under_curve, evaluate_graph, evaluate_run
from asp_offline.models import Hypothesis, ValidationIssue
from asp_offline.scoring import score_viewpoint
from asp_offline.support_policy import fit_loso_calibrator, support_filtered_graph, support_scores
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

    def test_room_without_dimensions_is_accepted_but_object_still_needs_them(self):
        """2026-09-15 bug fix: predicted rooms in this pipeline's own wire
        format NEVER carry a `dimension` field (confirmed on real data,
        including the pipeline's own observed graphs). A room with no
        `dimensions` key has aabb(node)=None, so room_overlap already
        skips it gracefully ("box is None: continue") regardless of
        position - it must be accepted on center alone, not rejected by
        finite_geometry. A predicted OBJECT without dimensions must still
        be rejected - this fix is scoped to rooms only, not a blanket
        relaxation of the geometry requirement."""
        no_dims_room = completion([{"id": "bedroom1", "type": "room", "label": "bedroom", "center": [1, 0, 0]}])
        result = validate_completion(no_dims_room, OBSERVED)
        self.assertTrue(result.accepted)
        self.assertNotIn("bedroom1", result.removed_nodes)

        no_dims_object = completion([{"id": "chair", "type": "object", "label": "chair", "center": [0, 0, 0], "room_id": "room0"}])
        result = validate_completion(no_dims_object, OBSERVED)
        self.assertEqual(result.removed_nodes, ["chair"])
        self.assertTrue(any(issue.code == "finite_geometry" for issue in result.issues))

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

    def test_isotonic_calibrator_pools_tied_x_before_fitting(self):
        """2026-09-15 regression: support only takes a handful of discrete
        values under a fixed K=4 denominator (deviation #56), so most real
        calibration samples share the exact same x. The un-pooled bug built
        one singleton block per SAMPLE and only merged on a strict decrease
        between adjacent (x, y)-sorted blocks - within a tie group sorted
        y-ascending (zeros then the one 1), nothing ever decreased, so
        predict() returned whichever tied block sorted first (a 0), not the
        group's true empirical mean. Pooling identical x into one weighted
        block before PAVA fixes this - assert the pooled mean, not 0.0."""
        x = [0.25] * 10
        y = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        calibrator = IsotonicCalibrator(x, y)
        self.assertAlmostEqual(calibrator(0.25), 0.1)

    def test_label_hypotheses_uses_predicted_order_not_distance_sorted(self):
        """Advisor-reviewed design decision: the calibration label must use
        match_objects' own predicted-input-order greedy (the author-
        faithful tools/evaluator/matching.py's algorithm), not the global-
        distance-sorted greedy asp_offline's own _match_nodes uses
        elsewhere for a different purpose (cross-completion support).
        Construct a case where the two disagree: two hypotheses compete for
        the SAME single reference node. Global-distance-sorted greedy would
        award it to whichever hypothesis is objectively closer (the second
        one here); predicted-order greedy awards it to whichever comes
        FIRST in the input list, even though the second is closer - this
        pins the intended algorithm, not just "some" one-to-one matching."""
        reference = {"nodes": [{"id": "r1", "type": "object", "label": "chair", "center": [0, 0, 0], "dimensions": [1, 1, 1]}], "edges": []}
        first_but_farther = Hypothesis("chair", None, [0.3, 0, 0], kind="object")
        second_but_closer = Hypothesis("chair", None, [0.1, 0, 0], kind="object")
        labels = label_hypotheses_against_reference([first_but_farther, second_but_closer], reference, object_threshold=0.5)
        self.assertEqual(labels, [1, 0])

    def test_label_hypotheses_strict_threshold_boundary(self):
        reference = {"nodes": [{"id": "r1", "type": "object", "label": "chair", "center": [0, 0, 0], "dimensions": [1, 1, 1]}], "edges": []}
        exactly_at_threshold = Hypothesis("chair", None, [0.5, 0, 0], kind="object")
        labels = label_hypotheses_against_reference([exactly_at_threshold], reference, object_threshold=0.5)
        self.assertEqual(labels, [0])  # strict '<', matching match_objects exactly - not '<='

    def test_label_hypotheses_ignores_parent_room(self):
        """Parent-room CANNOT be checked against the reference: it's a raw
        per-graph integer id with no shared namespace between an
        independent frontier-baseline reference run and a completion's own
        observed graph (confirmed on real data in the advisor review -
        scene 00069's reference rooms are ids 206-214, its completions'
        rooms are ids 101-110, zero overlap). A hypothesis must match on
        label+distance alone regardless of parent_room mismatch."""
        reference = {"nodes": [{"id": "r1", "type": "object", "label": "chair", "center": [0, 0, 0], "dimensions": [1, 1, 1]}], "edges": []}
        mismatched_parent = Hypothesis("chair", "some_unrelated_room_id", [0.1, 0, 0], kind="object")
        labels = label_hypotheses_against_reference([mismatched_parent], reference, object_threshold=0.5)
        self.assertEqual(labels, [1])


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

    def test_edge_match_survives_reversed_lexical_order_after_id_mapping(self):
        # Regression test for REVIEW_2026-09-14.md's "canonicalize mapped
        # predicted edges" finding: predicted ids "p1" < "p9" sort one way,
        # but their reference-space mapping ("z2", "a1") sorts the other way
        # ("a1" < "z2"). Before the fix, the mapped edge tuple kept the
        # predicted-space order and never matched the reference's own
        # sorted tuple, so a real shared edge was double-counted as one
        # insertion and one deletion.
        reference = {
            "nodes": [
                {"id": "a1", "type": "room", "label": "living", "center": [0, 0, 0], "dimensions": [5, 3, 5]},
                {"id": "z2", "type": "object", "label": "chair", "center": [1, 0, 0], "dimensions": [1, 1, 1]},
            ],
            "edges": [{"source": "z2", "target": "a1"}],
        }
        predicted = {
            "nodes": [
                {"id": "p9", "type": "room", "label": "living", "center": [0, 0, 0], "dimensions": [5, 3, 5]},
                {"id": "p1", "type": "object", "label": "chair", "center": [1, 0, 0], "dimensions": [1, 1, 1]},
            ],
            "edges": [{"source": "p1", "target": "p9"}],
        }
        metrics = evaluate_graph(predicted, reference)
        self.assertEqual(metrics["ged"], 0.0)


class SupportPolicyTests(unittest.TestCase):
    """IMPLEMENTATION_PLAN.md section 17 step 2's support-threshold-only and
    filter+support-threshold ablation variants (extension_policy_replay.py).
    Most tests here use calibrator=None (raw, uncalibrated support) since
    that's the control every fitted calibrator must beat; the calibrator
    parameter itself (added 2026-09-15, after the first real leave-one-
    scene-out fit - DEVIATIONS.md #61) is covered separately below."""

    OBSERVED = {"nodes": [{"id": "room0", "type": "room", "label": "living", "center": [0, 0, 0], "dimensions": [10, 3, 10], "observed": True}], "edges": []}

    def _completion(self, node):
        return {"nodes": self.OBSERVED["nodes"] + [node], "edges": []}

    def test_well_agreed_node_survives_a_mid_threshold(self):
        chair_a = self._completion({"id": "chair_a", "type": "object", "label": "chair", "center": [1, 1, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        chair_b = self._completion({"id": "chair_b", "type": "object", "label": "chair", "center": [1.1, 1, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        lamp = self._completion({"id": "lamp_a", "type": "object", "label": "lamp", "center": [5, 5, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        ensemble = [chair_a, chair_b, lamp]

        chair_support = support_scores(chair_a, ensemble, expected_size=3)
        self.assertAlmostEqual(chair_support[0].support, 2 / 3)
        self.assertEqual(chair_support[0].hits, 2)
        lamp_support = support_scores(lamp, ensemble, expected_size=3)
        self.assertAlmostEqual(lamp_support[0].support, 1 / 3)
        self.assertEqual(lamp_support[0].hits, 1)

    def test_threshold_between_the_two_supports_separates_them(self):
        chair_a = self._completion({"id": "chair_a", "type": "object", "label": "chair", "center": [1, 1, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        chair_b = self._completion({"id": "chair_b", "type": "object", "label": "chair", "center": [1.1, 1, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        lamp = self._completion({"id": "lamp_a", "type": "object", "label": "lamp", "center": [5, 5, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        ensemble = [chair_a, chair_b, lamp]

        kept_chair = support_filtered_graph(self.OBSERVED, chair_a, ensemble, tau=0.5, expected_size=3)
        self.assertIn("chair_a", {n["id"] for n in kept_chair["nodes"]})

        dropped_lamp = support_filtered_graph(self.OBSERVED, lamp, ensemble, tau=0.5, expected_size=3)
        self.assertNotIn("lamp_a", {n["id"] for n in dropped_lamp["nodes"]})
        self.assertEqual(dropped_lamp["support_threshold"], {"tau": 0.5, "calibrated": False, "expected_size": 3, "available": 3, "missing": 0, "kept": 0, "dropped": 1})

    def test_tau_zero_keeps_every_predicted_node(self):
        lamp = self._completion({"id": "lamp_a", "type": "object", "label": "lamp", "center": [5, 5, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        graph = support_filtered_graph(self.OBSERVED, lamp, [lamp], tau=0.0, expected_size=1)
        self.assertIn("lamp_a", {n["id"] for n in graph["nodes"]})

    def test_missing_completions_do_not_inflate_support(self):
        # Regression test for REVIEW_2026-09-14.md's denominator finding:
        # 2 of the intended 4-member ensemble survived (the other 2 were
        # dropped upstream by the parse-failure guard, so they're simply
        # absent from `ensemble`, not present-but-empty). A node in both
        # surviving completions must score support 0.5 (2 of the intended
        # 4), never 1.0 (2 of the 2 that happened to survive).
        chair_a = self._completion({"id": "chair_a", "type": "object", "label": "chair", "center": [1, 1, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        chair_b = self._completion({"id": "chair_b", "type": "object", "label": "chair", "center": [1.1, 1, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        ensemble = [chair_a, chair_b]  # only 2 of the intended 4 survived

        scores = support_scores(chair_a, ensemble, expected_size=4)
        self.assertAlmostEqual(scores[0].support, 0.5)
        self.assertEqual(scores[0].hits, 2)

        kept_at_half = support_filtered_graph(self.OBSERVED, chair_a, ensemble, tau=0.5, expected_size=4)
        self.assertIn("chair_a", {n["id"] for n in kept_at_half["nodes"]})
        dropped_above_half = support_filtered_graph(self.OBSERVED, chair_a, ensemble, tau=0.75, expected_size=4)
        self.assertNotIn("chair_a", {n["id"] for n in dropped_above_half["nodes"]})

    def test_more_completions_than_expected_size_raises(self):
        chair_a = self._completion({"id": "chair_a", "type": "object", "label": "chair", "center": [1, 1, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        chair_b = self._completion({"id": "chair_b", "type": "object", "label": "chair", "center": [1.1, 1, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        with self.assertRaises(ValueError):
            support_scores(chair_a, [chair_a, chair_b], expected_size=1)

    def test_calibrator_relabels_the_threshold_but_cannot_reorder_it(self):
        """2026-09-15: calibrator support added to support_filtered_graph.
        Because a fitted calibrator is a monotone function over a small
        discrete support domain (5 values under K=4), it can only RELABEL
        which numeric tau selects a given support level - it cannot make
        any graph reachable that a raw-support tau couldn't already reach.
        Pin that guarantee directly: an inverted (monotone-decreasing-
        looking on the surface, but still non-decreasing after PAVA)
        calibrator must still keep exactly the same node the equivalent
        raw-support tau would."""
        chair_a = self._completion({"id": "chair_a", "type": "object", "label": "chair", "center": [1, 1, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        chair_b = self._completion({"id": "chair_b", "type": "object", "label": "chair", "center": [1.1, 1, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        lamp = self._completion({"id": "lamp_a", "type": "object", "label": "lamp", "center": [5, 5, 0], "dimensions": [1, 1, 1], "room_id": "room0"})
        ensemble = [chair_a, chair_b, lamp]

        # A calibrator that maps raw support 2/3 -> 0.9 (way above the raw
        # value) and 1/3 -> 0.1 (way below) - if calibration could reorder
        # anything, this would flip which node survives a mid threshold.
        def calibrator(support: float) -> float:
            return 0.9 if support >= 0.5 else 0.1

        raw_kept = support_filtered_graph(self.OBSERVED, chair_a, ensemble, tau=0.5, expected_size=3)
        calibrated_kept = support_filtered_graph(self.OBSERVED, chair_a, ensemble, tau=0.5, expected_size=3, calibrator=calibrator)
        self.assertEqual(
            {n["id"] for n in raw_kept["nodes"]},
            {n["id"] for n in calibrated_kept["nodes"]},
        )
        self.assertTrue(calibrated_kept["support_threshold"]["calibrated"])
        self.assertFalse(raw_kept["support_threshold"]["calibrated"])

    def test_fit_loso_calibrator_excludes_held_out_scene_and_stamps_real_status(self):
        """Audit finding H2 (REVIEW_2026-09-14.md): extension_policy_replay.py
        must fit a REAL calibrator, not stamp UNCALIBRATED_STATUS while
        claiming otherwise. This is a wiring test for fit_loso_calibrator
        itself (fit_leave_one_scene_out's exclusion logic is already covered
        by test_leave_one_scene_out_uses_other_scenes) - it fakes
        collect_calibration_samples so it runs without real run directories,
        and checks the held-out scene never enters training and the status
        dict carries real (non-placeholder) counts."""
        fake_samples = {
            "a": [(0.0, 0, "object"), (0.25, 0, "object"), (0.5, 1, "room"), (0.75, 1, "room")],
            "b": [(0.0, 0, "object"), (1.0, 1, "room")],
            "c": [(0.5, 0, "object"), (0.5, 0, "object"), (1.0, 1, "room")],
        }
        scene_configs = {s: {"run": f"/fake/{s}/stages", "reference": f"/fake/{s}/ref.yaml"} for s in fake_samples}

        def fake_collect(run, reference, **kwargs):
            scene = Path(run).parts[-2]
            return fake_samples[scene]

        with patch("asp_offline.support_policy.collect_calibration_samples", side_effect=fake_collect):
            calibrator, status = fit_loso_calibrator(scene_configs, "a")

        self.assertEqual(set(status["fitted_on_scenes"]), {"b", "c"})
        self.assertNotIn("a", status["fitted_on_scenes"])
        self.assertEqual(status["held_out_scene"], "a")
        self.assertTrue(status["held_out"])
        self.assertEqual(status["status"], "LOSO_CALIBRATED")
        self.assertEqual(status["loso_scenes_available"], 3)
        self.assertEqual(status["n_training_samples"], 5)  # len(b) + len(c)
        self.assertEqual(status["n_training_positives"], 2)  # one positive each in b and c
        # by_kind (audit finding H1): b/c each contribute one object sample
        # (both negative) and one room sample (both positive) - splitting
        # must attribute every training positive to "room", none to "object".
        self.assertEqual(status["by_kind"]["room"], {"n_training_samples": 2, "n_training_positives": 2})
        self.assertEqual(status["by_kind"]["object"], {"n_training_samples": 3, "n_training_positives": 0})
        self.assertLessEqual(calibrator(0.0), calibrator(1.0))

    def test_fit_loso_calibrator_rejects_unknown_held_out_scene(self):
        with self.assertRaises(ValueError):
            fit_loso_calibrator({"a": {"run": "x", "reference": "y"}}, "not_a_scene")


if __name__ == "__main__":
    unittest.main()
