import json, os, re
import numpy as np
RUNS = "/tmp/cvp_review/runs"
runs = ["e1_00853_s42_official_60m","e1_00853_s43_official_60m","e1_00871_s42_official_60m","e1_00871_s43_official_60m","e1_00871_s44_official_60m",
        "e1_00853_s42_placebo_60m","e1_00853_s43_placebo_60m","e1_00853_s44_placebo_60m","e1_00871_s42_placebo_60m","e1_00871_s43_placebo_60m_rerun1","e1_00871_s44_placebo_60m",
        "e2_00853_s42_filter_only_60m","e2_00853_s43_filter_only_60m","e2_00853_s44_filter_only_60m","e2_00871_s42_filter_only_60m","e2_00871_s43_filter_only_60m","e2_00871_s44_filter_only_60m",
        "e3_00853_s42_oracle_visible_60m_rerun1","e3_00853_s43_oracle_visible_60m","e3_00871_s42_oracle_visible_60m","e3_00871_s43_oracle_visible_60m"]
agg = {}
for r in runs:
    arm = re.search(r"(official|placebo|filter_only|oracle_visible)", r).group(1)
    scene = re.search(r"_(\d{5})_", r).group(1)
    sd = os.path.join(RUNS, r, "stages")
    lens, disp, cum = [], [], 0.0
    for k in sorted(int(s) for s in os.listdir(sd) if s.isdigit()):
        ep = os.path.join(sd, str(k), "executed_path.json")
        if not os.path.exists(ep): continue
        P = np.array(json.load(open(ep))["world_frame_path"])
        if len(P) < 2: continue
        L = float(np.sum(np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1)))
        if cum >= 60.0: break
        cum += L
        lens.append(L); disp.append(float(np.linalg.norm(P[-1, :2] - P[0, :2])))
    agg.setdefault((arm, scene), []).append((np.mean(lens), np.median(lens), len(lens), np.mean(disp)))
print("arm scene | mean step path m (per run) | steps to 60 m (per run) | mean straight-line displacement m")
for (arm, scene), v in sorted(agg.items()):
    print(arm, scene, "|", [round(x[0], 2) for x in v], "|", [x[2] for x in v], "|", [round(x[3], 2) for x in v])
allv = {}
for (arm, scene), v in agg.items():
    allv.setdefault(arm, []).extend(x[0] for x in v)
print({a: round(float(np.mean(v)), 2) for a, v in allv.items()})
