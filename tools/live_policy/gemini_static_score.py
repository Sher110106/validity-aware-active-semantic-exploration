"""Score gemini_static.py outputs: predicted-object precision of Gemini vs
DeepSeek-1017 completions on identical inputs, against the HM3D annotation,
with placebo-v2 draws as the chance level.

A hit is a predicted object (a node not in the observed graph) within R m
(xy) of a same-label annotated object that the observed graph has not
already matched (greedy, one reference object per hit). Labels are
normalised (lower case, '_' -> ' '). Primary metric (fixed 2026-10-28 before
the second batch): only predictions placed more than 0.5 m from every observed
object count ("new_*"), because Gemini often re-emits an observed object under
a corrected label, which matches the annotation without predicting anything
unseen; those relabels are reported separately.

Usage: python -B gemini_static_score.py <out_dir> > scores.json
"""
import ast
import glob
import json
import os
import sys

import numpy as np
import yaml

sys.path[:0] = ["/workspace/tools/live_policy"]
import live_policy  # noqa: E402

REFS = {"00853": "/workspace/runs/live_campaign/hm3d_refs_work/00853_hm3d_reference.yaml",
        "00871": "/workspace/runs/live_campaign/hm3d_refs_work/00871_hm3d_reference.yaml"}
VOCAB = {v.lower() for v in yaml.safe_load(open(
    "/workspace/catkin_ws/src/active_semantic_perception/task_def/objects_habitat_apartment.yaml"))}


def norm(label):
    return str(label).lower().replace("_", " ").strip()


def xy(node):
    p = node["position"]
    p = ast.literal_eval(p) if isinstance(p, str) else p
    return float(p[0]), float(p[1])


def objects(graph):
    return [n for n in graph.get("nodes") or [] if n.get("node_type") == "object" and "position" in n]


def greedy(preds, refs, radius):
    pairs = sorted(((np.hypot(a[1][0] - b[1][0], a[1][1] - b[1][1]), i, j)
                    for i, a in enumerate(preds) for j, b in enumerate(refs) if a[0] == b[0]))
    used_p, used_r, hits = set(), set(), 0
    for d, i, j in pairs:
        if d >= radius:
            break
        if i not in used_p and j not in used_r:
            used_p.add(i); used_r.add(j); hits += 1
    return hits, used_r


def score(completion, observed, novel_refs):
    obs_ids = {n["id"] for n in observed.get("nodes") or []}
    obs_xy = [xy(n) for n in objects(observed)]
    preds = [(norm(n.get("name", "")), xy(n)) for n in objects(completion) if n["id"] not in obs_ids]
    new = [p for p in preds if all(np.hypot(p[1][0] - a, p[1][1] - b) > 0.5 for a, b in obs_xy)]
    out = {"n_pred": len(preds), "in_vocab": sum(1 for p in preds if p[0] in VOCAB),
           "n_new": len(new), "n_relabel": len(preds) - len(new)}
    for r in (0.5, 1.0, 2.0):
        out[f"hits_{r}"] = greedy(preds, novel_refs, r)[0]
        out[f"new_hits_{r}"] = greedy(new, novel_refs, r)[0]
    return out


def main():
    root = sys.argv[1]
    calib = live_policy.load_calibration()
    rows = []
    for work in sorted(glob.glob(os.path.join(root, "*", "*"))):
        obs_path = os.path.join(work, "habitat_scene_graph_original_graph0.yaml")
        if not os.path.exists(obs_path):
            continue
        run = os.path.basename(os.path.dirname(work))
        scene = run.split("_")[1]
        observed = yaml.safe_load(open(obs_path))
        ref = [(norm(n.get("name", "")), xy(n)) for n in objects(yaml.safe_load(open(REFS[scene])))]
        obs_objs = [(norm(n.get("name", "")), xy(n)) for n in objects(observed)]
        _, seen = greedy(obs_objs, ref, 0.5)
        novel = [r for j, r in enumerate(ref) if j not in seen]
        row = {"run": run, "stage": os.path.basename(work), "novel_refs": len(novel), "models": {}}
        for model, pattern in (("gemini", "gemini_new_graph_*.yaml"), ("deepseek", "deepseek_new_graph_*.yaml")):
            row["models"][model] = [score(yaml.safe_load(open(p)), observed, novel)
                                    for p in sorted(glob.glob(os.path.join(work, pattern)))]
        row["models"]["placebo"] = [score(live_policy.placebo_graph(observed, np.random.default_rng([7, k]), calib),
                                          observed, novel) for k in range(4)]
        rows.append(row)
    totals = {}
    for model in ("gemini", "deepseek", "placebo"):
        ms = [m for r in rows for m in r["models"][model]]
        t = {"completions": len(ms)}
        for k in ("n_pred", "in_vocab", "n_new", "n_relabel"):
            t[k] = sum(m[k] for m in ms)
        for rad in (0.5, 1.0, 2.0):
            t[f"hits_{rad}"] = sum(m[f"hits_{rad}"] for m in ms)
            t[f"precision_{rad}"] = round(t[f"hits_{rad}"] / t["n_pred"], 4) if t["n_pred"] else None
            t[f"new_hits_{rad}"] = sum(m[f"new_hits_{rad}"] for m in ms)
            t[f"new_precision_{rad}"] = round(t[f"new_hits_{rad}"] / t["n_new"], 4) if t["n_new"] else None
        totals[model] = t
    print(json.dumps({"totals": totals, "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
