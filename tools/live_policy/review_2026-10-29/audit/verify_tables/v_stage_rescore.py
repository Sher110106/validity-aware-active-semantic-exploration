"""Re-score 8 random stages (2 per arm, both scenes) from the saved replay condition files and
check replay2_results.jsonl fields used by Table 1 (top1_dist for obs/plc_a/plc_b/orc and the
plc_a-vs-plc_b floor, top1_same, top10_overlap). Read-only on work_A; pinned calculator workdir
redirected to this audit dir; no bytecode writes. No F1/AUC."""
import sys, json, os
sys.dont_write_bytecode = True
sys.path.insert(0, "/tmp/cvp_review/work_A")
import numpy as np
np.set_printoptions(legacy="1.25")
import pinned_harness as ph
_orig = ph.make_calc
AUD = "/tmp/cvp_review/audit/verify_tables/scratch"; os.makedirs(AUD, exist_ok=True)
ph.make_calc = lambda seed, n, wd: _orig(seed, n, AUD)
import fastig, replay as rp, replay2 as r2
fastig.ph.make_calc = ph.make_calc
rows = [json.loads(l) for l in open("/tmp/cvp_review/work_A/replay2_results.jsonl")]
rows = [r for r in rows if "error" not in r and r.get("n_cand", 0) > 0 and r["run"] != "e1_00871_s43_placebo_60m"]
rng = np.random.default_rng(1029)
pick = []
for arm in ["official", "placebo", "filter_only", "oracle_visible"]:
    for sc in ["00853", "00871"]:
        R = [r for r in rows if r["arm"] == arm and f"_{sc}_" in r["run"]]
        pick.append(R[rng.integers(len(R))])
out = []
for r in pick:
    run, k = r["run"], r["stage"]
    meta = rp.stage_meta(run)[k]; seed = rp.P[run]["cfg"]["SEED"]
    gids = r2.gids_for(run, k, meta)
    sd = f"{rp.RUNS}/{run}/stages/{k}"; wd = f"/tmp/cvp_review/work_A/tmp/r2_{run}_{k}"
    files = {"actual": [f"{sd}/habitat_scene_graph_new_graph_{g}.yaml" for g in gids]}
    for c in ["obs", "plc_a", "plc_b", "orc"]:
        files[c] = [f"{wd}/{c}_{g}.yaml" for g in gids]
    cur = rp.current_pos(run, k)
    kept, sc_act, _, _ = fastig.Scorer(files["actual"], seed).first_stage(seed, meta["nprior"], cur)
    d = np.linalg.norm(kept[:, :3] - cur[:3], axis=1)
    cam = fastig.cu.CameraConfig()
    tot = {"actual": sc_act[:, 0] + sc_act[:, 1] - 0.2 * d}
    for c in ["obs", "plc_a", "plc_b", "orc"]:
        s, _ = fastig.Scorer(files[c], seed).score(kept, cam)
        tot[c] = s[:, 0] + s[:, 1] - 0.2 * d
    top = {c: list(np.argsort(-tot[c], kind="stable")[:10]) for c in tot}
    a1 = kept[top["actual"][0], :2]
    mine = {c: float(np.hypot(*(kept[top[c][0], :2] - a1))) for c in ["obs", "plc_a", "plc_b", "orc"]}
    mine["floor"] = float(np.hypot(*(kept[top["plc_a"][0], :2] - kept[top["plc_b"][0], :2])))
    mine["ovl_plc_a"] = len(set(top["plc_a"]) & set(top["actual"])) / 10
    theirs = {c: r["fixed"][c]["top1_dist"] for c in ["obs", "plc_a", "plc_b", "orc"]}
    theirs["floor"] = r["fixed_plc_a_vs_b"]["top1_dist"]; theirs["ovl_plc_a"] = r["fixed"]["plc_a"]["top10_overlap"]
    ok = all(abs(mine[x] - theirs[x]) < 1e-6 for x in mine)
    out.append({"run": run, "stage": k, "arm": r["arm"], "n_cand": len(kept), "n_cand_theirs": r["n_cand"], "mine": mine, "theirs": theirs, "match": ok})
    print(run, k, ok, {x: (round(mine[x], 3), round(theirs[x], 3)) for x in mine}, flush=True)
json.dump(out, open("/tmp/cvp_review/audit/verify_tables/v_stage_rescore.json", "w"), indent=1)
