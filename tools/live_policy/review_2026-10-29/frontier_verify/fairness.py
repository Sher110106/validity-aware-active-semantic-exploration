import glob, json, os, importlib.util
import numpy as np, yaml
spec = importlib.util.spec_from_file_location("sc", "/tmp/cvp_verify_step7/score.py")
sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)
R0 = "/Users/sher/cvp_live_campaign_copy/runs"
S = json.load(open("/tmp/cvp_verify_step7/scores.json"))["runs"]
counted = ["e4_00853_s42_frontier_60m","e4_00853_s43_frontier_60m","e4_00853_s44_frontier_60m","e4_00871_s42_frontier_60m","e4_00871_s43_frontier_60m","e4_00871_s44_frontier_60m",
 "e1_00853_s42_official_60m","e1_00853_s43_official_60m","e1_00871_s42_official_60m","e1_00871_s43_official_60m","e1_00871_s44_official_60m",
 "e1_00853_s42_placebo_60m","e1_00853_s43_placebo_60m","e1_00853_s44_placebo_60m","e1_00871_s42_placebo_60m","e1_00871_s43_placebo_60m_rerun1","e1_00871_s44_placebo_60m"]
refs = {s: sc.load_objects(f"{R0}/live_campaign/hm3d_refs_work/{s}_hm3d_reference.yaml") for s in ("00853","00871")}
print("== stage completeness, predicted flags, spacing")
for n in counted:
    d = f"{R0}/{'frontier_seeds' if n.startswith('e4') else 'live_campaign'}/{n}/stages"
    issues, npred = [], 0
    for sd in sorted(glob.glob(d + "/*"), key=lambda p: int(os.path.basename(p))):
        k = os.path.basename(sd); ns = os.path.isfile(sd + "/navigation_stats.json")
        g = [i for i in (0, 1) if os.path.isfile(f"{sd}/habitat_scene_graph_original_graph{i}.yaml")]
        if not ns or len(g) < 2:
            issues.append(f"{k}:stats={'y' if ns else 'n'},tracks={g}")
        for i in g:
            y = yaml.safe_load(open(f"{sd}/habitat_scene_graph_original_graph{i}.yaml"))
            npred += sum(1 for x in y["nodes"] if x.get("is_predicted") is True)
    xs = [p["x"] for p in S[n]["points"] if p["x"] <= 60]
    gaps = np.diff(xs)
    print(f"{n:38s} stages_scored={S[n]['n_scored_stages']:2d} median_gap<=60m={np.median(gaps):.2f} max_gap={gaps.max():.2f} last<=60={xs[-1]:.2f} pred_nodes={npred} issues={issues}")
print("== object displacement to nearest same-label ref object (final scored stage <=60 m, both tracks), within 1.0 m")
for n in counted:
    r = S[n]; pts = [p for p in r["points"] if p["x"] <= 60.0001] or r["points"]
    k = max(pts, key=lambda p: p["x"])["stage"]
    d = f"{R0}/{'frontier_seeds' if n.startswith('e4') else 'live_campaign'}/{n}/stages/{k}"
    disp, npred = [], 0
    for i in (0, 1):
        f = f"{d}/habitat_scene_graph_original_graph{i}.yaml"
        if not os.path.isfile(f): continue
        P = sc.load_objects(f); npred += len(P)
        for nm, pos in P:
            c = [g for gn, g in refs[r["scene"]] if gn == nm]
            if not c: continue
            dd = [g - pos for g in c]; j = int(np.argmin([np.linalg.norm(x) for x in dd]))
            if np.linalg.norm(dd[j]) < 1.0: disp.append(dd[j])
    disp = np.array(disp)
    pr = [sc.f1(refs[r["scene"]], sc.load_objects(f"{d}/habitat_scene_graph_original_graph{i}.yaml")) for i in (0,1) if os.path.isfile(f"{d}/habitat_scene_graph_original_graph{i}.yaml")]
    print(f"{n:38s} stage={k:2d} n_pred_obj(2 tracks)={npred:3d} near={len(disp):3d} median_offset(ref-pred)={np.round(np.median(disp,0),3)} median_dist={np.median(np.linalg.norm(disp,axis=1)):.3f} P/R/F1 per track={[tuple(round(v,3) for v in t) for t in pr]}")
print("== sampling-density effect: frontier AUC60 using every k-th scored stage (keeping first and last)")
for n in counted[:6]:
    xy = [(p["x"], p["f1"]) for p in S[n]["points"]]
    row = [f"k=1 {sc.auc(xy,60):.4f}"]
    for k in (2, 3):
        sub = xy[::k]
        if sub[-1] != xy[-1]: sub.append(xy[-1])
        row.append(f"k={k} {sc.auc(sub,60):.4f}")
    print(f"{n:38s}", " ".join(row))
