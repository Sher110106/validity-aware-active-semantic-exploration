"""
Graph Edit Distance, replicating the substitution-cost logic in
exploration/scripts/ged_score_plot.py's custom_node_cost / CustomGED exactly:
substitution is free (cost 0) only if node_type and name match, and - for
objects - parent_name matches too, and position distance is within threshold
(0.5 m objects, 4 m rooms, matching IMPLEMENTATION_RESEARCH.md section 3.3);
otherwise a large forbidding penalty, so the optimal edit path always prefers
plain node insertion/deletion (cost 1 each, matching gmatch4py's
CustomGED(1, 1, 1, 1)) over any non-qualifying substitution.

Uses networkx's built-in graph_edit_distance rather than gmatch4py (a
reproduction choice, not an attempt at bit-identical output - see
IMPLEMENTATION_RESEARCH.md section 3.3: "we must implement our own
parameterized evaluator (already decided)"). Same cost semantics, standard
well-tested implementation, avoids an extra third-party dependency.

Solver-fidelity disclosure (2026-09-16, Opus audit finding M2,
REVIEW_2026-09-14.md): `nx.graph_edit_distance` is an anytime A*-style
search - given enough time it finds the EXACT minimum edit distance, but
under a finite `timeout` (60s here) it returns the best UPPER BOUND found
so far if the search has not yet proven optimality by then, with no flag
in its return value distinguishing "exact" from "cut off early."

**Checked directly on this project's real data, not left theoretical**:
called `nx.optimize_graph_edit_distance` (the generator `graph_edit_
distance` wraps) on scene 00069's real reference graph (76 nodes) against
a real predicted tracked graph (41 nodes) - a first complete edit path
was found at value=165.0 in 0.20s, improved once more to value=163.0 at
0.36s, then **zero further improvement for 70+ seconds** before the
check was stopped. This confirms the search does NOT reliably prove
optimality within this module's 60s timeout at this project's actual
graph scale (tens to ~100 object+room nodes) - every GED number this
project reports from this module is a best-found UPPER BOUND on the true
minimum edit distance, not a certified-exact result, and `compute_ged`
has no way to detect or flag when this happened (a valid, if suboptimal,
edit path is typically found within the first second, so the `ged is
None` branch essentially never triggers - the risk is a silently-
non-optimal value, not a missing one). Not fixed here (would need either
a fundamentally different exact algorithm or an explicit convergence
check wired into every call site) - disclosed as a real, checked
limitation of every GED number in this project, not a hypothetical one.
Reproduce via `tyrone_mirror/scratchpad_verify/check_ged_convergence.py`.
"""
from __future__ import annotations

import networkx as nx
import numpy as np

PENALTY = 1000.0
DEFAULT_OBJECT_THRESHOLD = 0.5
DEFAULT_ROOM_THRESHOLD = 4.0


def _node_substitute_cost(n1_attrs, n2_attrs, object_threshold, room_threshold):
    node_type = n1_attrs["node_type"]
    if node_type != n2_attrs["node_type"]:
        return PENALTY
    if n1_attrs["name"] != n2_attrs["name"]:
        return PENALTY
    if node_type == "object" and n1_attrs.get("parent_name") != n2_attrs.get("parent_name"):
        return PENALTY

    diff = n1_attrs["position"] - n2_attrs["position"]
    if node_type == "room":
        diff = diff.copy()
        diff[2] = 0.0  # room match ignores height, matching ged_score_plot.py
    distance = float(np.linalg.norm(diff))

    threshold = object_threshold if node_type == "object" else room_threshold
    if distance > threshold:
        return PENALTY
    return 0.0


def eval_graph_to_networkx(eval_graph) -> nx.Graph:
    G = nx.Graph()
    for node_id, node in eval_graph.nodes.items():
        G.add_node(
            node_id,
            node_type=node.node_type,
            name=node.name,
            position=node.position,
            parent_name=node.parent_name,
        )
    for u, v in eval_graph.edges:
        G.add_edge(u, v)
    return G


def compute_ged(pred_eval_graph, gt_eval_graph, object_threshold=DEFAULT_OBJECT_THRESHOLD,
                 room_threshold=DEFAULT_ROOM_THRESHOLD, timeout=60.0):
    """Returns (ged_value, reference_node_count, reference_edge_count).

    reference_* counts are the gt graph's own node/edge count, for the
    reference-size-normalized GED AUC IMPLEMENTATION_RESEARCH.md section 4.5
    calls for (normalize by dividing ged_value by (ref_nodes + ref_edges), or
    whichever denominator is chosen at aggregation time - left to the caller
    so this function stays a pure distance calculation).
    """
    G_pred = eval_graph_to_networkx(pred_eval_graph)
    G_gt = eval_graph_to_networkx(gt_eval_graph)

    if G_pred.number_of_nodes() == 0 and G_gt.number_of_nodes() == 0:
        return 0.0, 0, 0

    def node_subst_cost(a, b):
        return _node_substitute_cost(a, b, object_threshold, room_threshold)

    ged = nx.graph_edit_distance(
        G_pred,
        G_gt,
        node_subst_cost=node_subst_cost,
        node_del_cost=lambda a: 1.0,
        node_ins_cost=lambda a: 1.0,
        edge_subst_cost=lambda a, b: 0.0,
        edge_del_cost=lambda a: 1.0,
        edge_ins_cost=lambda a: 1.0,
        timeout=timeout,
    )
    if ged is None:
        # timed out before finding any complete edit path - caller must
        # decide how to handle (e.g. retry with a longer timeout, or report
        # missing rather than silently substituting a wrong number).
        return None, G_gt.number_of_nodes(), G_gt.number_of_edges()
    return float(ged), G_gt.number_of_nodes(), G_gt.number_of_edges()
