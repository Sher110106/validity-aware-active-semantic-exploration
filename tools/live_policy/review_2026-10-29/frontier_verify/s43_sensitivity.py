import json, os, importlib.util
import numpy as np
spec = importlib.util.spec_from_file_location("sc", "/tmp/cvp_verify_step7/score.py")
sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)
R0 = "/Users/sher/cvp_live_campaign_copy/runs/live_campaign/e1_00853_s43_official_60m/stages"
S = json.load(open("/tmp/cvp_verify_step7/scores.json"))["runs"]
ref = sc.load_objects("/Users/sher/cvp_live_campaign_copy/runs/live_campaign/hm3d_refs_work/00853_hm3d_reference.yaml")
def plen(f):
    h = np.array(json.load(open(f))["habitat_frame_path"]); d = h[1:, [0, 2]] - h[:-1, [0, 2]]
    return float(np.linalg.norm(d, axis=1).sum())
# validate the estimator on stages that do have stats: x_k ?= x_{k-1} + len(executed_path in stage k)
pts = {p["stage"]: p["x"] for p in S["e1_00853_s43_official_60m"]["points"]}
errs = [abs(pts[k-1] + plen(f"{R0}/{k}/executed_path.json") - pts[k]) for k in range(1, 20) if os.path.isfile(f"{R0}/{k}/executed_path.json")]
print("estimator check, max |err| m over stages 1-19:", max(errs))
x20 = pts[19] + plen(f"{R0}/20/executed_path.json")
f20 = np.mean([sc.f1(ref, sc.load_objects(f"{R0}/20/habitat_scene_graph_original_graph{i}.yaml"))[2] for i in (0, 1)])
xy = [(p["x"], p["f1"]) for p in S["e1_00853_s43_official_60m"]["points"]]
print(f"stage 19 x={pts[19]:.2f} f1={xy[-1][1]:.4f}; stage 20 est x={x20:.2f} f1={f20:.4f}")
print("auc60 registered (hold-last):", round(sc.auc(xy, 60), 6), " with stage 20 added:", round(sc.auc(xy + [(x20, f20)], 60), 6))
