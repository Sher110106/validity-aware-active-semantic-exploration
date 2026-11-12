#!/usr/bin/env python3
"""E3 approach-gap ceilings with the EXACT eligible sets.
Eligible set per stage/track = live_policy.oracle_eligible(observed graph, oracle_sets.json objects),
the same call stage_diagnostics.py (the gate) makes. Stage inclusion follows the gate: stage k needs
observed graphs at k and k+1 and a non-empty stages/(k+1)/executed_path.json. Uses paths, observed
graphs and hypothesis files only. No mapping outcome, no F1, no AUC.

Per (stage, track) unit with both drawn and undrawn eligible objects:
  live          robot's reached point (last point of stages/(k+1)/executed_path.json)
  random_drawn  standing on a drawn object: expectation over all drawn objects (exact),
                plus A's convention (one random drawn object, rng 11) for comparison
  max_drawn     0.5 m grid point(s) with the most drawn objects within 3.5 m (mean over ties)
  best_gap      grid point with the largest drawn-minus-undrawn approach gap (upper bound)
Two summaries: 'unit_mean' (mean of per-unit gaps, A's convention) and 'pooled' (rows pooled
over units, the gate's convention). Live share of max_drawn ceiling with a stage-bootstrap
95% CI (stages resampled within run, both tracks kept together, 2000 draws).
Validation: the pooled live gap over ALL gate rows must equal the gate file's approach gap.
Output: e3_ceiling_exact.json"""
import glob
import importlib.util
import json
import os
import re
import sys

sys.dont_write_bytecode = True
import numpy as np  # noqa: E402
import yaml  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "live_policy_ro", "/Users/sher/project/cvp/project/tools/live_policy/live_policy.py")
lp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lp)

RUNS = "/tmp/cvp_review/runs"
SETS = json.load(open("/tmp/cvp_review/refs/oracle_sets.json"))["scenes"]
OUT = "/tmp/cvp_review/audit/tables/e3_ceiling_exact.json"
R = 3.5
B = 2000
GATES = {
    "e3_00853_s42_oracle_visible_60m_FAILED_ATTEMPT1_gate": "/tmp/cvp_review/gates/E3_gate_00853_s42.json",
    "e3_00853_s42_oracle_visible_60m_rerun1": "/tmp/cvp_review/gates/E3_gate_00853_s42_rerun1.json",
    "e3_00853_s43_oracle_visible_60m": "/tmp/cvp_review/gates/E3_gate_00853_s43.json",
    "e3_00871_s42_oracle_visible_60m": "/tmp/cvp_review/gates/E3_gate_00871_s42.json",
    "e3_00871_s43_oracle_visible_60m": "/tmp/cvp_review/gates/E3_gate_00871_s43.json",
}


def load(p):
    with open(p) as f:
        return yaml.safe_load(f) or {"nodes": []}


def key_of(name, pos):
    return (lp._label(name), tuple(round(v, 3) for v in lp._vec(pos)))


def units_for(run):
    scene = str(int(re.search(r"_(\d{5})_s", run).group(1)))
    cands = SETS[scene]["objects"]
    sd = f"{RUNS}/{run}/stages"
    ks = sorted(int(d) for d in os.listdir(sd) if d.isdigit())
    units = []
    for k in ks:
        nxt = f"{sd}/{k + 1}"
        if not os.path.isdir(nxt):
            continue
        obs_k = {t: load(f"{sd}/{k}/habitat_scene_graph_original_graph{t}.yaml") for t in (0, 1)
                 if os.path.exists(f"{sd}/{k}/habitat_scene_graph_original_graph{t}.yaml")}
        obs_k1 = [t for t in (0, 1) if os.path.exists(f"{nxt}/habitat_scene_graph_original_graph{t}.yaml")]
        ep = f"{nxt}/executed_path.json"
        w = json.load(open(ep)).get("world_frame_path") if os.path.exists(ep) else None
        if not obs_k or not w or not obs_k1:
            continue
        rx, ry = float(w[-1][0]), float(w[-1][1])
        for t, g in obs_k.items():
            elig = lp.oracle_eligible(g, cands)
            if not elig:
                continue
            obs_ids = {n["id"] for n in g.get("nodes") or []}
            dk = set()
            for f in glob.glob(f"{sd}/{k}/habitat_scene_graph_new_graph_*.yaml"):
                gid = int(re.search(r"_(\d+)\.yaml$", f).group(1))
                if gid // 4 != t:
                    continue
                for n in load(f).get("nodes") or []:
                    if n.get("node_type") == "object" and n["id"] not in obs_ids and "position" in n:
                        dk.add(key_of(n.get("name", ""), n["position"]))
            pts = np.array([c["position"][:2] for c in elig], float)
            drawn = np.array([key_of(c["name"], c["position"]) in dk for c in elig])
            units.append({"stage": k, "track": t, "pts": pts, "drawn": drawn, "live": (rx, ry)})
    return units


def appr(pts, x, y):
    return np.hypot(pts[:, 0] - x, pts[:, 1] - y) <= R


def unit_ceilings(u, rng):
    pts, dr = u["pts"], u["drawn"]
    out = {"n_d": int(dr.sum()), "n_u": int((~dr).sum())}
    # approach counts (drawn approached, undrawn approached) per strategy, for pooling
    live = appr(pts, *u["live"])
    out["live"] = (int(live[dr].sum()), int(live[~dr].sum()))
    if not dr.any() or dr.all():
        out["mixed"] = False
        return out
    out["mixed"] = True
    # random drawn object: exact expectation over drawn standing points
    D = np.nonzero(dr)[0]
    M = np.hypot(pts[D, None, 0] - pts[None, :, 0], pts[D, None, 1] - pts[None, :, 1]) <= R  # |D| x n
    out["random_drawn"] = (float(M[:, dr].sum(1).mean()), float(M[:, ~dr].sum(1).mean()))
    j = rng.choice(D)
    a1 = appr(pts, *pts[j])
    out["random_drawn_single"] = (int(a1[dr].sum()), int(a1[~dr].sum()))
    xs = np.arange(pts[:, 0].min() - 1, pts[:, 0].max() + 1, 0.5)
    ys = np.arange(pts[:, 1].min() - 1, pts[:, 1].max() + 1, 0.5)
    G = np.array([(x, y) for x in xs for y in ys])
    A = np.hypot(G[:, None, 0] - pts[None, :, 0], G[:, None, 1] - pts[None, :, 1]) <= R
    cd, cu = A[:, dr].sum(1), A[:, ~dr].sum(1)
    best = np.flatnonzero(cd == cd.max())
    out["max_drawn"] = (float(cd[best].mean()), float(cu[best].mean()))
    gaps = cd / dr.sum() - cu / (~dr).sum()
    b = int(np.argmax(gaps))
    out["best_gap"] = (float(cd[b]), float(cu[b]))
    return out


STRATS = ["live", "random_drawn", "random_drawn_single", "max_drawn", "best_gap"]


def summarize(U, only_mixed=True):
    V = [u for u in U if u["mixed"]] if only_mixed else U
    res = {}
    for s in STRATS:
        if only_mixed or s == "live":
            per = [u[s][0] / u["n_d"] - u[s][1] / u["n_u"] for u in V if u["n_d"] and u["n_u"]]
            nd = sum(u["n_d"] for u in V)
            nu = sum(u["n_u"] for u in V)
            res[s] = {"unit_mean": float(np.mean(per)) if per else float("nan"),
                      "pooled": sum(u[s][0] for u in V) / nd - sum(u[s][1] for u in V) / nu if nd and nu else float("nan")}
    return res


def main():
    rng = np.random.default_rng(11)
    out = {}
    for run in sorted(GATES):
        U0 = units_for(run)
        U = []
        for u in U0:
            c = unit_ceilings(u, rng)
            c.update(stage=u["stage"], track=u["track"])
            U.append(c)
        gate = json.load(open(GATES[run]))[0]
        allg = summarize(U, only_mixed=False)["live"]["pooled"]
        o = {"gate_file": GATES[run],
             "gate_approach_gap": gate["gate"]["all"]["approach"]["gap"],
             "gate_p_one_sided": gate["gate"]["all"]["approach"]["p_one_sided"],
             "gate_n_drawn": gate["gate"]["all"]["approach"]["n_drawn"],
             "gate_n_undrawn": gate["gate"]["all"]["approach"]["n_undrawn"],
             "gate_stages_used": gate["stages_used"],
             "recomputed_live_gap_all_rows": allg,
             "recomputed_n_drawn": sum(u["n_d"] for u in U), "recomputed_n_undrawn": sum(u["n_u"] for u in U),
             "recomputed_stages": len({u["stage"] for u in U}),
             "units_all": len(U), "units_mixed": sum(u["mixed"] for u in U),
             "units_all_drawn": sum(1 for u in U if u["n_d"] and not u["n_u"]),
             "units_no_drawn": sum(1 for u in U if u["n_u"] and not u["n_d"]),
             "mixed": summarize(U)}
        m = o["mixed"]
        for conv in ("unit_mean", "pooled"):
            o[f"live_share_of_max_drawn_{conv}"] = m["live"][conv] / m["max_drawn"][conv]
        # stage bootstrap of the share (pooled and unit_mean)
        stages = sorted({u["stage"] for u in U if u["mixed"]})
        by_stage = {s: [u for u in U if u["mixed"] and u["stage"] == s] for s in stages}
        bs = {"unit_mean": [], "pooled": []}
        brng = np.random.default_rng(20261029)
        for _ in range(B):
            pick = brng.integers(0, len(stages), len(stages))
            V = [u for i in pick for u in by_stage[stages[i]]]
            sm = summarize(V)
            for conv in bs:
                den = sm["max_drawn"][conv]
                bs[conv].append(sm["live"][conv] / den if den > 0 else np.nan)
        for conv in bs:
            a = np.array(bs[conv])
            o[f"live_share_ci95_{conv}"] = [float(np.nanpercentile(a, 2.5)), float(np.nanpercentile(a, 97.5))]
        out[run] = o
        print(run, json.dumps({k: v for k, v in o.items() if k != "mixed"}), flush=True)
        print("   ", json.dumps(m), flush=True)
    json.dump(out, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
