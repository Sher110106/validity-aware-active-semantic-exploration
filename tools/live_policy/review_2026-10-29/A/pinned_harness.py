#!/usr/bin/env python3
"""Load the pinned calculate_uncertainty.py read-only (no sys.path change) and
replay select_next_target's first stage for one saved stage.

NumPy 2 note: the pinned code writes perturbed positions as str(list(np_array));
with NumPy >= 2 that renders np.float64(...) and ast.literal_eval fails. We set
numpy's legacy print mode 1.25 so the strings match the NumPy 1.x runtime the
host used. No pinned line is changed.
"""
import importlib.util
import json
import os
import sys
from dataclasses import dataclass

import numpy as np

np.set_printoptions(legacy="1.25")

PINNED = "/tmp/cvp_review/pipeline_pinned_copy/scripts/calculate_uncertainty.py"
_spec = importlib.util.spec_from_file_location("pinned_calculate_uncertainty", PINNED)
cu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cu)


@dataclass
class Cfg:
    SEED: int
    WORKING_DIRECTORY: str
    UNCERTAINTY_SAMPLES: int = 300
    UNCERTAINTY_PERTURBATIONS: int = 3
    UNCERTAINTY_NOISE_LOW: float = -0.25
    UNCERTAINTY_NOISE_HIGH: float = 0.25
    MINIMUM_DISTANCE_DIFFERENCE: float = 1.0
    UNCERTAINTY_ROOM_WEIGHT: float = 1.0
    MOVE_COST_LAMBDA: float = 0.2
    AGENT_HEIGHT: float = 1.1
    CAMERA_CONFIG: object = None


def make_calc(seed, n_prior_calls, workdir):
    cfg = Cfg(SEED=seed, WORKING_DIRECTORY=workdir, CAMERA_CONFIG=cu.CameraConfig())
    calc = cu.UncertaintyCalculator(cfg)
    for _ in range(n_prior_calls):
        calc.rng.uniform(low=np.zeros(4), high=np.ones(4), size=(cfg.UNCERTAINTY_SAMPLES * 10, 4))
    return calc


def first_stage(calc, files, current_pos):
    groups = calc._build_scene_graph_groups(files)
    calc.mapping = calc._get_object_to_parent_mapping(files)
    lo, hi = calc._get_sampling_bounds(groups)
    obs = calc._gather_sample_observations(groups, calc.mapping, lo, hi)
    scored = []
    for g in obs:
        o = calc._calculate_ig_components(g, lambda x: x["names_list"])
        r = calc._calculate_ig_components(g, lambda x: x["rooms_list"])
        ig = (o["H_y"] - o["H_y_epsilon"]) + calc.config.UNCERTAINTY_ROOM_WEIGHT * (r["H_y"] - r["H_y_epsilon"])
        pose = g[0]["sample"]
        d = np.linalg.norm(pose[:3] - current_pos[:3])
        scored.append((ig - calc.config.MOVE_COST_LAMBDA * d, ig, pose))
    order = sorted(range(len(scored)), key=lambda i: scored[i][0], reverse=True)
    return lo, hi, scored, order


if __name__ == "__main__":
    import time
    run, k, nprior = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    first = sys.argv[4] if len(sys.argv) > 4 else None
    sd = f"/tmp/cvp_review/runs/{run}/stages/{k}"
    files = [os.path.join(sd, f"habitat_scene_graph_new_graph_{g}.yaml") for g in range(8)
             if os.path.exists(os.path.join(sd, f"habitat_scene_graph_new_graph_{g}.yaml"))]
    if first is not None:
        order = [int(x) for x in first.split(",")]
        files = [os.path.join(sd, f"habitat_scene_graph_new_graph_{g}.yaml") for g in order]
    seed = int([l.split(":")[1] for l in open(f"/tmp/cvp_review/runs/{run}/config/pipeline_config.yaml") if l.startswith("SEED:")][0])
    if k == 0:
        cur = np.array(json.load(open(f"/tmp/cvp_review/runs/{run}/stages/1/executed_path.json"))["world_frame_path"][0])
    else:
        cur = np.array(json.load(open(f"{sd}/executed_path.json"))["world_frame_path"][-1])
    calc = make_calc(seed, nprior, "/tmp/cvp_review/work_A/tmp")
    t = time.time()
    lo, hi, scored, order = first_stage(calc, files, cur)
    print("bounds", lo, hi, "n", len(scored), "time", round(time.time() - t, 1))
    print("best", round(scored[order[0]][0], 4))
    for i in order[:10]:
        print([round(x, 2) for x in scored[i][2]], round(scored[i][0], 4))
