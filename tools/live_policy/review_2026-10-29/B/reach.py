"""Per stage: chosen target (final_pose), reachable endpoint (new_pose), and where
the robot actually stopped (last point of stages/k+1/executed_path.json).
Also: rank of the chosen pose in the first-stage top-10 list."""
import json, os, re, sys
import numpy as np
RUNS = "/tmp/cvp_review/runs"
runs = ["e1_00853_s42_official_60m","e1_00853_s43_official_60m","e1_00871_s42_official_60m","e1_00871_s43_official_60m","e1_00871_s44_official_60m",
        "e1_00853_s42_placebo_60m","e1_00853_s43_placebo_60m","e1_00853_s44_placebo_60m","e1_00871_s42_placebo_60m","e1_00871_s43_placebo_60m_rerun1","e1_00871_s44_placebo_60m",
        "e2_00853_s42_filter_only_60m","e2_00853_s43_filter_only_60m","e2_00853_s44_filter_only_60m","e2_00871_s42_filter_only_60m","e2_00871_s43_filter_only_60m","e2_00871_s44_filter_only_60m",
        "e3_00853_s42_oracle_visible_60m_rerun1","e3_00853_s43_oracle_visible_60m","e3_00871_s42_oracle_visible_60m","e3_00871_s43_oracle_visible_60m"]
def arm_of(r):
    return re.search(r"(official|placebo|filter_only|oracle_visible)", r).group(1)
agg = {}
rows = []
for r in runs:
    sd = os.path.join(RUNS, r, "stages")
    ks = sorted(int(s) for s in os.listdir(sd) if s.isdigit())
    for k in ks:
        pl = os.path.join(sd, str(k), "pose_log.json")
        ep = os.path.join(sd, str(k + 1), "executed_path.json")
        if not (os.path.exists(pl) and os.path.exists(ep)):
            continue
        lines = [json.loads(l) for l in open(pl) if l.strip()]
        tops = [l for l in lines if "best_sample_poses" in l]
        finals = [l for l in lines if "final_pose" in l]
        if not finals or not finals[-1]["final_pose"]:
            continue
        fin = finals[-1]
        tgt = np.array(fin["final_pose"][0]); newp = np.array(fin["new_pose"][0])
        path = json.load(open(ep))["world_frame_path"]
        if not path:
            continue
        stop = np.array(path[-1]); start = np.array(path[0])
        top = tops[-1]["best_filtered_poses"] or tops[-1]["best_sample_poses"]
        rank = None
        for i, p in enumerate(top):
            if np.allclose(p, tgt[:4]):
                rank = i + 1
        n_retry = len(tops)
        d_tgt_stop = float(np.linalg.norm(tgt[:2] - stop[:2]))
        d_new_stop = float(np.linalg.norm(newp[:2] - stop[:2]))
        d_tgt_new = float(np.linalg.norm(tgt[:2] - newp[:2]))
        d_start_tgt = float(np.linalg.norm(tgt[:2] - start[:2]))
        d_start_stop = float(np.linalg.norm(stop[:2] - start[:2]))
        rows.append((r, arm_of(r), k, rank, n_retry, d_tgt_new, d_tgt_stop, d_new_stop, d_start_tgt, d_start_stop, len(fin["final_pose"])))
arms = ["official", "placebo", "filter_only", "oracle_visible"]
print("arm | stages | target unreachable (new_pose >0.1 m from target) | median target->stop m | median new_pose->stop m | median start->target | median start->stop | chosen rank distribution (1..10) | ties>1")
for a in arms:
    R = [x for x in rows if x[1] == a]
    unreach = np.mean([x[5] > 0.1 for x in R])
    ranks = [x[3] for x in R if x[3] is not None]
    hist = np.bincount(ranks, minlength=11)[1:]
    print(a, len(R), "%.2f" % unreach, "%.2f" % np.median([x[6] for x in R]), "%.2f" % np.median([x[7] for x in R]),
          "%.2f" % np.median([x[8] for x in R]), "%.2f" % np.median([x[9] for x in R]), list(hist), sum(1 for x in R if x[10] > 1))
allR = rows
print("ALL", len(allR), "unreachable share %.2f" % np.mean([x[5] > 0.1 for x in allR]),
      "stop within 1 m of target: %.2f" % np.mean([x[6] < 1.0 for x in allR]),
      "stop within 1 m of new_pose: %.2f" % np.mean([x[7] < 1.0 for x in allR]),
      "rank1 chosen share: %.2f" % np.mean([x[3] == 1 for x in allR if x[3]]))
