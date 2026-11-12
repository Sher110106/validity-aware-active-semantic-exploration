"""Independent per-stage recomputation using the PINNED code loop (not fastig):
candidates via pinned_harness.first_stage (pinned _gather_sample_observations),
visibility via pinned UncertaintyCalculator._visible_testing with cu.Camera.
Own unmapped rule, own stop/percentile/yardstick. No F1/AUC."""
import sys, json, os, glob, ast
sys.dont_write_bytecode = True
sys.path.insert(0, "/tmp/cvp_review/work_A")
import numpy as np
np.set_printoptions(legacy="1.25")
import yaml
from scipy.stats import spearmanr
from multiprocessing import Pool
import pinned_harness as ph
import replay as rp
import replay2 as rp2
cu = ph.cu
RUNS = "/tmp/cvp_review/runs"
OUT = "/tmp/cvp_review/audit/verify_audit"
REF = json.load(open("/tmp/cvp_review/refs/oracle_sets.json"))["scenes"]

def V(x): return np.array(ast.literal_eval(x) if isinstance(x, str) else x, float)
def L(n): return str(n).lower().replace("_", " ").strip()

def obs_nodes(run, k):
    ns = []
    for t in (0, 1):
        p = f"{RUNS}/{run}/stages/{k}/habitat_scene_graph_original_graph{t}.yaml"
        if os.path.exists(p):
            ns += [n for n in yaml.safe_load(open(p))["nodes"] if "position" in n]
    return ns

def unmapped(refs, nodes, rule):
    obj = [(L(n["name"]), V(n["position"])[:2]) for n in nodes if n.get("node_type") == "object"]
    st = [(L(n["name"]), V(n["position"])[:2]) for n in nodes if n.get("node_type") == "structure"]
    out = []
    for o in refs:
        xy = np.array(o["position"][:2]); lab = L(o["name"])
        def near(lst, same):
            return any(np.hypot(*(xy - p)) <= 0.5 for l, p in lst if (not same or l == lab))
        if rule == "code":
            m = near(obj, False) or near(st, True)
        else:
            m = near(obj, True) or near(st, True)
        out.append(not m)
    return np.array(out)

def opt_sg(refs, nodes):
    tg = [{"id": f"ref{i}", "name": o["name"], "pos": np.array(o["position"], float),
           "dims": np.array(o["dimension"], float), "orient": np.eye(3)} for i, o in enumerate(refs)]
    oc = []
    for n in nodes:
        nt = n.get("node_type")
        if nt not in ("object", "structure"):
            continue
        isdoor = "door" in str(n.get("name", "")).lower()
        if nt == "structure" or isdoor:
            o = n.get("orientation")
            oc.append({"id": n["id"], "name": n.get("name"), "pos": V(n["position"]), "dims": V(n["dimension"]),
                       "orient": np.eye(3) if o is None else V(o)})
    return {"targets": tg, "occluders": oc}

def visset(calc, sg, pos, yaws, cfg):
    ids = set()
    for y in yaws:
        cam = cu.Camera(config=cfg, position=np.asarray(pos[:3], float), yaw_degrees=float(y))
        v, _, _, _ = calc._visible_testing(sg, cam)
        ids |= set(v)
    return ids

def rho(a, b):
    if np.std(a) == 0 or np.std(b) == 0: return None
    return float(spearmanr(a, b).statistic)

def pct(u, U):
    U = np.asarray(U); return float((np.sum(U < u) + 0.5 * np.sum(U == u)) / len(U))

def last_logged_top(run, k):
    tops = None
    for line in open(f"{RUNS}/{run}/stages/{k}/pose_log.json"):
        line = line.strip()
        if not line: continue
        j = json.loads(line)
        if "best_sample_poses" in j: tops = j["best_sample_poses"]
    return tops

def stage(run, k):
    meta = rp.stage_meta(run)[k]
    seed = int([l.split(":")[1] for l in open(f"{RUNS}/{run}/config/pipeline_config.yaml") if l.startswith("SEED:")][0])
    gids = rp2.gids_for(run, k, meta)
    files = [f"{RUNS}/{run}/stages/{k}/habitat_scene_graph_new_graph_{g}.yaml" for g in gids]
    if k == 0:
        cur = np.array(json.load(open(f"{RUNS}/{run}/stages/1/executed_path.json"))["world_frame_path"][0])
    else:
        cur = np.array(json.load(open(f"{RUNS}/{run}/stages/{k}/executed_path.json"))["world_frame_path"][-1])
    calc = ph.make_calc(seed, meta["nprior"], f"{OUT}/tmp_{run}_{k}")
    os.makedirs(f"{OUT}/tmp_{run}_{k}", exist_ok=True)
    lo, hi, scored, order = ph.first_stage(calc, files, cur)
    poses = np.array([s[2] for s in scored]); total = np.array([s[0] for s in scored])
    logged = last_logged_top(run, k)
    rep = [poses[i] for i in order[:10]]
    match = logged is not None and len(logged) == len(rep) and all(np.allclose(a, b, atol=1e-6) for a, b in zip(logged, rep))
    scene = run.split("_")[1]
    refs = REF[str(int(scene))]["objects"]
    nodes = obs_nodes(run, k)
    un = unmapped(refs, nodes, "code"); un_sl = unmapped(refs, nodes, "samelabel")
    sg = opt_sg(refs, nodes)
    idx = {f"ref{i}": i for i in range(len(refs))}
    c1 = cu.CameraConfig(); c2 = cu.CameraConfig(); c2.near_clip = 0.1; c2.max_range = 4.0
    yaws = np.arange(0, 360, 30.0)
    def U(ids, mask): return int(sum(mask[idx[i]] for i in ids))
    Uc, U3, U3s = [], [], []
    for p in poses:
        ic = visset(calc, sg, p, [p[3]], c1); i3 = visset(calc, sg, p, yaws, c2)
        Uc.append(U(ic, un)); U3.append(U(i3, un)); U3s.append(U(i3, un_sl))
    Uc, U3, U3s = map(np.array, (Uc, U3, U3s))
    nxt = json.load(open(f"{RUNS}/{run}/stages/{k+1}/executed_path.json"))["world_frame_path"]
    stop = np.array(nxt[-1], float)
    start_gap = float(np.hypot(*(np.array(nxt[0][:2]) - cur[:2])))
    istop = visset(calc, sg, stop, yaws, c2)
    ibest = visset(calc, sg, np.array(logged[0]), yaws, c2)
    us, ub = U(istop, un), U(ibest, un)
    row = {"run": run, "stage": k, "top10_match": bool(match), "n_cand": len(poses), "n_unmapped": int(un.sum()),
           "n_unmapped_sl": int(un_sl.sum()),
           "rho_total_U360": rho(total, U3), "rho_total_Ucone": rho(total, Uc), "rho_total_U360_sl": rho(total, U3s),
           "U360_mean": float(U3.mean()), "U360_stop": us, "pct_stop": pct(us, U3), "U360_best": ub, "pct_best": pct(ub, U3),
           "path_start_to_cur_m": start_gap, "stop_z": float(stop[2])}
    nn = obs_nodes(run, k + 1)
    if os.path.exists(f"{RUNS}/{run}/stages/{k+1}/habitat_scene_graph_original_graph0.yaml"):
        m2_sl = ~unmapped(refs, nn, "samelabel")
        inv = np.zeros(len(refs), bool)
        for i in istop: inv[idx[i]] = True
        a = inv & un; b = (~inv) & un
        row["yard"] = {"n_in": int(a.sum()), "in_mapped_sl": int((a & m2_sl).sum()), "n_out": int(b.sum()), "out_mapped_sl": int((b & m2_sl).sum())}
    return row

def job(a):
    try: return stage(*a)
    except Exception as e:
        import traceback; return {"run": a[0], "stage": a[1], "error": repr(e), "tb": traceback.format_exc()[-1200:]}

if __name__ == "__main__":
    S = [json.loads(l) for l in open("/tmp/cvp_review/audit/audit/stages.jsonl")]
    used = [r for r in S if r.get("top10_match") and "rho_total_U360" in r]
    rng = np.random.default_rng(20261029)
    picks = []
    for arm in ("official", "placebo", "filter_only", "oracle_visible"):
        for sc in ("00853", "00871"):
            cell = sorted([r for r in used if r["arm"] == arm and r["scene"] == sc], key=lambda r: (r["run"], r["stage"]))
            picks.append(cell[int(rng.integers(len(cell)))])
    rest = sorted(used, key=lambda r: (r["run"], r["stage"]))
    for i in rng.choice(len(rest), 4, replace=False):
        if rest[i] not in picks: picks.append(rest[i])
    # also one dropped (mismatch) stage to confirm mismatch reproduces
    dropped = sorted([r for r in S if not r.get("top10_match")], key=lambda r: (r["run"], r["stage"]))
    jobs = [(r["run"], r["stage"]) for r in picks] + [(dropped[0]["run"], dropped[0]["stage"])]
    print(jobs, flush=True)
    with Pool(7) as pool, open(f"{OUT}/verify_stages.jsonl", "w") as f:
        for res in pool.imap_unordered(job, jobs):
            f.write(json.dumps(res) + "\n"); f.flush(); print(json.dumps(res), flush=True)
