#!/usr/bin/env python3
"""E3 mechanism: why exact objects pull the robot only slightly.

Eligible set per stage/track is approximated by the POOL of true objects that
any oracle run drew (oracle_sets.json is not on this machine). For each e3 run,
stage k, track t:
  - drawn = named by some member of the track (as stage_diagnostics.py);
  - members_per_drawn = how many of the track's members drew it;
  - approach = reached viewpoint (last point of stages/(k+1)/executed_path.json)
    within 3.5 m (xy);
  - ideal approach: same indicator if the robot stood exactly at a random drawn
    object (an upper bound on how much a single stop can favour drawn objects);
  - neighbours: undrawn eligible objects within 3.5 m of each drawn object.
Uses paths and hypothesis files only; no mapping outcome, no F1/AUC.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, "/tmp/cvp_review/work_A")
import numpy as np  # noqa: E402
import yaml  # noqa: E402

import replay as rp  # noqa: E402

lp = rp.lp
RUNS = rp.RUNS


def main():
    rng = np.random.default_rng(7)
    runs = [r for r in sorted(os.listdir(RUNS)) if r.startswith("e3_")]
    summary = {}
    for run in runs:
        scene = re.search(r"_(\d{5})_s", run).group(1)
        pool = rp.oracle_pool(scene)
        ks = sorted(int(os.path.basename(d)) for d in glob.glob(f"{RUNS}/{run}/stages/*") if os.path.basename(d).isdigit())
        rows = []
        ideal_gaps = []
        neigh = []
        mult = []
        for k in ks:
            nxt = f"{RUNS}/{run}/stages/{k + 1}/executed_path.json"
            if not os.path.exists(nxt):
                continue
            w = json.load(open(nxt))["world_frame_path"]
            if not w:
                continue
            rx, ry = w[-1][0], w[-1][1]
            for t in (0, 1):
                op = f"{RUNS}/{run}/stages/{k}/habitat_scene_graph_original_graph{t}.yaml"
                if not os.path.exists(op):
                    continue
                g = yaml.safe_load(open(op))
                elig = lp.oracle_eligible(g, pool)
                if not elig:
                    continue
                obs_ids = {n["id"] for n in g["nodes"]}
                drawn_count = {}
                for f in glob.glob(f"{RUNS}/{run}/stages/{k}/habitat_scene_graph_new_graph_*.yaml"):
                    gid = int(re.search(r"_(\d+)\.yaml$", f).group(1))
                    if gid // 4 != t:
                        continue
                    seen = set()
                    for n in yaml.safe_load(open(f))["nodes"]:
                        if n.get("node_type") == "object" and n["id"] not in obs_ids and "position" in n:
                            key = (lp._label(n["name"]), tuple(round(v, 3) for v in lp._vec(n["position"])))
                            seen.add(key)
                    for key in seen:
                        drawn_count[key] = drawn_count.get(key, 0) + 1
                pts = np.array([c["position"][:2] for c in elig])
                keys = [(lp._label(c["name"]), tuple(round(v, 3) for v in c["position"])) for c in elig]
                drawn = np.array([kk in drawn_count for kk in keys])
                appr = np.hypot(pts[:, 0] - rx, pts[:, 1] - ry) <= 3.5
                for i in range(len(elig)):
                    rows.append((k, t, bool(drawn[i]), bool(appr[i])))
                if drawn.any() and (~drawn).any():
                    # ideal: stand at a random drawn object
                    j = rng.choice(np.nonzero(drawn)[0])
                    ia = np.hypot(pts[:, 0] - pts[j, 0], pts[:, 1] - pts[j, 1]) <= 3.5
                    ideal_gaps.append(ia[drawn].mean() - ia[~drawn].mean())
                    for i in np.nonzero(drawn)[0]:
                        dd = np.hypot(pts[:, 0] - pts[i, 0], pts[:, 1] - pts[i, 1])
                        neigh.append(int(np.sum((dd <= 3.5) & ~drawn)))
                    mult += [drawn_count[keys[i]] for i in np.nonzero(drawn)[0]]
        if not rows:
            continue
        a = np.array(rows, dtype=object)
        dr = np.array([r[2] for r in rows])
        ap = np.array([r[3] for r in rows])
        summary[run] = {"rows": len(rows), "drawn_share": float(dr.mean()),
                        "approach_drawn": float(ap[dr].mean()), "approach_undrawn": float(ap[~dr].mean()),
                        "approach_gap": float(ap[dr].mean() - ap[~dr].mean()),
                        "ideal_gap_mean": float(np.mean(ideal_gaps)) if ideal_gaps else None,
                        "undrawn_neighbours_within_3.5m_median": float(np.median(neigh)) if neigh else None,
                        "members_per_drawn_mean": float(np.mean(mult)) if mult else None,
                        "share_drawn_by_1_member": float(np.mean(np.array(mult) == 1)) if mult else None}
        print(run, json.dumps(summary[run]), flush=True)
    json.dump(summary, open("/tmp/cvp_review/work_A/e3_mech.json", "w"), indent=1)


if __name__ == "__main__":
    main()
