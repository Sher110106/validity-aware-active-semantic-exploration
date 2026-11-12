"""Cross-check own per-stage F1 and AUC against the author's matcher/loader/AUC."""
import json
import os
import sys

sys.path.insert(0, "/Users/sher/project/cvp/project")
from tools.evaluator.graph_io import load_eval_graph  # noqa: E402
from tools.evaluator.matching import match_objects  # noqa: E402
from tools.asp_offline.evaluator import area_under_curve  # noqa: E402

ROOT = "/Users/sher/cvp_live_campaign_copy/runs"
REFDIR = os.path.join(ROOT, "live_campaign", "hm3d_refs_work")
mine = json.load(open("/tmp/cvp_verify_step7/scores.json"))
refs = {s: load_eval_graph(os.path.join(REFDIR, f"{s}_hm3d_reference.yaml")).objects for s in ("00853", "00871")}
maxdf = 0.0
maxda = 0.0
for name, r in mine["runs"].items():
    if "points" not in r:
        continue
    base = os.path.join(ROOT, "frontier_seeds" if name.startswith("e4_") else "live_campaign", name, "stages")
    rows = []
    for p in r["points"]:
        sd = os.path.join(base, str(p["stage"]))
        f1s = []
        for i in (0, 1):
            g = os.path.join(sd, f"habitat_scene_graph_original_graph{i}.yaml")
            if os.path.isfile(g):
                f1s.append(match_objects(refs[r["scene"]], load_eval_graph(g).objects, 0.5).f1)
        f = sum(f1s) / len(f1s)
        maxdf = max(maxdf, abs(f - p["f1"]))
        rows.append({"path_m": p["x"], "f1": f})
    a60 = area_under_curve(rows, "f1", budget_m=60.0)
    a50 = area_under_curve(rows, "f1", budget_m=50.0)
    maxda = max(maxda, abs(a60 - r["auc60"]), abs(a50 - r["auc50"]))
    print(f"{name:40s} author auc60={a60:.6f} mine={r['auc60']:.6f} author auc50={a50:.6f} mine={r['auc50']:.6f}")
print("max |dF1| stage =", maxdf, " max |dAUC| =", maxda)
