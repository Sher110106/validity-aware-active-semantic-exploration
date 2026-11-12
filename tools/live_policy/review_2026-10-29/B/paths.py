"""Light path check on copied run data ($0, offline).
For each counted run: per-stage chosen target (pose_log final_pose), stage start
positions, and the executed path in world frame. Reports when same-seed runs in
different arms first choose targets more than X m apart, and how much of the
swept area (cells within R m of the path) two runs share, across arms vs across seeds."""
import json, os, sys, glob, re, itertools
import numpy as np

RUNS = "/tmp/cvp_review/runs"
COUNTED = None

def stages_of(run):
    d = os.path.join(RUNS, run, "stages")
    return sorted([int(s) for s in os.listdir(d) if s.isdigit()])

def load_run(run):
    out = {"targets": [], "paths": [], "stage_dirs": []}
    for k in stages_of(run):
        sd = os.path.join(RUNS, run, "stages", str(k))
        pl = os.path.join(sd, "pose_log.json")
        tgt = None
        if os.path.exists(pl):
            lines = [json.loads(l) for l in open(pl) if l.strip()]
            finals = [l for l in lines if "final_pose" in l]
            if finals:
                fp = finals[-1]["final_pose"]
                if fp:
                    tgt = fp[0]
        out["targets"].append((k, tgt))
        ep = os.path.join(sd, "executed_path.json")
        if os.path.exists(ep):
            p = json.load(open(ep)).get("world_frame_path") or []
            out["paths"].append((k, np.array(p) if p else np.zeros((0, 3))))
    return out

def path_len(p):
    return float(np.sum(np.linalg.norm(np.diff(p[:, :2], axis=0), axis=1))) if len(p) > 1 else 0.0

def cum_path(run):
    r = load_run(run)
    pts = [p for _, p in r["paths"] if len(p)]
    return np.vstack(pts) if pts else np.zeros((0, 3)), r

def swept_cells(P, R=2.0, cell=0.25, upto_m=None):
    if len(P) == 0:
        return set()
    if upto_m is not None:
        seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1))]
        P = P[seg <= upto_m]
    cells = set()
    r = int(np.ceil(R / cell))
    offs = [(i, j) for i in range(-r, r + 1) for j in range(-r, r + 1) if (i * cell) ** 2 + (j * cell) ** 2 <= R * R]
    base = set(map(tuple, np.floor(P[:, :2] / cell).astype(int)))
    for (a, b) in base:
        for (i, j) in offs:
            cells.add((a + i, b + j))
    return cells

def jacc(a, b):
    return len(a & b) / max(1, len(a | b))

if __name__ == "__main__":
    runs = sorted(os.listdir(RUNS))
    pat = re.compile(r"^e(\d)_(\d{5})_s(\d+)_(official|placebo|filter_only|oracle_visible)_60m(_rerun\d+)?$")
    counted = {}
    for r in runs:
        m = pat.match(r)
        if not m:
            continue
        key = (m.group(2), int(m.group(3)), m.group(4))
        # prefer reruns where present (the counted cell); listed below for audit
        counted.setdefault(key, []).append(r)
    for k, v in sorted(counted.items()):
        print(k, v)

def final_at(rec, budget=60.0, key='af_f1'):
    st = [s for s in rec['hm3d_stages'] if s['path_m'] is not None and s['path_m'] <= budget + 1e-6]
    return st[-1][key] if st else None

def main2():
    scores = json.load(open('/tmp/cvp_review/analysis_pre/scores_e1_e2.json'))
    byrun = {os.path.basename(r['run_dir']): r for r in scores}
    counted = ["e1_00853_s42_official_60m","e1_00853_s42_placebo_60m","e1_00853_s43_official_60m","e1_00853_s43_placebo_60m","e1_00853_s44_placebo_60m",
               "e1_00871_s42_official_60m","e1_00871_s42_placebo_60m","e1_00871_s43_official_60m","e1_00871_s43_placebo_60m_rerun1","e1_00871_s44_official_60m","e1_00871_s44_placebo_60m",
               "e2_00853_s42_filter_only_60m","e2_00853_s43_filter_only_60m","e2_00853_s44_filter_only_60m","e2_00871_s42_filter_only_60m","e2_00871_s43_filter_only_60m","e2_00871_s44_filter_only_60m"]
    oracle = ["e3_00853_s42_oracle_visible_60m_rerun1","e3_00853_s43_oracle_visible_60m","e3_00871_s42_oracle_visible_60m","e3_00871_s43_oracle_visible_60m"]
    pat = re.compile(r"^e\d_(\d{5})_s(\d+)_(official|placebo|filter_only|oracle_visible)_60m(_rerun\d+)?$")
    info = {}
    print("run, arm, final_m, F1@60 (hm3d af), P@60, R@60, AUC60, stages")
    for r in counted + oracle:
        m = pat.match(r); scene, seed, arm = m.group(1), int(m.group(2)), m.group(3)
        P, rr = cum_path(r)
        info[r] = dict(scene=scene, seed=seed, arm=arm, P=P, targets=rr['targets'])
        if r in byrun:
            rec = byrun[r]
            print(r, arm, round(rec['final_path_m'],1), round(final_at(rec),3), round(final_at(rec,key='af_precision'),3), round(final_at(rec,key='af_recall'),3), rec['hm3d_auc_af_f1_to_60m'], len(rec['hm3d_stages']))
        else:
            print(r, arm, 'sealed (E3) - no score computed', 'path_m=%.1f' % path_len(P))
    # first-target divergence for same scene+seed across arms
    print("\nFirst chosen targets (stage 0) per scene/seed/arm, xy:")
    groups = {}
    for r, v in info.items():
        groups.setdefault((v['scene'], v['seed']), []).append(r)
    for key, rs in sorted(groups.items()):
        print(key)
        T = {}
        for r in rs:
            tg = [(k, t) for k, t in info[r]['targets'] if t is not None]
            T[r] = tg
            print("   ", info[r]['arm'].ljust(15), [ (k, round(t[0],2), round(t[1],2)) for k,t in tg[:4]])
        for a, b in itertools.combinations(rs, 2):
            ta, tb = T[a], T[b]
            if ta and tb:
                d0 = np.linalg.norm(np.array(ta[0][1][:2]) - np.array(tb[0][1][:2]))
                print("    stage0 target distance %s vs %s: %.2f m" % (info[a]['arm'], info[b]['arm'], d0))
    # swept-area overlap at 20/40/60 m
    print("\nSwept-area Jaccard (cells within 2 m of path), by budget:")
    for budget in (20, 40, 60):
        cells = {r: swept_cells(info[r]['P'], upto_m=budget) for r in info}
        same_arm_diff_seed, diff_arm_same_seed, diff_arm_diff_seed = [], [], []
        for a, b in itertools.combinations(info, 2):
            A, B = info[a], info[b]
            if A['scene'] != B['scene']:
                continue
            j = jacc(cells[a], cells[b])
            if A['arm'] == B['arm'] and A['seed'] != B['seed']:
                same_arm_diff_seed.append(j)
            elif A['arm'] != B['arm'] and A['seed'] == B['seed']:
                diff_arm_same_seed.append(j)
            elif A['arm'] != B['arm']:
                diff_arm_diff_seed.append(j)
        f = lambda x: "n=%d mean=%.3f min=%.3f max=%.3f" % (len(x), np.mean(x), np.min(x), np.max(x)) if x else "n=0"
        print(" %d m | same arm, diff seed: %s | diff arm, same seed: %s | diff arm, diff seed: %s" % (budget, f(same_arm_diff_seed), f(diff_arm_same_seed), f(diff_arm_diff_seed)))
    return info

if __name__ == "__main__":
    main2()
