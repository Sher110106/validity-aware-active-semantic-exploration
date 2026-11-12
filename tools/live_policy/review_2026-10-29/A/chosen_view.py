#!/usr/bin/env python3
"""What does the robot look at when it picks a target?

For each counted stage: take the logged winning pose(s) at the reachable
endpoint (pose_log 'new'), and with the pinned second-stage camera (near 0.1 m,
range 4 m, -10 deg pitch, 90 deg FOV, structure/door occlusion) list the
predicted (hypothesis) objects visible in any member's graph. For each visible
predicted object record whether it lies within 3 m (xy) of the path walked
before this stage ('scanned', as in stage_diagnostics.py). Compare with the
scanned share of ALL predicted objects at that stage.
Also: share of the chosen view's predicted objects proposed by only one member.
No F1/AUC.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, "/tmp/cvp_review/work_A")
import numpy as np  # noqa: E402

np.set_printoptions(legacy="1.25")
import fastig  # noqa: E402
import replay as rp  # noqa: E402


def main():
    runs = [l.strip() for l in open("/tmp/cvp_review/analysis_pre/runs.txt") if l.strip()]
    cam2 = fastig.second_cfg()
    normals = fastig.frustum_normals(cam2)
    out = []
    for run in runs:
        meta = rp.stage_meta(run)
        for k in sorted(meta):
            sd = f"{rp.RUNS}/{run}/stages/{k}"
            fin = rp.P[run]["stages"][str(k)]["pose_finals"][-1]
            if not fin["new"]:
                continue
            files = sorted(glob.glob(f"{sd}/habitat_scene_graph_new_graph_*.yaml"))
            if not files:
                continue
            walked = []
            for j in range(1, k + 1):
                p = f"{rp.RUNS}/{run}/stages/{j}/executed_path.json"
                if os.path.exists(p):
                    walked += [q[:2] for q in json.load(open(p))["world_frame_path"]]
            walked = np.array(walked) if walked else np.zeros((0, 2))
            # use the chosen target: the final pose nearest the published target
            tgt = json.loads(open(f"{sd}/path_log.json").read().strip().splitlines()[-1])["final_path"][-1]
            finals = np.array(fin["final"])
            j = int(np.argmin(np.hypot(finals[:, 0] - tgt[0], finals[:, 1] - tgt[1])))
            pose = np.array(fin["new"][j])[None, :]
            R, t, cpos = fastig.cam_frames(pose)
            vis_pred = {}
            all_pred = {}
            for f in files:
                g = int(re.search(r"_(\d+)\.yaml$", f).group(1))
                obs_ids = {n["id"] for n in rp.load(f"{sd}/habitat_scene_graph_original_graph{g // 4}.yaml")["nodes"]}
                calc = rp.ph.make_calc(0, 0, "/tmp/cvp_review/work_A/tmp")
                opt = calc._preprocess_groups([[rp.load(f)]])[0][0]
                geom = fastig.GraphGeom(opt)
                vis, _ = fastig.visible(geom, R, t, cpos, cam2, normals)
                for i, (nid, nm) in enumerate(zip(geom.ids, geom.names)):
                    if nid in obs_ids:
                        continue
                    key = (nm, tuple(np.round(geom.tpos[i], 2)))
                    all_pred.setdefault(key, set()).add(g)
                    if geom.T and vis[0, i]:
                        vis_pred.setdefault(key, set()).add(g)

            def scanned(key):
                if not len(walked):
                    return False
                x, y = key[1][0], key[1][1]
                return float(np.min(np.hypot(walked[:, 0] - x, walked[:, 1] - y))) <= 3.0

            row = {"run": run, "arm": rp.arm_of(run), "stage": k, "n_vis_pred": len(vis_pred), "n_all_pred": len(all_pred),
                   "vis_scanned_share": float(np.mean([scanned(kk) for kk in vis_pred])) if vis_pred else None,
                   "all_scanned_share": float(np.mean([scanned(kk) for kk in all_pred])) if all_pred else None,
                   "vis_single_member_share": float(np.mean([len(v) == 1 for v in vis_pred.values()])) if vis_pred else None,
                   "all_single_member_share": float(np.mean([len(v) == 1 for v in all_pred.values()])) if all_pred else None,
                   "best_ig": fin["best_ig"]}
            out.append(row)
            print(json.dumps(row), flush=True)
    json.dump(out, open("/tmp/cvp_review/work_A/chosen_view.json", "w"), indent=0)


if __name__ == "__main__":
    main()
