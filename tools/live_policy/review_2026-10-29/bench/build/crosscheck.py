#!/usr/bin/env python3
"""Cross-checks of stages.jsonl against the earlier audit (stages.jsonl there):
U_360 yardstick counts at the stop, U_360 max/mean over candidates, and the
number of candidates. Writes crosscheck.json."""
import json
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
A = {(r["run"], r["stage"]): r for r in map(json.loads, open("/tmp/cvp_review/audit/audit/stages.jsonl"))}
mine = [r for r in map(json.loads, open(os.path.join(OUT, "stages.jsonl"))) if "error" not in r and "drop" not in r]
res = {"n": len(mine), "yard_U360_equal": 0, "yard_compared": 0, "U360_max_equal": 0, "U360_mean_absdiff_max": 0.0,
       "n_cand_equal": 0, "mismatches": []}
for r in mine:
    a = A[(r["run"], r["stage"])]
    U3 = np.array(r["U360"])
    if a["U360_max"] == int(U3.max()):
        res["U360_max_equal"] += 1
    res["U360_mean_absdiff_max"] = max(res["U360_mean_absdiff_max"], abs(a["U360_mean"] - U3.mean()))
    res["n_cand_equal"] += int(a["n_cand"] == r["n_cand"])
    if a.get("yard") and r.get("yard"):
        res["yard_compared"] += 1
        y, m = a["yard"], r["yard"]["U360"]
        same = (y["n_in"], y["in_mapped_sl"], y["n_out"], y["out_mapped_sl"]) == (m["n_in"], m["in_mapped"], m["n_out"],
                                                                                   m["out_mapped"])
        res["yard_U360_equal"] += int(same)
        if not same:
            res["mismatches"].append([r["run"], r["stage"], y, m])
json.dump(res, open(os.path.join(OUT, "crosscheck.json"), "w"), indent=1)
print({k: v for k, v in res.items() if k != "mismatches"}, len(res["mismatches"]))
