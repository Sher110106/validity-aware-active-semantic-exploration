#!/usr/bin/env python3
"""Summarize cf_stages.jsonl: median/IQR per arm of the per-stage rho under each
hypothesis condition on identical states and candidates. Writes cf_summary.json."""
import json
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(f"{OUT}/cf_stages.jsonl") if "error" not in l]


def q(x):
    x = np.array([v for v in x if v is not None], float)
    return {"n": int(len(x)), "median": float(np.median(x)), "q25": float(np.percentile(x, 25)),
            "q75": float(np.percentile(x, 75))} if len(x) else None


res = {"n_stages": len(R), "by_arm": {}}
for a in ["official", "placebo", "filter_only", "oracle_visible", "ALL"]:
    rows = [r for r in R if a == "ALL" or r["arm"] == a]
    b = {"n": len(rows)}
    for c in ("actual", "obs", "plc", "orc"):
        for m in ("rho_total_U360", "rho_total_Ucone", "rho_ig_U360"):
            b[f"{c}:{m}"] = q([r[c][m] for r in rows])
        b[f"{c}:ig_zero_frac_mean"] = float(np.mean([r[c]["ig_zero_frac"] for r in rows]))
    # paired: actual minus plc, orc minus plc (rho_total_U360)
    for m in ("rho_total_U360", "rho_total_Ucone"):
        b[f"paired_actual_minus_plc:{m}"] = q([r["actual"][m] - r["plc"][m] for r in rows
                                                if r["actual"][m] is not None and r["plc"][m] is not None])
        b[f"paired_orc_minus_plc:{m}"] = q([r["orc"][m] - r["plc"][m] for r in rows
                                             if r["orc"][m] is not None and r["plc"][m] is not None])
    b["frontier:rho_dwalk_U360"] = q([r.get("frontier_proxy", {}).get("rho_dwalk_U360") for r in rows])
    b["frontier:rho_dwalk_Ucone"] = q([r.get("frontier_proxy", {}).get("rho_dwalk_Ucone") for r in rows])
    res["by_arm"][a] = b
json.dump(res, open(f"{OUT}/cf_summary.json", "w"), indent=1)
for a, b in res["by_arm"].items():
    print(a, b["n"])
    for k, v in b.items():
        if isinstance(v, dict):
            print("   ", k, v["n"], round(v["median"], 3), [round(v["q25"], 3), round(v["q75"], 3)])
        elif k != "n":
            print("   ", k, round(v, 3))
