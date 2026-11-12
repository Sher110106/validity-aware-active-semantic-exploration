#!/usr/bin/env python3
"""Static three-way table on live official runs: observed map plus raw
predictions, plus unanimity-filtered predictions (tau = 1.0), and the observed
map alone, scored against one reference as path-normalised object-F1 AUC.

Same construction as /tmp/cvp_zero/hm3d_rescore/scripts/observed_auc.py (the
120 m matrix check), with the budget as an argument. Predictions never steer
anything here; this asks only whether adding them to the map helps the map.

Usage: static_three_way.py <budget_m> <reference.yaml> <out.json> <run_dir> [<run_dir> ...]
Run with PYTHONPATH=<repo>/tools.
"""
import json
import sys
from pathlib import Path

from asp_offline.author_io import load_author_graph
from asp_offline.evaluator import area_under_curve, evaluate_graph
from asp_offline.support_policy import support_filtered_graph
import extension_policy_replay as epr

M = ("object_precision", "object_recall", "object_f1", "normalized_ged")


def avg(rs):
    return {k: sum(r[k] for r in rs) / len(rs) for k in M}


def run_table(root: Path, reference, budget: float) -> dict:
    rows = {"official": [], "tau_1.0": [], "observed_only": []}
    kept = total = 0
    for sd in sorted([p for p in (root / "stages").iterdir() if p.name.isdigit()], key=lambda p: int(p.name)):
        ns = sd / "navigation_stats.json"
        path_m = json.loads(ns.read_text()).get("total_path_length_meters") if ns.exists() else None
        if path_m is None:
            continue
        per = {k: [] for k in rows}
        for gi in (0, 1):
            op = sd / f"habitat_scene_graph_original_graph{gi}.yaml"
            if not op.exists():
                continue
            obs = load_author_graph(op, observed=True)
            comps = [load_author_graph(p) for p in epr._scene_completion_paths(sd, gi)[0]]
            if not comps:
                continue
            per["official"].append(avg([evaluate_graph(epr._official_graph(obs, c), reference) for c in comps]))
            filtered = [support_filtered_graph(obs, c, comps, 1.0, expected_size=4) for c in comps]
            per["tau_1.0"].append(avg([evaluate_graph(g, reference) for g in filtered]))
            per["observed_only"].append(evaluate_graph(obs, reference))
            n_obs = len(obs.get("nodes", []))
            total += sum(len(c.get("nodes", [])) - n_obs for c in comps)
            kept += sum(len(g.get("nodes", [])) - n_obs for g in filtered)
        for k in rows:
            if per[k]:
                rows[k].append({"path_m": path_m, **avg(per[k])})
    out = {k: {m: round(area_under_curve(v, m, budget_m=budget), 4) for m in M} for k, v in rows.items()}
    out["predicted_nodes"] = {"total": total, "kept_by_unanimity": kept}
    return out


def main():
    budget, ref_path, out_path = float(sys.argv[1]), sys.argv[2], sys.argv[3]
    reference = load_author_graph(ref_path, observed=True)
    result = {"budget_m": budget, "reference": ref_path, "runs": {}}
    for run in sys.argv[4:]:
        result["runs"][Path(run).name] = run_table(Path(run), reference, budget)
        print(Path(run).name, json.dumps({k: v.get("object_f1", v) for k, v in result["runs"][Path(run).name].items()}), flush=True)
    json.dump(result, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main()
