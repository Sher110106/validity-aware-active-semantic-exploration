import sys
sys.path.insert(0, "/workspace/catkin_ws/src/active_semantic_perception/exploration/scripts")

import numpy as np
from dataclasses import dataclass
from calculate_uncertainty import UncertaintyCalculator, CameraConfig


@dataclass
class Config:
    SEED: int
    CAMERA_CONFIG: CameraConfig
    UNCERTAINTY_PERTURBATIONS: int
    UNCERTAINTY_NOISE_LOW: float
    UNCERTAINTY_NOISE_HIGH: float
    UNCERTAINTY_SAMPLES: int
    UNCERTAINTY_ROOM_WEIGHT: float
    MOVE_COST_LAMBDA: float
    AGENT_HEIGHT: float
    MINIMUM_DISTANCE_DIFFERENCE: float
    WORKING_DIRECTORY: str


camera_config = CameraConfig(fx=320.0, fy=320.0, cx=320.0, cy=240.0, width=640, height=480, near_clip=0.5, max_range=3.0)

config = Config(
    SEED=42,
    CAMERA_CONFIG=camera_config,
    UNCERTAINTY_PERTURBATIONS=3,
    UNCERTAINTY_NOISE_LOW=-0.25,
    UNCERTAINTY_NOISE_HIGH=0.25,
    UNCERTAINTY_SAMPLES=300,
    UNCERTAINTY_ROOM_WEIGHT=1.0,
    MOVE_COST_LAMBDA=0.2,
    AGENT_HEIGHT=1.1,
    MINIMUM_DISTANCE_DIFFERENCE=1.0,
    WORKING_DIRECTORY="/tmp/gate_check_out",
)

import os
import json
os.makedirs(config.WORKING_DIRECTORY, exist_ok=True)

stage_dir = "/workspace/runs/scene00069_seed42_25m_20260914_v3/stages/0"
scene_graph_files = [f"{stage_dir}/habitat_scene_graph_new_graph_{i}.yaml" for i in range(8)]

calc = UncertaintyCalculator(config)
history_pos = [np.array([3.5457770742297225, -7.000415207642157, 1.1000000238418552])]

best_list = calc.select_next_target(scene_graph_files, history_pos)
print("num best candidates:", len(best_list))
print("first candidate:", best_list[0])

# Second stage: rescore the top-10 candidates with calculate_specific_pose_ig
# (hardcoded near_clip=0.1/max_range=4.0, no move cost, uses self.optimized_groups
# already cached from the call above)
print("\n--- stage 2 rescoring ---")
for pose in best_list:
    ig2 = calc.calculate_specific_pose_ig(pose, path_distance=0.0)
    print(f"  pose={pose} ig2={ig2}")

# Compare against the real logged values from exploration_pipeline.log
print("\n--- expected from real log ---")
print("Expected bounds: low [-5.78865449 -13.70862757 1.1 0.] high [6.012 -3.49774255 1.1 360.]")
print("Expected stage-1 top IG: 3.5899")
print("Expected stage-2 selected IG: 4.377421707715273 (2nd best of the 10)")
