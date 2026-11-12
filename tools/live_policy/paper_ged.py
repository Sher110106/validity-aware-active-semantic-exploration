"""GED on the paper's scale, with the author's own code (PREREGISTRATION_PAPER.md §1).

Imports load_graph_from_yaml and CustomGED from the author's
exploration/scripts/ged_score_plot.py, so the GED is gmatch4py's
GraphEditDistance(1, 1, 1, 1) with the author's substitution costs. The stage
value is the mean over the graph0 and graph1 YAMLs that exist, as in the
author's main(). Runs inside asp-noetic with gmatch4py in a scratch directory:

    SETUPTOOLS_USE_DISTUTILS=stdlib PYTHONPATH=/workspace/scratch/gm MPLBACKEND=Agg \
      /workspace/environments/semantic_perception/bin/python -B paper_ged.py \
      --ref hm3d:00853=<yaml> --ref frontier_made:00853=<yaml> \
      <run_dir>=<scene> [...] > ged.json

A reference is used only for runs of its own scene. Stages without
navigation_stats.json or without any graph YAML are skipped, as the author does.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
SCRIPTS = "/workspace/catkin_ws/src/active_semantic_perception/exploration/scripts"
sys.path.insert(0, SCRIPTS)
import ged_score_plot as author  # noqa: E402


def stage_rows(run_dir, refs):
    stages_dir = os.path.join(run_dir, "stages")
    rows = []
    for name in sorted((e for e in os.listdir(stages_dir) if e.isdigit()), key=int):
        sd = os.path.join(stages_dir, name)
        ns = os.path.join(sd, "navigation_stats.json")
        if not os.path.exists(ns):
            continue
        stats = json.load(open(ns))
        path_m = stats.get("total_path_length_meters")
        nav_s = stats.get("total_navigation_time_seconds")
        if path_m is None:
            continue
        graphs = []
        for gi in (0, 1):
            gp = os.path.join(sd, f"habitat_scene_graph_original_graph{gi}.yaml")
            if os.path.exists(gp):
                # The author scores an empty graph at path length 0.
                graphs.append(author.nx.Graph() if path_m == 0 else author.load_graph_from_yaml(gp))
        if not graphs:
            continue
        row = {"stage": int(name), "path_m": path_m, "nav_s": nav_s, "n_graphs": len(graphs)}
        for ref_name, ref_graph in refs.items():
            values = [author.CustomGED(1, 1, 1, 1).distance_ged(g, ref_graph) for g in graphs]
            row[f"ged_{ref_name}"] = sum(values) / len(values)
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", action="append", default=[], help="name:scene=path")
    ap.add_argument("runs", nargs="+", help="run_dir=scene")
    args = ap.parse_args()
    refs_by_scene = {}
    for spec in args.ref:
        name_scene, path = spec.split("=", 1)
        name, scene = name_scene.split(":", 1)
        refs_by_scene.setdefault(scene, {})[name] = author.load_graph_from_yaml(path)
    out = {"method": "author ged_score_plot.CustomGED(1,1,1,1), gmatch4py scratch install",
           "references": args.ref, "runs": []}
    for spec in args.runs:
        run_dir, scene = spec.rsplit("=", 1)
        rows = stage_rows(run_dir, refs_by_scene.get(scene, {}))
        out["runs"].append({"run_dir": run_dir, "scene": scene, "stages": rows})
        print(f"{os.path.basename(run_dir)}: {len(rows)} stages", file=sys.stderr)
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
