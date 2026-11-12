#!/usr/bin/env python3
"""Approach-gap ceilings for the E3 drawn-vs-undrawn contrast (pool approximation).
For each e3 stage/track: gap if the robot stood at (a) a random drawn object,
(b) the 0.5 m grid point with the MOST drawn objects within 3.5 m (what a planner
that follows only the hypotheses could do), (c) the grid point with the largest gap
(uses the undrawn labels too; an upper bound), (d) the live reached point.
Paths and hypothesis files only."""
import sys, re, glob, json, os
sys.path.insert(0, "/tmp/cvp_review/work_A")
import numpy as np, yaml
import replay as rp
lp = rp.lp; RUNS = rp.RUNS
rng = np.random.default_rng(11)
res = {}
for run in sorted(os.listdir(RUNS)):
    if not run.startswith("e3_"): continue
    scene = re.search(r"_(\d{5})_s", run).group(1)
    pool = rp.oracle_pool(scene)
    ks = sorted(int(os.path.basename(d)) for d in glob.glob(f"{RUNS}/{run}/stages/*") if os.path.basename(d).isdigit())
    acc = {"random_drawn": [], "max_drawn_count": [], "best_gap": [], "live": []}
    for k in ks:
        nxt = f"{RUNS}/{run}/stages/{k+1}/executed_path.json"
        if not os.path.exists(nxt): continue
        w = json.load(open(nxt))["world_frame_path"]
        if not w: continue
        rx, ry = w[-1][0], w[-1][1]
        for t in (0, 1):
            op = f"{RUNS}/{run}/stages/{k}/habitat_scene_graph_original_graph{t}.yaml"
            if not os.path.exists(op): continue
            g = yaml.safe_load(open(op)); elig = lp.oracle_eligible(g, pool)
            if not elig: continue
            obs_ids = {n["id"] for n in g["nodes"]}
            dk = set()
            for f in glob.glob(f"{RUNS}/{run}/stages/{k}/habitat_scene_graph_new_graph_*.yaml"):
                gid = int(re.search(r"_(\d+)\.yaml$", f).group(1))
                if gid // 4 != t: continue
                for n in yaml.safe_load(open(f))["nodes"]:
                    if n.get("node_type") == "object" and n["id"] not in obs_ids and "position" in n:
                        dk.add((lp._label(n["name"]), tuple(round(v, 3) for v in lp._vec(n["position"]))))
            pts = np.array([c["position"][:2] for c in elig])
            drawn = np.array([(lp._label(c["name"]), tuple(round(v, 3) for v in c["position"])) in dk for c in elig])
            if not drawn.any() or drawn.all(): continue
            def gap(mask): return mask[drawn].mean() - mask[~drawn].mean()
            j = rng.choice(np.nonzero(drawn)[0])
            acc["random_drawn"].append(gap(np.hypot(pts[:,0]-pts[j,0], pts[:,1]-pts[j,1]) <= 3.5))
            xs = np.arange(pts[:,0].min()-1, pts[:,0].max()+1, 0.5); ys = np.arange(pts[:,1].min()-1, pts[:,1].max()+1, 0.5)
            G = np.array([(x, y) for x in xs for y in ys])
            A = np.hypot(G[:,None,0]-pts[None,:,0], G[:,None,1]-pts[None,:,1]) <= 3.5
            cnt = A[:, drawn].sum(1)
            best = np.flatnonzero(cnt == cnt.max())
            acc["max_drawn_count"].append(np.mean([gap(A[b]) for b in best]))
            acc["best_gap"].append(max(gap(A[b]) for b in range(len(G))))
            acc["live"].append(gap(np.hypot(pts[:,0]-rx, pts[:,1]-ry) <= 3.5))
    res[run] = {k: round(float(np.mean(v)), 3) for k, v in acc.items()}
    res[run]["units"] = len(acc["live"])
    print(run, res[run])
json.dump(res, open("/tmp/cvp_review/work_A/e3_ceiling.json", "w"), indent=1)
