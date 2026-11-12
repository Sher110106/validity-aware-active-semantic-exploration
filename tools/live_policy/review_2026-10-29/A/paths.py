#!/usr/bin/env python3
"""Compare where runs go: per-stage reached viewpoints and swept-area overlap.

Pairs of runs on the same scene are grouped as:
  same_arm_same_seed   (a counted run vs an archived attempt of the same arm and seed)
  diff_arm_same_seed   (e.g. official vs placebo, seed 42)
  same_arm_diff_seed
  diff_arm_diff_seed
For each pair: first stage at which reached viewpoints differ by > 0.5 m, the
distance at stages 0..5, and the Jaccard overlap of the area within r metres
of the walked path up to 30 m and 60 m of path. Uses only executed paths.
No F1/AUC.
"""
import itertools
import json
import math
import os
import re

import numpy as np

RUNS = "/tmp/cvp_review/runs"
P = json.load(open("/tmp/cvp_review/work_A/parsed_runs.json"))
CELL = 0.1


def arm_of(run):
    for a in ("official", "placebo", "filter_only", "oracle_visible"):
        if f"_{a}_" in run:
            return a
    return "?"


def info(run):
    m = re.search(r"_(\d{5})_s(\d+)_", run)
    return m.group(1), int(m.group(2))


def walk(run):
    """Concatenated world-frame path (xy) and per-stage reached points."""
    st = P[run]["stages"]
    ks = sorted(int(k) for k in st)
    pts, reached = [], {}
    for k in ks:
        w = st[str(k)].get("exec_world") or []
        if not w:
            continue
        xy = [(p[0], p[1]) for p in w]
        pts.extend(xy)
        reached[k - 1] = np.array(xy[-1])  # walk in folder k is driven after stage k-1's plan
    return np.array(pts), reached


def truncate(pts, L):
    if len(pts) < 2:
        return pts
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    keep = cum <= L
    return pts[keep]


def total_len(pts):
    return float(np.sum(np.hypot(*np.diff(pts, axis=0).T))) if len(pts) > 1 else 0.0


def raster(pts, r):
    if len(pts) == 0:
        return set()
    dense = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(math.ceil(np.hypot(*(b - a)) / 0.05)))
        for t in range(1, n + 1):
            dense.append(a + (b - a) * t / n)
    dense = np.array(dense)
    cells = set()
    R = int(math.ceil(r / CELL))
    offs = [(i, j) for i in range(-R, R + 1) for j in range(-R, R + 1) if (i * CELL) ** 2 + (j * CELL) ** 2 <= r * r]
    base = np.unique(np.floor(dense / CELL).astype(int), axis=0)
    for (cx, cy) in base:
        for (i, j) in offs:
            cells.add((cx + i, cy + j))
    return cells


def jacc(a, b):
    return len(a & b) / len(a | b) if (a or b) else float("nan")


def main():
    runs = [r for r in P if not r.startswith("dryrun") and P[r]["stages"]]
    data = {}
    for r in runs:
        pts, reached = walk(r)
        if len(pts) < 2:
            continue
        data[r] = {"pts": pts, "reached": reached, "len": total_len(pts)}
    counted = [l.strip() for l in open("/tmp/cvp_review/analysis_pre/runs.txt") if l.strip()]
    rows = []
    cache = {}

    def cov(r, L, rad):
        key = (r, L, rad)
        if key not in cache:
            cache[key] = raster(truncate(data[r]["pts"], L), rad)
        return cache[key]

    for a, b in itertools.combinations(sorted(data), 2):
        sa, ea = info(a)
        sb, eb = info(b)
        if sa != sb:
            continue
        a_c, b_c = a in counted, b in counted
        if not (a_c or b_c):
            continue
        same_arm = arm_of(a) == arm_of(b)
        same_seed = ea == eb
        kind = ("same_arm" if same_arm else "diff_arm") + "_" + ("same_seed" if same_seed else "diff_seed")
        if not (a_c and b_c) and kind != "same_arm_same_seed":
            continue  # archived attempts only serve as same-arm same-seed replicates
        ra, rb = data[a]["reached"], data[b]["reached"]
        ks = sorted(set(ra) & set(rb))
        dists = [float(np.hypot(*(ra[k] - rb[k]))) for k in ks]
        first_div = next((k for k, dd in zip(ks, dists) if dd > 0.5), None)
        row = {"a": a, "b": b, "scene": sa, "kind": kind, "arms": f"{arm_of(a)}|{arm_of(b)}",
               "first_div": first_div, "d_stage": dict(zip([str(k) for k in ks[:8]], dists[:8])),
               "common_stages": len(ks)}
        Lmax = min(data[a]["len"], data[b]["len"])
        for L in (10, 30, 60):
            if Lmax + 1e-6 < L and L != 10:
                row[f"J{L}_r2"] = None
                continue
            row[f"J{L}_r2"] = jacc(cov(a, L, 2.0), cov(b, L, 2.0))
            row[f"J{L}_r3"] = jacc(cov(a, L, 3.0), cov(b, L, 3.0))
        rows.append(row)
    json.dump(rows, open("/tmp/cvp_review/work_A/paths_pairs.json", "w"), indent=0)
    # summaries
    for scene in ("00853", "00871"):
        print("=== scene", scene)
        for kind in ("same_arm_same_seed", "diff_arm_same_seed", "same_arm_diff_seed", "diff_arm_diff_seed"):
            rs = [r for r in rows if r["scene"] == scene and r["kind"] == kind]
            if not rs:
                continue
            fd = [r["first_div"] for r in rs]
            d0 = [r["d_stage"].get("0") for r in rs if r["d_stage"].get("0") is not None]
            d1 = [r["d_stage"].get("1") for r in rs if r["d_stage"].get("1") is not None]
            j30 = [r.get("J30_r3") for r in rs if r.get("J30_r3") is not None]
            j60 = [r.get("J60_r3") for r in rs if r.get("J60_r3") is not None]
            j30b = [r.get("J30_r2") for r in rs if r.get("J30_r2") is not None]
            j10 = [r.get("J10_r3") for r in rs if r.get("J10_r3") is not None]
            print(f"{kind:20s} n={len(rs):3d} first_div={fd} "
                  f"d0_med={np.median(d0) if d0 else float('nan'):.2f} d1_med={np.median(d1) if d1 else float('nan'):.2f} "
                  f"J10r3={np.mean(j10) if j10 else float('nan'):.2f} J30r3={np.mean(j30) if j30 else float('nan'):.2f} "
                  f"J30r2={np.mean(j30b) if j30b else float('nan'):.2f} J60r3={np.mean(j60) if j60 else float('nan'):.2f} (n60={len(j60)})")
    print()
    for r in rows:
        if r["kind"] in ("same_arm_same_seed", "diff_arm_same_seed"):
            print(r["kind"], r["a"], "<>", r["b"], "first_div", r["first_div"],
                  {k: round(v, 2) for k, v in list(r["d_stage"].items())[:5]},
                  "J10", None if r.get("J10_r3") is None else round(r["J10_r3"], 2),
                  "J30", None if r.get("J30_r3") is None else round(r["J30_r3"], 2),
                  "J60", None if r.get("J60_r3") is None else round(r["J60_r3"], 2))


if __name__ == "__main__":
    main()
