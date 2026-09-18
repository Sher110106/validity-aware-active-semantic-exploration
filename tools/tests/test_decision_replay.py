from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

# Keep this integration test pinned to the sibling tool even when a deployment
# has an unrelated/stale decision_replay.py in its working directory.
TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

import decision_replay


def write_synthetic_stage(root: Path):
    observed = {
        "nodes": [
            {
                "id": 1,
                "node_type": "room",
                "name": "living room",
                "position": "[0.0, 0.0, 0.0]",
            },
            {
                "id": 2,
                "node_type": "structure",
                "name": "wall",
                "position": "[5.0, 0.0, 1.0]",
                "dimension": "[0.2, 4.0, 2.0]",
                "orientation": "[[1,0,0],[0,1,0],[0,0,1]]",
            },
        ],
        "edges": [[2, 1]],
    }
    completion = {
        "nodes": observed["nodes"]
        + [
            {
                "id": 3,
                "node_type": "object",
                "name": "chair",
                "position": "[1.0, 1.0, 0.5]",
                "dimension": "[0.5, 0.5, 1.0]",
                "orientation": "[[1,0,0],[0,1,0],[0,0,1]]",
                "is_predicted": True,
            }
        ],
        "edges": observed["edges"] + [[3, 1]],
    }
    reference = {
        "nodes": [
            {
                "id": 30,
                "node_type": "object",
                "name": "chair",
                "position": "[1.0, 1.0, 0.5]",
                "dimension": "[0.5, 0.5, 1.0]",
                "orientation": "[[1,0,0],[0,1,0],[0,0,1]]",
            }
        ],
        "edges": [],
    }

    run_dir = root / "run"
    stage_dir = run_dir / "0"
    work_dir = root / "work"
    out_dir = root / "out"
    stage_dir.mkdir(parents=True)
    work_dir.mkdir()
    out_dir.mkdir()
    (stage_dir / "habitat_scene_graph_original_graph0.yaml").write_text(
        yaml.safe_dump(observed)
    )
    (stage_dir / "habitat_scene_graph_new_graph_0.yaml").write_text(
        yaml.safe_dump(completion)
    )
    (stage_dir / "path_log.json").write_text(
        json.dumps({"final_path": [[0.0, 0.0, 1.1]]})
    )
    reference_path = root / "reference.yaml"
    reference_path.write_text(yaml.safe_dump(reference))
    return run_dir, stage_dir, work_dir, out_dir, reference_path


class NullControlContractTests(unittest.TestCase):
    def test_import_resolves_the_tools_copy(self):
        expected = Path(__file__).resolve().parents[1] / "decision_replay.py"
        self.assertEqual(Path(decision_replay.__file__).resolve(), expected)

    def test_null_control_reuses_official_files_exactly(self):

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, stage_dir, work_dir, _, _ = write_synthetic_stage(root)

            policies, _ = decision_replay.build_policy_files(
                stage_dir,
                work_dir,
                calibrator=lambda _support: 1.0,
                support_tau=0.5,
            )

            self.assertIn("null_control", policies)
            self.assertEqual(policies["null_control"], policies["official"])
            self.assertEqual(
                [path.read_bytes() for path in policies["null_control"]],
                [path.read_bytes() for path in policies["official"]],
            )

    def test_null_control_uses_a_fresh_calculator_on_the_official_candidate_pool(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            run_dir, _, _, out_dir, reference_path = write_synthetic_stage(root)
            real_make_config = decision_replay.make_config
            real_calculator = decision_replay.PoolReplayCalculator
            calculator_instances = []

            def small_config(working_directory):
                config = real_make_config(working_directory)
                config.UNCERTAINTY_SAMPLES = 20
                return config

            def tracked_calculator(config):
                calculator = real_calculator(config)
                calculator_instances.append(calculator)
                return calculator

            with (
                patch.object(decision_replay, "RUN_DIR", run_dir),
                patch.object(decision_replay, "REFERENCE_PATH", str(reference_path)),
                patch.object(decision_replay, "OUT_DIR", out_dir),
                patch.object(decision_replay, "make_config", side_effect=small_config),
                patch.object(
                    decision_replay,
                    "PoolReplayCalculator",
                    side_effect=tracked_calculator,
                ),
            ):
                result = decision_replay.replay_stage(
                    0,
                    calibrator=lambda _support: 1.0,
                    support_tau=0.5,
                    beta_values=[0.0],
                )

            self.assertIn("null_control", result["policies"])
            self.assertEqual(len(calculator_instances), 4)
            official = result["policies"]["official"]
            null_control = result["policies"]["null_control"]
            self.assertIs(null_control["input_files_shared_with_official"], True)
            self.assertEqual(null_control["stage1_top_ig"], official["stage1_top_ig"])
            self.assertEqual(
                null_control["stage2_top_pose"], official["stage2_top_pose"]
            )
            self.assertEqual(
                null_control["reference_objects_visible"],
                official["reference_objects_visible"],
            )
            self.assertEqual(null_control["displacement_from_official_m"], 0.0)


if __name__ == "__main__":
    unittest.main()
