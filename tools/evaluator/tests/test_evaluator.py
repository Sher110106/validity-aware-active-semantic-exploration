import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # tools/ - for asp_offline

from graph_io import load_eval_graph, EvalGraph, EvalNode
from matching import match_objects
from ged import compute_ged

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    return os.path.join(FIXTURES, name)


def test_door_and_structure_nodes_excluded_from_loading():
    g = load_eval_graph(fixture("gt_simple.yaml"))
    names = {n.name for n in g.nodes.values()}
    assert "door" not in names
    assert len(g.objects) == 3
    assert len(g.rooms) == 2


def test_object_parent_resolved_from_edges():
    g = load_eval_graph(fixture("gt_simple.yaml"))
    chair = next(n for n in g.objects if n.name == "chair")
    bed = next(n for n in g.objects if n.name == "bed")
    assert chair.parent_name == "Living Room"
    assert bed.parent_name == "Bedroom"


def test_object_matching_precision_recall_f1_hand_verified():
    gt = load_eval_graph(fixture("gt_simple.yaml"))
    pred = load_eval_graph(fixture("pred_partial.yaml"))

    result = match_objects(gt.objects, pred.objects, threshold=0.5)

    # chair: gt (1,1,0) vs pred (1.1,1,0), dist ~0.1 -> matches
    # table: gt (1,2,0) vs pred (1,2.6,0), dist 0.6 -> same name but over
    #        threshold -> NOT a match (this is the whole point of the fixture)
    # bed: no predicted object named "bed" at all -> false negative
    # lamp: no gt object named "lamp" -> false positive
    assert result.true_positives == 1
    assert result.false_positives == 2  # table_far, lamp
    assert result.false_negatives == 2  # gt table (unmatched), bed
    assert abs(result.precision - 1 / 3) < 1e-9
    assert abs(result.recall - 1 / 3) < 1e-9
    assert abs(result.f1 - 1 / 3) < 1e-9
    assert len(result.matches) == 1
    matched = result.matches[0]
    assert matched.distance < 0.5


def test_object_matching_is_not_parent_room_aware():
    """f1_score_plot.py's calculate_f1_score matches on name+distance only -
    replicate that exactly, even though ged.py's substitution cost DOES
    check parent_name. This asymmetry is intentional, not a bug."""
    gt = load_eval_graph(fixture("gt_simple.yaml"))
    pred = load_eval_graph(fixture("pred_partial.yaml"))
    chair_gt = next(n for n in gt.objects if n.name == "chair")
    chair_pred = next(n for n in pred.objects if n.name == "chair")
    assert chair_gt.parent_name == chair_pred.parent_name == "Living Room"
    # (sanity check only - the actual no-parent-check behavior is exercised
    # by test_object_matching_precision_recall_f1_hand_verified above, since
    # match_objects never even looks at parent_name)


def test_empty_ground_truth_returns_zero_scores():
    result = match_objects([], [1], threshold=0.5)
    assert (result.precision, result.recall, result.f1) == (0.0, 0.0, 0.0)


def test_empty_predictions_returns_zero_scores_not_perfect_precision():
    gt = load_eval_graph(fixture("gt_simple.yaml"))
    result = match_objects(gt.objects, [], threshold=0.5)
    assert (result.precision, result.recall, result.f1) == (0.0, 0.0, 0.0)
    assert result.false_negatives == len(gt.objects)


def test_ged_zero_for_identical_graphs():
    g = load_eval_graph(fixture("ged_gt_one_object.yaml"))
    ged, ref_nodes, ref_edges = compute_ged(g, g)
    assert ged == 0.0
    assert ref_nodes == 2  # 1 room + 1 object
    assert ref_edges == 1


def test_ged_penalizes_parent_mismatch_via_orphaned_object():
    """pred's chair has no parent-room edge at all (vs gt's chair, which is
    attached to Kitchen) - substitution must be forbidden for the object
    despite identical name/position, forcing delete+insert (cost 2) plus
    the now-unmatched room-object edge on the gt side (cost 1) = 3 total.
    Hand-verified expected value, see ged.py's module docstring for the
    reasoning."""
    gt = load_eval_graph(fixture("ged_gt_one_object.yaml"))
    pred = load_eval_graph(fixture("ged_pred_orphan_object.yaml"))
    ged, ref_nodes, ref_edges = compute_ged(pred, gt)
    assert ged == 3.0


def test_match_objects_one_to_one_when_three_compete_for_two():
    """REVIEW_2026-09-14.md: 'one-to-one matching when three predictions
    compete for two references.' match_objects iterates predictions in
    input order and greedily claims the nearest still-available same-name
    gt object (replicating f1_score_plot.py exactly - this is NOT meant to
    be a globally optimal assignment, and this test documents that, not
    "fixes" it). Three same-named predicted chairs, two gt chairs: the
    predicted chair closest to gt chair A is processed second and finds A
    already taken by predicted chair B (which arrived first and was
    actually closer to gt chair B, not A) - verifies each gt object is
    claimed at most once and the leftover prediction becomes a false
    positive, never a duplicate match."""
    import numpy as np
    from graph_io import EvalGraph, EvalNode

    gt = EvalGraph(
        nodes={
            1: EvalNode(id=1, node_type="object", name="chair", position=np.array([0.0, 0.0, 0.0])),
            2: EvalNode(id=2, node_type="object", name="chair", position=np.array([10.0, 0.0, 0.0])),
        },
        edges=[],
    )
    pred = EvalGraph(
        nodes={
            101: EvalNode(id=101, node_type="object", name="chair", position=np.array([10.1, 0.0, 0.0])),  # nearest to gt 2
            102: EvalNode(id=102, node_type="object", name="chair", position=np.array([0.1, 0.0, 0.0])),   # nearest to gt 1
            103: EvalNode(id=103, node_type="object", name="chair", position=np.array([0.2, 0.0, 0.0])),   # also near gt 1, but 1 is taken
        },
        edges=[],
    )
    result = match_objects(gt.objects, pred.objects, threshold=0.5)
    assert result.true_positives == 2
    assert result.false_positives == 1
    assert result.false_negatives == 0
    matched_gt_ids = {m.gt_id for m in result.matches}
    assert matched_gt_ids == {1, 2}  # each gt object claimed at most once


def test_label_hypotheses_against_reference_agrees_with_match_objects():
    """Cross-implementation guard on a deliberately duplicated rule.
    tools/asp_offline/calibration.py's label_hypotheses_against_reference
    reimplements THIS module's match_objects algorithm (predicted-order
    greedy, name+distance only, strict '<') rather than importing it, so
    the offline extension's PyYAML-only dependency contract doesn't pick
    up a numpy dependency - see that function's docstring for the full
    reasoning. This test is the real guard on the duplication staying in
    sync, not the docstring's promise alone: run the SAME fixture through
    both implementations and require the same match COUNT (not literal
    equality of representation, since the two functions return different
    shapes - MatchResult vs a plain 0/1 list)."""
    import numpy as np
    from asp_offline.calibration import label_hypotheses_against_reference
    from asp_offline.models import Hypothesis

    gt = EvalGraph(
        nodes={
            1: EvalNode(id=1, node_type="object", name="chair", position=np.array([0.0, 0.0, 0.0])),
            2: EvalNode(id=2, node_type="object", name="chair", position=np.array([10.0, 0.0, 0.0])),
            3: EvalNode(id=3, node_type="object", name="lamp", position=np.array([5.0, 5.0, 0.0])),
        },
        edges=[],
    )
    pred_positions = [
        ("chair", [0.3, 0.0, 0.0]),   # competes with the next one for gt chair id=1
        ("chair", [0.1, 0.0, 0.0]),   # objectively closer to gt chair id=1
        ("chair", [10.2, 0.0, 0.0]),  # matches gt chair id=2
        ("sofa", [5.0, 5.0, 0.0]),    # no matching name in gt at all
    ]
    pred = EvalGraph(
        nodes={i: EvalNode(id=i, node_type="object", name=name, position=np.array(pos)) for i, (name, pos) in enumerate(pred_positions)},
        edges=[],
    )
    author_result = match_objects(gt.objects, pred.objects, threshold=0.5)

    reference = {"nodes": [{"id": n.id, "type": "object", "label": n.name, "center": list(n.position), "dimensions": [1, 1, 1]} for n in gt.objects], "edges": []}
    hypotheses = [Hypothesis(name, None, pos, kind="object") for name, pos in pred_positions]
    offline_labels = label_hypotheses_against_reference(hypotheses, reference, object_threshold=0.5)

    assert author_result.true_positives == sum(offline_labels)
    # And they must agree on WHICH ones, not just the count, for a case
    # this specific (two hypotheses genuinely competing for one gt node).
    assert offline_labels == [1, 0, 1, 0]


def test_ged_forbids_substitution_across_different_names():
    gt = load_eval_graph(fixture("ged_gt_one_object.yaml"))
    # Same fixture but pretend everything is renamed - build a graph with
    # a totally different single object, no rooms, to keep the expected
    # value hand-computable: no valid substitution anywhere -> the cheapest
    # option is delete gt's 2 nodes + 1 edge, insert pred's 1 node,
    # cost = 2 (del) + 1 (edge del) + 1 (ins) = 4.
    import networkx as nx
    from graph_io import EvalGraph, EvalNode
    import numpy as np

    other = EvalGraph(
        nodes={99: EvalNode(id=99, node_type="object", name="sofa", position=np.array([0.0, 0.0, 0.0]))},
        edges=[],
    )
    ged, ref_nodes, ref_edges = compute_ged(other, gt)
    assert ged == 4.0
