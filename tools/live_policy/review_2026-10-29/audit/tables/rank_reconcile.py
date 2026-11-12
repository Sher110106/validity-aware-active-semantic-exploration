#!/usr/bin/env python3
"""Reconcile Reviewer A's 18% and Reviewer B's 31% top-1 share.
Reads pose_log.json / path_log.json / executed_path.json (read-only) and
/tmp/cvp_review/work_A/decisions.json. No F1/AUC. Output: rank_reconcile.json"""
import json, os, re
import numpy as np

RUNS = "/tmp/cvp_review/runs"
OUT = "/tmp/cvp_review/audit/tables/rank_reconcile.json"
A_RUNS = [l.strip() for l in open("/tmp/cvp_review/analysis_pre/runs.txt") if l.strip()]
B_RUNS = ["e1_00853_s42_official_60m", "e1_00853_s43_official_60m", "e1_00871_s42_official_60m", "e1_00871_s43_official_60m", "e1_00871_s44_official_60m",
          "e1_00853_s42_placebo_60m", "e1_00853_s43_placebo_60m", "e1_00853_s44_placebo_60m", "e1_00871_s42_placebo_60m", "e1_00871_s43_placebo_60m_rerun1", "e1_00871_s44_placebo_60m",
          "e2_00853_s42_filter_only_60m", "e2_00853_s43_filter_only_60m", "e2_00853_s44_filter_only_60m", "e2_00871_s42_filter_only_60m", "e2_00871_s43_filter_only_60m", "e2_00871_s44_filter_only_60m",
          "e3_00853_s42_oracle_visible_60m_rerun1", "e3_00853_s43_oracle_visible_60m", "e3_00871_s42_oracle_visible_60m", "e3_00871_s43_oracle_visible_60m"]
ARMS = ["official", "placebo", "filter_only", "oracle_visible"]


def arm_of(r):
    return re.search(r"(official|placebo|filter_only|oracle_visible)", r).group(1)


def rows_for(run):
    sd = os.path.join(RUNS, run, "stages")
    out = []
    for k in sorted(int(s) for s in os.listdir(sd) if s.isdigit()):
        pl = os.path.join(sd, str(k), "pose_log.json")
        ep = os.path.join(sd, str(k + 1), "executed_path.json")
        pa = os.path.join(sd, str(k), "path_log.json")
        if not os.path.exists(pl):
            continue
        lines = [json.loads(l) for l in open(pl) if l.strip()]
        tops = [l for l in lines if "best_sample_poses" in l]
        finals = [l for l in lines if "final_pose" in l]
        if not tops or not finals or not finals[-1]["final_pose"]:
            continue
        top = np.array(tops[-1]["best_sample_poses"])
        filt = np.array(tops[-1]["best_filtered_poses"]) if tops[-1]["best_filtered_poses"] else None
        fin0 = np.array(finals[-1]["final_pose"][0])
        # target actually published (A's choice): last point of last path_log line
        tgt_path = None
        if os.path.exists(pa):
            pls = [json.loads(x) for x in open(pa) if x.strip()]
            if pls:
                tgt_path = np.array(pls[-1]["final_path"][-1][:2])
        has_exec = os.path.exists(ep) and bool(json.load(open(ep)).get("world_frame_path"))

        def rank_in(lst, t2):
            if lst is None or t2 is None:
                return None
            d = np.hypot(lst[:, 0] - t2[0], lst[:, 1] - t2[1])
            return int(np.argmin(d)) if d.min() < 1e-6 else None
        out.append({
            "run": run, "arm": arm_of(run), "stage": k,
            "has_next_exec": has_exec, "has_path_log": tgt_path is not None,
            "n_tied": len(finals[-1]["final_pose"]), "n_filtered": 0 if filt is None else len(filt),
            "rank_unfilt_pathlog": rank_in(top, tgt_path),          # A's definition
            "rank_unfilt_final0": rank_in(top, fin0[:2]),
            "rank_filt_final0": rank_in(filt if filt is not None else top, fin0[:2]),  # B's definition
            "rank_filt_pathlog": rank_in(filt if filt is not None else top, tgt_path),
            "top1_removed_by_history": bool(filt is not None and not np.allclose(filt[0], top[0])),
        })
    return out


def share(rows, key, val=0):
    allr = len(rows)
    m = [r for r in rows if r[key] is not None]
    hit = sum(1 for r in m if r[key] == val)
    return {"hits": hit, "n_all": allr, "n_matched": len(m),
            "share_all": hit / allr if allr else None, "share_matched": hit / len(m) if m else None}


def hist(rows, key):
    return np.bincount([r[key] for r in rows if r[key] is not None], minlength=10).tolist()


res = {}
allrows = {r: rows_for(r) for r in sorted(set(A_RUNS) | set(B_RUNS))}
for name, runs, filt in [("A_set_A_filter", A_RUNS, lambda r: r["has_path_log"]),
                         ("B_set_B_filter", B_RUNS, lambda r: r["has_next_exec"])]:
    R = [x for run in runs for x in allrows[run] if filt(x)]
    o = {"n": len(R)}
    for key in ["rank_unfilt_pathlog", "rank_unfilt_final0", "rank_filt_final0", "rank_filt_pathlog"]:
        o[key] = {"all": share(R, key), "hist": hist(R, key)}
        o[key]["by_arm"] = {a: share([x for x in R if x["arm"] == a], key) for a in ARMS}
        o[key]["hist_by_arm"] = {a: hist([x for x in R if x["arm"] == a], key) for a in ARMS}
    o["share_top1_removed_by_history"] = float(np.mean([x["top1_removed_by_history"] for x in R]))
    o["share_ties_gt1"] = float(np.mean([x["n_tied"] > 1 for x in R]))
    res[name] = o

# cross-check with decisions.json (A's file)
D = json.load(open("/tmp/cvp_review/work_A/decisions.json"))
DR = [x for r in A_RUNS for x in D.get(r, [])]
res["decisions_json"] = {"n_all": len(DR), "n_rank_matched": sum(1 for x in DR if x["rank"] is not None),
                         "top1_hits": sum(1 for x in DR if x["rank"] == 0),
                         "hist": np.bincount([x["rank"] for x in DR if x["rank"] is not None], minlength=10).tolist()}
for a in ARMS:
    sub = [x for r in A_RUNS if arm_of(r) == a for x in D.get(r, [])]
    res["decisions_json"][a] = {"n_all": len(sub), "n_matched": sum(1 for x in sub if x["rank"] is not None),
                                "top1_hits": sum(1 for x in sub if x["rank"] == 0),
                                "hist": np.bincount([x["rank"] for x in sub if x["rank"] is not None], minlength=10).tolist()}
json.dump(res, open(OUT, "w"), indent=1)
for k, o in res.items():
    print("==", k)
    print(json.dumps(o, indent=None)[:3000])

# chance baseline: share expected if the pick were uniform over the history-filtered list
nf = [x["n_filtered"] for x in DR]
chance = {"uniform_over_filtered_list_mean_1_over_n": float(np.mean([1.0 / n for n in nf if n > 0])),
          "uniform_over_top10": 0.1, "n_filtered_mean": float(np.mean(nf))}
res["chance"] = chance
json.dump(res, open(OUT, "w"), indent=1)
print("chance", chance)
