#!/usr/bin/env python3
"""Parse planner logs, pose logs and executed paths of every run (read-only).

Output: /tmp/cvp_review/work_A/parsed_runs.json
Per run: list of planning attempts (log order) and per-stage records.
No F1/AUC is computed here.
"""
import glob
import json
import math
import os
import re

RUNS = "/tmp/cvp_review/runs"
OUT = "/tmp/cvp_review/work_A/parsed_runs.json"

re_bounds = re.compile(r"Sampling (\d+) viewpoints within bounds: \[([^\]]*)\] to \[([^\]]*)\]")
re_hig = re.compile(r"Highest Combined Information Gain found at first stage: (-?[\d.]+|nan|-?inf)")
re_eval = re.compile(r"Evaluating reachability for (\d+) candidates")
re_sel = re.compile(r"selected target pose with IG: (\S+)")
re_vp = re.compile(r"Selected Viewpoint: \[([^\]]*)\]")
re_end = re.compile(r"Ending stage (\d+)")
re_done = re.compile(r"\[Scene (\d+), Ensemble (\d+), GraphID (\d+)\] Done")
re_err = re.compile(r"Error during planning: (.*)")


def floats(s):
    return [float(x) for x in s.replace(",", " ").split()]


def parse_log(path):
    attempts = []
    cur = None
    done_order = []
    stage = 0
    with open(path, errors="replace") as f:
        for line in f:
            m = re_done.search(line)
            if m:
                done_order.append(int(m.group(3)))
                continue
            m = re_bounds.search(line)
            if m:
                cur = {"stage": stage, "low": floats(m.group(2)), "high": floats(m.group(3)),
                       "done_order": done_order, "astar_fail": 0, "skipped": 0}
                done_order = []
                attempts.append(cur)
                continue
            if cur is None:
                m = re_end.search(line)
                if m:
                    stage = int(m.group(1)) + 1
                continue
            m = re_hig.search(line)
            if m:
                cur["first_stage_best"] = float(m.group(1))
                continue
            m = re_eval.search(line)
            if m:
                cur["n_eval"] = int(m.group(1))
                continue
            if "Mid planner cannot find endpoint" in line:
                cur["astar_fail"] += 1
                continue
            if "Skipping this candidate" in line:
                cur["skipped"] += 1
                continue
            m = re_sel.search(line)
            if m:
                cur["selected_ig"] = float(m.group(1))
                continue
            m = re_vp.search(line)
            if m:
                cur["viewpoint"] = floats(m.group(1))
                continue
            m = re_err.search(line)
            if m:
                cur["error"] = m.group(1)[:200]
                continue
            m = re_end.search(line)
            if m:
                stage = int(m.group(1)) + 1
                continue
    return attempts


def path_len_xy(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def parse_stage(d):
    rec = {}
    pl = os.path.join(d, "pose_log.json")
    if os.path.exists(pl):
        tops, finals = [], []
        for line in open(pl):
            line = line.strip()
            if not line:
                continue
            j = json.loads(line)
            if "best_sample_poses" in j:
                tops.append({"top": j["best_sample_poses"], "filtered": j["best_filtered_poses"]})
            else:
                finals.append({"final": j["final_pose"], "new": j["new_pose"], "best_ig": j["best_ig"]})
        rec["pose_tops"] = tops
        rec["pose_finals"] = finals
    ep = os.path.join(d, "executed_path.json")
    if os.path.exists(ep):
        j = json.load(open(ep))
        w = j.get("world_frame_path") or []
        rec["exec_world"] = w
        rec["exec_len"] = path_len_xy(w)
    lp = os.path.join(d, "live_policy.jsonl")
    if os.path.exists(lp):
        rec["live_policy"] = [json.loads(x) for x in open(lp) if x.strip()]
    rec["has_obs"] = all(os.path.exists(os.path.join(d, f"habitat_scene_graph_original_graph{t}.yaml")) for t in (0, 1))
    rec["n_hyp"] = len(glob.glob(os.path.join(d, "habitat_scene_graph_new_graph_*.yaml")))
    return rec


def main():
    out = {}
    for run in sorted(os.listdir(RUNS)):
        rd = os.path.join(RUNS, run)
        log = os.path.join(rd, "logs", "exploration_pipeline.log")
        attempts = parse_log(log) if os.path.exists(log) else []
        stages = {}
        for d in glob.glob(os.path.join(rd, "stages", "*")):
            b = os.path.basename(d)
            if b.isdigit():
                stages[int(b)] = parse_stage(d)
        cfg = {}
        cp = os.path.join(rd, "config", "pipeline_config.yaml")
        if os.path.exists(cp):
            for line in open(cp):
                m = re.match(r"^(SEED|SCENE_NUMBER):\s*(\d+)", line)
                if m:
                    cfg[m.group(1)] = int(m.group(2))
        out[run] = {"attempts": attempts, "stages": {str(k): v for k, v in sorted(stages.items())}, "cfg": cfg}
    json.dump(out, open(OUT, "w"))
    for run, r in out.items():
        n_err = sum(1 for a in r["attempts"] if "error" in a)
        cum = 0.0
        for k in sorted(int(x) for x in r["stages"]):
            cum += r["stages"][str(k)].get("exec_len", 0.0)
        print(f"{run:60s} attempts={len(r['attempts']):3d} errors={n_err:2d} stages={len(r['stages']):3d} path={cum:6.1f}")


if __name__ == "__main__":
    main()
