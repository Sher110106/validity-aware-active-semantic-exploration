import sys, os, json, glob
sys.path.insert(0, "/tmp/cvp_review/work_B")
import numpy as np
import replay as R
run = "/tmp/cvp_review/runs/e1_00853_s42_placebo_60m"
sd = run + "/stages/0"
files = [f"{sd}/habitat_scene_graph_new_graph_{i}.yaml" for i in range(8)]
print("visibility mismatches (graphs x poses):", R.validate(files, 42, n=30))
S = R.Scorer(files, 42)
print("bounds", S.bounds)
U = np.random.default_rng(42).random((3000, 4))
start = np.array(json.load(open(run + "/stages/1/executed_path.json"))["world_frame_path"][0])
out = S.decide(U, start, [start])
logged = [json.loads(l) for l in open(sd + "/pose_log.json")]
top_logged = np.array(logged[0]["best_sample_poses"])
top_mine = np.array([t[1] for t in out["top"]])
print("best first-stage score mine %.4f (log says 3.9750)" % out["best_first"])
print("final IG mine %.4f (log 4.2814 after reachability)" % out["final_ig"], "ties", out["ties"])
print("top10 match:", np.allclose(top_logged, top_mine, atol=1e-6) if top_logged.shape == top_mine.shape else (top_logged.shape, top_mine.shape))
for a, b in zip(top_logged, top_mine):
    print(np.round(a, 3), np.round(b, 3))
