"""Inter-member agreement of predicted objects per arm ($0, offline).
For each stage and track, for each predicted object of each member, is there a
same-label predicted object within r m (xy) in at least one OTHER member of the
same track? Also: share of predicted objects that sit within 0.5 m (xy) of an
observed object or inside the observed graph's xy hull ("in seen space" proxy)."""
import os, re, glob, ast, json, sys
import numpy as np, yaml
RUNS = sys.argv[1] if len(sys.argv) > 1 else "/tmp/cvp_review/runs"
def vec(v): return np.array(ast.literal_eval(v) if isinstance(v, str) else v, float)
def lab(s): return str(s).lower().replace("_", " ").strip()
runs = sorted(r for r in os.listdir(RUNS) if re.match(r"^e\d_\d{5}_s\d+_(official|placebo|filter_only|oracle_visible)_60m(_rerun\d+)?$", r)
              and r not in ("e1_00853_s44_official_60m", "e1_00853_s44_official_60m_rerun1", "e1_00871_s43_placebo_60m"))
res = {}
for r in runs:
    arm = re.search(r"(official|placebo|filter_only|oracle_visible)", r).group(1)
    sd = os.path.join(RUNS, r, "stages")
    for k in sorted(int(s) for s in os.listdir(sd) if s.isdigit()):
        d = os.path.join(sd, str(k))
        for track in (0, 1):
            obs_p = os.path.join(d, f"habitat_scene_graph_original_graph{track}.yaml")
            if not os.path.exists(obs_p): continue
            obs = yaml.safe_load(open(obs_p))
            obs_ids = {n["id"] for n in obs["nodes"]}
            obs_xy = np.array([vec(n["position"])[:2] for n in obs["nodes"] if n.get("node_type") == "object"]).reshape(-1, 2)
            mem = []
            for g in range(track * 4, track * 4 + 4):
                p = os.path.join(d, f"habitat_scene_graph_new_graph_{g}.yaml")
                if not os.path.exists(p): continue
                G = yaml.safe_load(open(p))
                preds = [(lab(n["name"]), vec(n["position"])[:2]) for n in G["nodes"]
                         if n.get("node_type") == "object" and (n.get("is_predicted") or n["id"] not in obs_ids) and "door" not in lab(n.get("name", ""))]
                mem.append(preds)
            if len(mem) < 2: continue
            for i, P in enumerate(mem):
                others = [q for j, Q in enumerate(mem) if j != i for q in Q]
                for (l, xy) in P:
                    a05 = any(l == l2 and np.linalg.norm(xy - xy2) < 0.5 for (l2, xy2) in others)
                    a10 = any(l == l2 and np.linalg.norm(xy - xy2) < 1.0 for (l2, xy2) in others)
                    a20 = any(l == l2 and np.linalg.norm(xy - xy2) < 2.0 for (l2, xy2) in others)
                    any10 = any(np.linalg.norm(xy - xy2) < 1.0 for (l2, xy2) in others)
                    near_obs = bool(len(obs_xy)) and float(np.min(np.linalg.norm(obs_xy - xy, axis=1))) < 1.0
                    res.setdefault(arm, []).append((a05, a10, a20, any10, near_obs))
print("arm, n predicted objects, same-label agreement with another member within 0.5 / 1 / 2 m, any-label within 1 m, within 1 m of an observed object")
for arm, v in res.items():
    v = np.array(v, float)
    print(arm, len(v), " ".join("%.3f" % x for x in v.mean(0)))
if len(sys.argv) > 2:
    keys = ["same_label_0.5m", "same_label_1m", "same_label_2m", "any_label_1m", "within_1m_of_observed"]
    json.dump({arm: dict(n=len(v), **{k: round(float(x), 4) for k, x in zip(keys, np.array(v, float).mean(0))}) for arm, v in res.items()},
              open(sys.argv[2], "w"), indent=1)
