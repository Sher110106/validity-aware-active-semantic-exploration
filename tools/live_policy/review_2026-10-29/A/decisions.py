#!/usr/bin/env python3
"""Per-stage decision anatomy from pose_log.json, path_log.json and executed paths.

For each counted run and stage k (last pose_log attempt = the one that planned):
- rank of the chosen target among the first-stage top-10 (0 = first-stage best);
- number of candidates tied at the final (second-stage) IG;
- second-stage IG of the chosen target (best_ig);
- snap distance: |target xy - reachable endpoint xy| for the chosen target;
- reached point: last point of stages/(k+1)/executed_path.json; its distance to target;
- step length of the walk.
No F1/AUC.
"""
import json
import math
import os
import sys

import numpy as np

P = json.load(open("/tmp/cvp_review/work_A/parsed_runs.json"))
RUNS = "/tmp/cvp_review/runs"
COUNTED = [l.strip() for l in open("/tmp/cvp_review/analysis_pre/runs.txt") if l.strip()]


def arm_of(run):
    for a in ("official", "placebo", "filter_only", "oracle_visible"):
        if f"_{a}_" in run:
            return a
    return "?"


def chosen_target(run, k):
    p = os.path.join(RUNS, run, "stages", str(k), "path_log.json")
    if not os.path.exists(p):
        return None
    lines = [json.loads(x) for x in open(p) if x.strip()]
    return lines[-1]["final_path"][-1] if lines else None


def stage_rows(run):
    r = P[run]
    out = []
    ks = sorted(int(x) for x in r["stages"])
    for k in ks:
        s = r["stages"][str(k)]
        tops = s.get("pose_tops") or []
        fins = s.get("pose_finals") or []
        if not tops or not fins:
            continue
        top = np.array(tops[-1]["top"])
        filt = tops[-1]["filtered"]
        fin = fins[-1]
        tgt = chosen_target(run, k)
        if tgt is None:
            continue
        tgt = np.array(tgt[:2])
        # which tied final pose was chosen
        finals = np.array(fin["final"]) if fin["final"] else np.zeros((0, 4))
        news = np.array(fin["new"]) if fin["new"] else np.zeros((0, 4))
        if len(finals):
            j = int(np.argmin(np.hypot(finals[:, 0] - tgt[0], finals[:, 1] - tgt[1])))
            snap = float(np.hypot(*(finals[j, :2] - news[j, :2])))
        else:
            j, snap = None, None
        rank = int(np.argmin(np.hypot(top[:, 0] - tgt[0], top[:, 1] - tgt[1])))
        rank_exact = float(np.min(np.hypot(top[:, 0] - tgt[0], top[:, 1] - tgt[1]))) < 1e-6
        nxt = r["stages"].get(str(k + 1), {})
        w = nxt.get("exec_world") or []
        reached = np.array(w[-1][:2]) if w else None
        start = np.array(w[0][:2]) if w else None
        out.append({
            "stage": k, "n_attempts": len(tops), "rank": rank if rank_exact else None,
            "n_filtered": len(filt), "n_tied": len(finals), "best_ig": fin["best_ig"],
            "top1_xy": top[0, :2].tolist(), "target_xy": tgt.tolist(), "snap": snap,
            "reached_xy": reached.tolist() if reached is not None else None,
            "reach_to_target": float(np.hypot(*(reached - tgt))) if reached is not None else None,
            "start_xy": start.tolist() if start is not None else None,
            "start_to_target": float(np.hypot(*(start - tgt))) if start is not None else None,
            "step_len": nxt.get("exec_len"),
        })
    return out


def main():
    allrows = {}
    for run in sorted(P):
        if run.startswith("dryrun"):
            continue
        allrows[run] = stage_rows(run)
    json.dump(allrows, open("/tmp/cvp_review/work_A/decisions.json", "w"), indent=0)
    # summaries over counted runs per arm
    by_arm = {}
    for run in COUNTED:
        by_arm.setdefault(arm_of(run), []).extend(allrows.get(run, []))
    print("arm            n  top1_chosen  rank_mean  tied>1  ig2==0  ig2<1  snap_med  snap>0.5  reach2tgt_med  start2tgt_med  steplen_med  attempts>1")
    for arm, rows in by_arm.items():
        rows = [x for x in rows]
        n = len(rows)
        ranks = [x["rank"] for x in rows if x["rank"] is not None]
        top1 = np.mean([x["rank"] == 0 for x in rows])
        tied = np.mean([x["n_tied"] > 1 for x in rows])
        ig0 = np.mean([abs(x["best_ig"]) < 1e-9 for x in rows])
        ig1 = np.mean([x["best_ig"] < 1.0 for x in rows])
        snaps = [x["snap"] for x in rows if x["snap"] is not None]
        r2t = [x["reach_to_target"] for x in rows if x["reach_to_target"] is not None]
        s2t = [x["start_to_target"] for x in rows if x["start_to_target"] is not None]
        sl = [x["step_len"] for x in rows if x["step_len"] is not None]
        att = np.mean([x["n_attempts"] > 1 for x in rows])
        print(f"{arm:13s} {n:3d}  {top1:10.2f}  {np.mean(ranks):8.2f}  {tied:6.2f}  {ig0:6.2f}  {ig1:5.2f}  {np.median(snaps):8.2f}  {np.mean(np.array(snaps)>0.5):8.2f}  {np.median(r2t):12.2f}  {np.median(s2t):12.2f}  {np.median(sl):10.2f}  {att:8.2f}")
    # rank distribution
    for arm, rows in by_arm.items():
        ranks = [x["rank"] for x in rows if x["rank"] is not None]
        print(arm, "rank histogram", np.bincount(ranks, minlength=10).tolist(), "n_filtered mean", round(np.mean([x['n_filtered'] for x in rows]), 2))


if __name__ == "__main__":
    main()
