#!/usr/bin/env python3
"""Positive control for the oracle_visible arm (E3), run before any counted run.

Draws four oracle members per track on saved observed graphs from finished
live runs (stages 0, 5, 10 and 15 of each, both tracks; key [run seed, stage,
track * 4 + member], as live) and scores them with gemini_static_score.score
against the primary HM3D reference, beside the placebo on the same graphs and
the run's own completions for that track.
Pass rule: oracle new_precision_0.5 = 1.0, n_relabel = 0, and fewer than 20%
fallback draws. Also reports, for the P2 replacement check, each hypothesis
object's xy distance to the nearest observed room centre, oracle vs placebo.

Usage (pipeline Python, inside a container):
    oracle_positive_control.py <campaign_dir> <out.json> <run> [<run> ...]
"""
import glob
import json
import os
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_static_score as gs  # noqa: E402
import live_policy  # noqa: E402

STAGES = (0, 5, 10, 15)


def main() -> int:
    campaign, out = sys.argv[1], sys.argv[2]
    calib = live_policy.load_calibration()
    sets = json.load(open(live_policy.ORACLE_SETS_PATH))["scenes"]
    rows = []
    for run in sys.argv[3:]:
        scene = run.split("_")[1]
        number = str(int(scene))
        candidates = sets[number]["objects"]
        ref = [(gs.norm(c["name"]), (c["position"][0], c["position"][1])) for c in candidates]
        for k in STAGES:
            work = os.path.join(campaign, run, "stages", str(k))
            for track in (0, 1):
                obs_path = os.path.join(work, f"habitat_scene_graph_original_graph{track}.yaml")
                if not os.path.exists(obs_path):
                    continue
                observed = yaml.safe_load(open(obs_path))
                obs_objs = [(gs.norm(n.get("name", "")), gs.xy(n)) for n in gs.objects(observed)]
                _, seen = gs.greedy(obs_objs, ref, 0.5)
                novel = [r for j, r in enumerate(ref) if j not in seen]
                row = {"run": run, "stage": k, "track": track, "observed_objects": len(obs_objs),
                       "refs_seen": len(seen), "novel_refs": len(novel), "oracle": [], "placebo": [], "llm": []}
                rooms = [gs.xy(n) for n in observed.get("nodes") or [] if n.get("node_type") == "room" and "position" in n]
                obs_ids = {n["id"] for n in observed.get("nodes") or []}
                seed = int(run.split("_s")[1].split("_")[0])
                for member in range(4):
                    gid = track * 4 + member
                    graph, info = live_policy.oracle_graph(observed, np.random.default_rng([seed, k, gid]), calib, candidates)
                    placebo = live_policy.placebo_graph(observed, np.random.default_rng([seed, k, gid]), calib)
                    row["oracle"].append({**gs.score(graph, observed, novel), **info})
                    row["placebo"].append(gs.score(placebo, observed, novel))
                    for arm, g in (("oracle", graph), ("placebo", placebo)):
                        if rooms:
                            row.setdefault(f"{arm}_room_dist", []).extend(
                                min(np.hypot(gs.xy(n)[0] - a, gs.xy(n)[1] - b) for a, b in rooms)
                                for n in gs.objects(g) if n["id"] not in obs_ids)
                # The run's own completions for this track (graph id // 4 == track).
                for p in sorted(glob.glob(os.path.join(work, "habitat_scene_graph_new_graph_*.yaml"))):
                    if int(os.path.splitext(p)[0].rsplit("_", 1)[1]) // 4 == track:
                        row["llm"].append(gs.score(yaml.safe_load(open(p)), observed, novel))
                rows.append(row)
    totals = {}
    for arm in ("oracle", "placebo", "llm"):
        ms = [m for r in rows for m in r[arm]]
        t = {"completions": len(ms)}
        for key in ("n_pred", "n_new", "n_relabel"):
            t[key] = sum(m[key] for m in ms)
        for rad in (0.5, 1.0, 2.0):
            t[f"new_hits_{rad}"] = sum(m[f"new_hits_{rad}"] for m in ms)
            t[f"new_precision_{rad}"] = round(t[f"new_hits_{rad}"] / t["n_new"], 4) if t["n_new"] else None
        if arm == "oracle":
            t["fallback_frac"] = round(sum(m["fallback"] for m in ms) / len(ms), 4) if ms else None
            t["candidates_in_reach_median"] = float(np.median([m["n_candidates_in_reach"] for m in ms])) if ms else None
            t["drawn_median"] = float(np.median([m["n_drawn"] for m in ms])) if ms else None
        totals[arm] = t
    for arm in ("oracle", "placebo"):
        d = np.array([x for r in rows for x in r.get(f"{arm}_room_dist", [])])
        totals[f"{arm}_room_dist"] = {"n": int(d.size), "median": round(float(np.median(d)), 3),
                                      "p90": round(float(np.percentile(d, 90)), 3)} if d.size else None
    o = totals["oracle"]
    totals["pass"] = bool(o["completions"] and o["new_precision_0.5"] == 1.0 and o["n_relabel"] == 0
                          and o["fallback_frac"] < 0.2)
    json.dump({"totals": totals, "rows": rows}, open(out, "w"), indent=1)
    print(json.dumps(totals, indent=1))
    return 0 if totals["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
