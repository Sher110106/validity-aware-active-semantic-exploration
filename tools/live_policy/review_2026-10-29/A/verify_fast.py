#!/usr/bin/env python3
"""Check the vectorized scorer against the pinned loop and the run's own pose_log."""
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, "/tmp/cvp_review/work_A")
import numpy as np  # noqa: E402

np.set_printoptions(legacy="1.25")
import fastig  # noqa: E402
import pinned_harness as ph  # noqa: E402
import replay as rp  # noqa: E402

cases = [("e1_00853_s42_official_60m", 1), ("e1_00853_s42_official_60m", 9), ("e1_00871_s42_placebo_60m", 5),
         ("e2_00871_s44_filter_only_60m", 12), ("e3_00871_s42_oracle_visible_60m", 7), ("e1_00871_s44_placebo_60m", 20)]
for run, k in cases:
    meta = rp.stage_meta(run)[k]
    sd = f"{rp.RUNS}/{run}/stages/{k}"
    gids_exist = sorted(int(re.search(r"_(\d+)\.yaml$", f).group(1)) for f in glob.glob(f"{sd}/habitat_scene_graph_new_graph_*.yaml"))
    order = meta.get("done_order")
    if rp.arm_of(run) in ("official", "filter_only") and order:
        seen = []
        for g in order:
            if g in gids_exist and g not in seen:
                seen.append(g)
        gids = seen + [g for g in gids_exist if g not in seen]
    else:
        gids = gids_exist
    files = [f"{sd}/habitat_scene_graph_new_graph_{g}.yaml" for g in gids]
    seed = rp.P[run]["cfg"]["SEED"]
    cur = rp.current_pos(run, k)
    t0 = time.time()
    sc = fastig.Scorer(files, seed)
    kept, scores, total, order_f = sc.first_stage(seed, meta["nprior"], cur)
    t1 = time.time()
    calc = ph.make_calc(seed, meta["nprior"], "/tmp/cvp_review/work_A/tmp")
    lo, hi, scored, order_p = ph.first_stage(calc, files, cur)
    t2 = time.time()
    pin_ig = np.array([s[1] for s in scored])
    fast_ig = scores[:, 0] + scores[:, 1]
    same_cands = len(kept) == len(scored) and np.allclose(kept, np.array([s[2] for s in scored]))
    tops = rp.P[run]["stages"][str(k)]["pose_tops"][-1]["top"]
    fast_top = [kept[i] for i in order_f[:10]]
    match_log = all(np.allclose(a, b, atol=1e-6) for a, b in zip(tops, fast_top)) and len(tops) == len(fast_top)
    print(run, k, "cands_same", same_cands, "max|dIG|", float(np.max(np.abs(pin_ig - fast_ig))) if same_cands else None,
          "fast_top10==log", match_log, f"fast {t1 - t0:.1f}s pinned {t2 - t1:.1f}s", flush=True)
    # second stage check at logged winner new pose
    fin = rp.P[run]["stages"][str(k)]["pose_finals"][-1]
    s2, _ = sc.score(np.array(fin["new"]), fastig.second_cfg())
    print("   second-stage logged", fin["best_ig"], "fast", (s2[:, 0] + s2[:, 1]).round(6).tolist())
