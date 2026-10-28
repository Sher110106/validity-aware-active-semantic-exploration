"""Score live-campaign runs on the map the robot actually built.

For every stage with a navigation_stats.json, both tracked observed graphs
(habitat_scene_graph_original_graph{0,1}.yaml) are scored against the
scene's frontier reference with two scorers, then averaged over tracks:
- canonical: tools/asp_offline/evaluator.py evaluate_graph (object P/R/F1, nGED)
- author-faithful: tools/evaluator match_objects (exact label, < 0.5 m, greedy)
Scenes with an HM3D-annotation reference (00853, 00871) are scored against it
too, under hm3d_-prefixed keys. Path-normalised AUC
(asp_offline.evaluator.area_under_curve, hold-last past the final checkpoint)
is reported at every budget, with reached_<B>m flags. Predictions never enter these numbers, so all
policy arms are scored the same way.

Usage (inside the container):
    python -B live_score.py <run_dir>=<scene> [...] > scores.json
"""
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path[:0] = ["/workspace/tools/evaluator", "/workspace/tools"]
from asp_offline.author_io import load_author_graph  # noqa: E402
from asp_offline.evaluator import area_under_curve, evaluate_graph  # noqa: E402
from graph_io import load_eval_graph  # noqa: E402
from matching import match_objects  # noqa: E402

REFS = {
    "00069": "/workspace/runs/scene00069_frontier_reference/stages/25/habitat_scene_graph_original_graph0.yaml",
    "00573": "/workspace/runs/scene00573_frontier_reference/stages/53/habitat_scene_graph_original_graph0.yaml",
    "00853": "/workspace/runs/scene00853_frontier_reference/stages/33/habitat_scene_graph_original_graph0.yaml",
    "00871": "/workspace/runs/scene00871_frontier_reference/stages/54/habitat_scene_graph_original_graph0.yaml",
}
# Policy-independent references built from the official HM3D semantic
# annotations (val scenes only); see runs/live_campaign/hm3d_refs_work/.
REFS_HM3D = {
    "00853": "/workspace/runs/live_campaign/hm3d_refs_work/00853_hm3d_reference.yaml",
    "00871": "/workspace/runs/live_campaign/hm3d_refs_work/00871_hm3d_reference.yaml",
}
BUDGETS = (10.0, 25.0, 50.0, 60.0, 90.0, 120.0)
CANON = ("object_precision", "object_recall", "object_f1", "normalized_ged")


def score_run(run_dir, scene, ref_path=None, prefix=""):
    ref_path = ref_path or REFS[scene]
    ref_canon = load_author_graph(ref_path, observed=True)
    ref_af = load_eval_graph(ref_path)
    stages_dir = os.path.join(run_dir, "stages")
    rows = []
    for name in sorted((e for e in os.listdir(stages_dir) if e.isdigit()), key=int):
        sd = os.path.join(stages_dir, name)
        ns = os.path.join(sd, "navigation_stats.json")
        if not os.path.exists(ns):
            continue
        path_m = json.load(open(ns)).get("total_path_length_meters")
        if path_m is None:
            continue
        canon, af = [], []
        for gi in (0, 1):
            gp = os.path.join(sd, f"habitat_scene_graph_original_graph{gi}.yaml")
            if not os.path.exists(gp):
                continue
            canon.append(evaluate_graph(load_author_graph(gp, observed=True), ref_canon))
            mr = match_objects(ref_af.objects, load_eval_graph(gp).objects, threshold=0.5)
            af.append({"af_precision": mr.precision, "af_recall": mr.recall, "af_f1": mr.f1})
        if not canon:
            continue
        row = {"stage": int(name), "path_m": path_m, "n_graphs": len(canon)}
        for k in CANON:
            row[k] = sum(c[k] for c in canon) / len(canon)
        for k in ("af_precision", "af_recall", "af_f1"):
            row[k] = sum(a[k] for a in af) / len(af)
        rows.append(row)
    out = {"run_dir": run_dir, "scene": scene, "reference": ref_path, "stages": rows,
           "final_path_m": max((r["path_m"] for r in rows), default=0.0)}
    # area_under_curve holds the last value past the final checkpoint, so a
    # run that stopped short is scored hold-last; reached_<B>m records it and
    # the analysis applies the pre-registered 50 m exclusion.
    for budget in BUDGETS:
        if rows:
            out[f"reached_{int(budget)}m"] = out["final_path_m"] + 1e-9 >= budget
            for metric in ("object_f1", "object_recall", "normalized_ged", "af_f1", "af_recall"):
                out[f"auc_{metric}_to_{int(budget)}m"] = round(area_under_curve(rows, metric, budget_m=budget), 4)
    if prefix:
        out = {k if k in ("run_dir", "scene", "final_path_m") else prefix + k: v for k, v in out.items()}
    return out


def score_all(run_dir, scene):
    """Frontier-made reference (unprefixed keys) plus the HM3D-annotation
    reference (hm3d_ keys) where one exists."""
    out = score_run(run_dir, scene)
    if scene in REFS_HM3D:
        out.update(score_run(run_dir, scene, REFS_HM3D[scene], prefix="hm3d_"))
    return out


if __name__ == "__main__":
    results = []
    for arg in sys.argv[1:]:
        run_dir, scene = arg.split("=")
        try:
            results.append(score_all(run_dir, scene))
        except Exception as e:  # report and keep scoring the other runs
            results.append({"run_dir": run_dir, "scene": scene, "error": repr(e)})
    print(json.dumps(results, indent=1))
