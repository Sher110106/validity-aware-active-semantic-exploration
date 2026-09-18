#!/usr/bin/env python3
"""Decision-level replay: for each checkpoint in a frozen run, compare
which viewpoint the pinned UncertaintyCalculator would select under each
policy (official / identical-graph null control / filter-only /
calibrated-support / combined calibrated-risk), using the SAME candidate
pool across all policies (drawn
once under the official policy) so a decision divergence reflects a real
policy effect, not where candidates happened to be sampled from.

Design decisions, all advisor-reviewed (REVIEW_2026-09-14.md's Step 5,
consulted 2026-09-15):
- Reuses the pinned UncertaintyCalculator class's real geometry/entropy
  code UNCHANGED (ray-box occlusion, frustum culling, multi-group mutual-
  information entropy) rather than reimplementing it - verified this
  reproduces the live pipeline's actual logged decision exactly (see
  gate_check.py: stage 0's bounds, top-stage-1 IG, and the exact
  reachability-gated selected IG all match the real run's log character
  for character).
- Filters/calibrates by computing a KEEP SET of node ids with the
  existing asp_offline tools, then applying that set to the RAW YAML
  dict (never round-tripping through normalize_author_graph, which drops
  `orientation` - silently making every occlusion test wrong).
- Policy 3 (calibrated-support) is beta=0: calibration can only reach the
  decision through the support-threshold filter. Policy 4 (combined
  calibrated-risk) is tau=0 (the RAW/unfiltered graph) with beta>0's risk
  re-ranking - applying both the filter AND the risk term to the same
  nodes would double-count one mechanism.
- The two-stage pinned scoring (select_next_target's top-10, then
  calculate_specific_pose_ig's reachability-gated rescoring) is both
  replayed - the first stage alone is not the decision.
- Cross-policy IG values are NOT compared (filtering mechanically lowers
  obj_ig by removing the cross-hypothesis disagreement it measures, so a
  filtered policy will always look "worse" on IG regardless of quality).
  Instead: did the SELECTED viewpoint change, and how far is it from the
  official policy's own selection; and separately, is the selected
  viewpoint close to real reference-graph content (a policy-independent
  yardstick).
- Tie multiplicity at the top score is reported - ties are common (stage
  1 of the real run ties 3-way at the exact selected pose) and a "policy
  picked a different viewpoint" claim is only meaningful when top scores
  actually differ, not just when the argmax tie-break landed elsewhere.

Known, disclosed gap (not fixed - out of scope per the review's own
allowance): the live pipeline gates its top-10 candidates through a REAL
reachability check (path-planning feasibility against the actual navmesh)
before final selection - this run's "official" stage2_top_pose is the
raw top-scored candidate BEFORE that gate, so it does NOT match the real
log's actual historical selection (verified separately in gate_check.py,
which DOES reproduce the real reachability-filtered selection exactly by
inferring the mask from the live log's own recorded IG value - a trick
that only works for the one policy with a real log to compare against).
Since there is no live log for the three counterfactual policies, their
reachability cannot be reconstructed at all - so this script applies "no
reachability gate" UNIFORMLY across all four policies rather than
special-casing official, keeping the cross-policy comparison fair even
though no single policy's result matches a live trajectory. Label every
result from this script "decision-replay approximation," never "live
trajectory," per REVIEW_2026-09-14.md's own explicit allowance for this.
"""
from __future__ import annotations

import ast
import copy
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import yaml

sys.path.insert(0, "/workspace/catkin_ws/src/active_semantic_perception/exploration/scripts")
sys.path.insert(0, "/workspace/tools")

from calculate_uncertainty import UncertaintyCalculator, CameraConfig
from asp_offline.author_io import load_author_graph
from asp_offline.geometry import distance as offline_distance
from asp_offline.support_policy import fit_loso_calibrator, support_scores
from asp_offline.validator import ValidationConfig, validate_completion

LLM_ENSEMBLE_COUNT = 4

# 2026-09-17: generalized from hardcoded scene-00069-only constants to a
# configure() call so this script can replay any of the 4 scenes without
# copy-pasting the file. The original single-scene defaults are kept as
# the module's starting values (so any code that imports this module
# without calling configure() first sees the exact same behavior as
# before), but configure() is now the one place that changes them -
# never edit RUN_DIR/REFERENCE_PATH/OUT_DIR/SCENE_ID directly elsewhere.
#
# Hazard this closes (flagged before any new-scene run, not after):
# SCENE_CALIBRATION_CONFIGS below is the calibration TRAINING corpus for
# all 4 scenes and must never change when replaying a different run -
# only RUN_DIR/REFERENCE_PATH (which run's DECISIONS we replay) and
# SCENE_ID (which entry to hold OUT of that training corpus) change.
# Pointing RUN_DIR at scene 00573's matrix run while leaving SCENE_ID as
# "00069" would fit a calibrator that still excludes "00069" but folds
# 00573's data into training under the wrong label, AND hold out nothing
# real - a silent leak, not a crash. configure() asserts scene_id is one
# of SCENE_CALIBRATION_CONFIGS' own keys specifically to make that
# mistake require overriding an explicit check, not just editing a path.
RUN_DIR = Path("/workspace/runs/scene00069_seed42_25m_20260914_v3/stages")
REFERENCE_PATH = "/workspace/runs/scene00069_frontier_reference/stages/25/habitat_scene_graph_original_graph0.yaml"
OUT_DIR = Path("/workspace/runs/decision_replay_scene00069_v3")
SCENE_ID = "00069"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def configure(*, scene_id: str, run_dir: Path, reference_path: str, out_dir: Path) -> None:
    """Point this module at a different scene/run/reference/output than
    the scene-00069 defaults above. Must be called (if at all) before
    fit_held_out_calibrator()/replay_stage()/main()'s replay loop -
    every function below reads the module-level RUN_DIR/REFERENCE_PATH/
    OUT_DIR/SCENE_ID globals this sets, exactly as they did before this
    function existed. `scene_id` is checked against
    SCENE_CALIBRATION_CONFIGS' own keys (defined further down in this
    module, already loaded by the time this runs) specifically so a
    typo'd or mismatched scene id fails loudly instead of silently
    training a calibrator on the wrong held-out label - see the hazard
    note above."""
    global RUN_DIR, REFERENCE_PATH, OUT_DIR, SCENE_ID
    if scene_id not in SCENE_CALIBRATION_CONFIGS:
        raise ValueError(
            f"{scene_id!r} is not one of SCENE_CALIBRATION_CONFIGS' scenes: "
            f"{sorted(SCENE_CALIBRATION_CONFIGS)}"
        )
    SCENE_ID = scene_id
    RUN_DIR = run_dir
    REFERENCE_PATH = reference_path
    OUT_DIR = out_dir
    OUT_DIR.mkdir(parents=True, exist_ok=True)

CAMERA_CONFIG = CameraConfig(fx=320.0, fy=320.0, cx=320.0, cy=240.0, width=640, height=480, near_clip=0.5, max_range=3.0)
# calculate_specific_pose_ig's own hardcoded override (near_clip=0.1,
# max_range=4.0) - every stage2_top_pose being scored came from that
# second-stage rescoring, not the stage-1 CAMERA_CONFIG above, so
# reference-visibility must use the SAME override or silently reintroduce
# a fidelity gap (audit finding H3).
STAGE2_CAMERA_CONFIG = CameraConfig(fx=320.0, fy=320.0, cx=320.0, cy=240.0, width=640, height=480, near_clip=0.1, max_range=4.0)


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


def make_config(working_dir: str) -> Config:
    return Config(
        SEED=42, CAMERA_CONFIG=CAMERA_CONFIG, UNCERTAINTY_PERTURBATIONS=3,
        UNCERTAINTY_NOISE_LOW=-0.25, UNCERTAINTY_NOISE_HIGH=0.25, UNCERTAINTY_SAMPLES=300,
        UNCERTAINTY_ROOM_WEIGHT=1.0, MOVE_COST_LAMBDA=0.2, AGENT_HEIGHT=1.1,
        MINIMUM_DISTANCE_DIFFERENCE=1.0, WORKING_DIRECTORY=working_dir,
    )


class PoolReplayCalculator(UncertaintyCalculator):
    """Same as the pinned UncertaintyCalculator, except _gather_sample_observations
    can be pointed at a FIXED list of candidate poses instead of drawing fresh
    ones via RNG - so multiple policies can be scored against the identical
    candidate pool. The visibility/entropy inner loop is copied verbatim from
    the pinned method; only candidate SOURCING differs."""

    def gather_observations_for_fixed_poses(self, groups, mapping, poses: np.ndarray):
        self.optimized_groups = self._preprocess_groups(groups)
        self.mapping = mapping  # calculate_specific_pose_ig reads self.mapping, not a local
        sample_observations = []
        for sample in poses:
            pos = sample[:3]
            yaw_deg = float(sample[3])
            group_obs_for_sample = []
            camera_cls = type(self)._camera_cls()
            camera = camera_cls(config=self.camera_config, position=pos, yaw_degrees=yaw_deg)
            for i, opt_group in enumerate(self.optimized_groups):
                names_list = []
                rooms_list = []
                for opt_sg in opt_group:
                    ids, _, _, name_counts = self._visible_testing(opt_sg, camera)
                    final_room_observation = set()
                    if ids:
                        parent_names = [mapping[i][obj_id] for obj_id in ids if obj_id in mapping[i]]
                        if parent_names:
                            from collections import Counter
                            majority_vote_room = Counter(parent_names).most_common(1)[0][0]
                            final_room_observation = {majority_vote_room}
                    names_list.append(name_counts)
                    rooms_list.append(final_room_observation)
                group_obs_for_sample.append({'sample': sample, 'names_list': names_list, 'rooms_list': rooms_list})
            sample_observations.append(group_obs_for_sample)
        return sample_observations

    @staticmethod
    def _camera_cls():
        import calculate_uncertainty as cu
        return cu.Camera

    def visible_predicted_ids_at(self, optimized_groups, pose: np.ndarray) -> List[List[Any]]:
        """Per-group visible predicted node ids at one pose, unperturbed
        (group index 0 = the original, un-perturbed member) - used for the
        risk term, which should not count perturbation copies 4x over.
        Takes ALREADY-preprocessed groups (self.optimized_groups from a
        prior call) - reprocessing per-candidate is redundant, the groups
        don't change across candidates."""
        pos = pose[:3]
        yaw_deg = float(pose[3])
        import calculate_uncertainty as cu
        camera = cu.Camera(config=self.camera_config, position=pos, yaw_degrees=yaw_deg)
        result = []
        for opt_group in optimized_groups:
            ids, _, _, _ = self._visible_testing(opt_group[0], camera)
            result.append(ids)
        return result


def smart_eval(expr):
    return ast.literal_eval(expr) if isinstance(expr, str) else expr


def write_keep_set_yaml(raw_graph: Dict[str, Any], keep_ids: Optional[set], out_path: Path) -> None:
    """Write a copy of `raw_graph` (already-loaded raw YAML dict, ints for
    node ids, string-encoded position/dimension/orientation - the exact
    format _load_scene_graph/_smart_eval expect) keeping only nodes whose
    id is in `keep_ids` (None = keep everything, i.e. the official/raw
    policy). Never round-trips through the offline Node/Graph schema, so
    every pinned-only field (orientation, is_predicted, ...) survives
    untouched for every surviving node."""
    if keep_ids is None:
        kept_nodes = raw_graph["nodes"]
    else:
        kept_nodes = [n for n in raw_graph["nodes"] if n["id"] in keep_ids]
    kept_ids_set = {n["id"] for n in kept_nodes}
    kept_edges = [e for e in raw_graph["edges"] if e[0] in kept_ids_set and e[1] in kept_ids_set]
    with open(out_path, "w") as f:
        yaml.safe_dump({"nodes": kept_nodes, "edges": kept_edges}, f)


def build_policy_files(stage_dir: Path, work_dir: Path, calibrator, support_tau: float) -> Tuple[Dict[str, List[Path]], Dict[Tuple[int, str], float]]:
    """For the up-to-8 raw completions in this stage, write each policy's
    filtered YAML files (official/null_control/filter_only/calibrated_support),
    returning ({policy_name: [file paths]}, {(group_index, node_id_str): raw_support}).
    'combined' reuses 'official' (raw, unfiltered) as its INPUT graph - the
    risk term re-ranks the candidate pool afterward, it does not change
    which nodes are visible.

    2026-09-15 correction (audit finding H6): node ids are only unique
    WITHIN one raw completion file - the same numeric id is reassigned by
    a different (scene track, completion) pair, since each LLM completion
    re-derives its own graph from scratch. A single flat {node_id: support}
    dict therefore collided on ~30% of real lookups (same failure mode as
    the parent_room issue already documented in support_policy.py). The
    support map is now keyed by (group_index, node_id_str), where
    group_index is a running counter over EXACTLY the same (scene_index,
    idx) iteration order used to append to policies['official'] below - so
    group_index here lines up 1:1 with official_calc.optimized_groups'
    position in replay_stage, and group_index in visible_predicted_ids_at's
    per-group output is the same index space."""
    raw_paths = sorted(stage_dir.glob("habitat_scene_graph_new_graph_*.yaml"), key=lambda p: int(p.stem.rsplit("_", 1)[1]))
    policies: Dict[str, List[Path]] = {
        "official": [],
        "null_control": [],
        "filter_only": [],
        "calibrated_support": [],
        "combined": [],
    }
    node_support: Dict[Tuple[int, str], float] = {}
    config = ValidationConfig(allow_parsed_mapping=True)
    group_index = 0

    for scene_index in (0, 1):
        lo, hi = scene_index * LLM_ENSEMBLE_COUNT, scene_index * LLM_ENSEMBLE_COUNT + LLM_ENSEMBLE_COUNT
        track_paths = [p for p in raw_paths if lo <= int(p.stem.rsplit("_", 1)[1]) < hi]
        if not track_paths:
            continue
        observed_path = stage_dir / f"habitat_scene_graph_original_graph{scene_index}.yaml"
        observed = load_author_graph(observed_path, observed=True)
        ensemble = [load_author_graph(p) for p in track_paths]

        for idx, (raw_path, completion) in enumerate(zip(track_paths, ensemble)):
            raw_graph = yaml.safe_load(raw_path.read_text())
            stem = raw_path.stem

            official_out = work_dir / f"{stem}_official.yaml"
            write_keep_set_yaml(raw_graph, None, official_out)
            policies["official"].append(official_out)
            # The null control must be graph-identical by construction, not
            # merely reconstructed in a way expected to be equivalent. It
            # reuses official's exact files and differs only by traversing a
            # fresh PoolReplayCalculator in replay_stage.
            policies["null_control"].append(official_out)
            policies["combined"].append(official_out)  # combined scores the raw graph; risk re-ranks candidates, not nodes

            result = validate_completion(completion, observed, config)
            # 2026-09-17 fix (DEVIATIONS #74): both keep-sets below used to
            # keep predicted nodes ONLY, silently dropping every observed
            # node (walls, doors, the actual map) that `official` keeps in
            # full - confounding every alternative-vs-official comparison
            # with "has the map" vs "doesn't have the map" instead of
            # testing the filtering policy. Fixed by unioning observed ids
            # in, exactly matching support_filtered_graph's existing,
            # already-correct pattern (asp_offline/support_policy.py:
            # `kept_node_ids = {n.id for n in observed_nodes} | kept_ids`).
            observed_keep_ids = {str(n["id"]) for n in result.graph["nodes"] if n.get("observed", False)}

            filter_keep_ids = observed_keep_ids | {str(n["id"]) for n in result.graph["nodes"] if not n.get("observed", False)}
            filter_keep_ids_int = {n["id"] for n in raw_graph["nodes"] if str(n["id"]) in filter_keep_ids}
            filter_out = work_dir / f"{stem}_filter.yaml"
            write_keep_set_yaml(raw_graph, filter_keep_ids_int, filter_out)
            policies["filter_only"].append(filter_out)

            scored = support_scores(completion, ensemble, expected_size=LLM_ENSEMBLE_COUNT)
            for h in scored:
                if h.node_id is not None:
                    node_support[(group_index, h.node_id)] = h.support
            group_index += 1
            # 2026-09-17 second fix, same day: the observed_keep_ids union
            # above (first fix) still built calib_keep_ids ADDITIVELY -
            # start from nothing, add only what the hypothesis extractor
            # can classify - so a node it can't see (an LLM-invented room
            # missing is_predicted, confirmed NOT in the observed file
            # either - not a real observed node, just untagged) fell out
            # silently. That's the same root cause as the first fix,
            # applied to a different node, not a new bug class. Rewritten
            # SUBTRACTIVE instead: start from official's own raw node set
            # (identical baseline to what official already keeps) and
            # remove only the specific predicted nodes the calibrator
            # actually scores below threshold. A node the extractor can't
            # classify is simply never subtracted, so it survives exactly
            # as official treats it - no observed/predicted classification
            # needed for this policy at all. Acceptance test: on a scene
            # whose calibrator maps every reachable support level to the
            # same value (00573), drop_ids is empty and this policy must
            # become byte-identical to official (displacement 0.00 at
            # every stage) - verify this before trusting any new number.
            drop_ids = {h.node_id for h in scored if calibrator(h.support) < support_tau}
            calib_keep_ids_int = {n["id"] for n in raw_graph["nodes"] if str(n["id"]) not in drop_ids}
            calib_out = work_dir / f"{stem}_calibrated.yaml"
            write_keep_set_yaml(raw_graph, calib_keep_ids_int, calib_out)
            policies["calibrated_support"].append(calib_out)

    return policies, node_support


def _reference_targets_and_occluders(reference_graph) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Same target/occluder split as the pinned _preprocess_groups (targets =
    object, not a door; occluders = structure, or an object whose name
    contains 'door') - reference nodes use the SAME wire format as
    completions (position/dimension/orientation string-encoded, parsed via
    smart_eval), confirmed on real data earlier this session. Orientation
    is read when present, identity only as a genuine fallback for a
    missing field - matching _preprocess_groups' own handling exactly,
    not hardcoding identity for every node regardless."""
    targets, occluders = [], []
    for node in reference_graph.get("nodes", []):
        node_type = node.get("node_type")
        if node_type not in ("object", "structure"):
            continue
        pos = smart_eval(node.get("position"))
        dims = smart_eval(node.get("dimension"))
        if pos is None or dims is None:
            continue
        orient_str = node.get("orientation")
        orient = np.eye(3) if orient_str is None else np.array(smart_eval(orient_str), dtype=float)
        obj = {"id": node["id"], "name": node.get("name", "unknown"), "pos": np.array(pos, dtype=float), "dims": np.array(dims, dtype=float), "orient": orient}
        name_lower = obj["name"].lower()
        is_door = "door" in name_lower
        if node_type == "object" and not is_door:
            targets.append(obj)
        elif node_type == "structure" or is_door:
            occluders.append(obj)
    return targets, occluders


def score_pose_against_reference(reference_optimized_sg: Dict[str, Any], pose: np.ndarray, camera_config: CameraConfig) -> int:
    """Policy-independent yardstick (advisor's recommendation): how many
    REAL reference-graph objects are visible from a chosen pose - the
    thing decision quality should actually be judged against, since raw
    IG is not comparable across policies.

    2026-09-15 correction (audit finding H3): this originally used only
    frustum culling (camera.points_are_in_view), never occlusion - on real
    data, recomputing stage 0's official/filter-only/calibrated-support
    selections with the pinned _visible_testing's ray-box occlusion test
    (against the reference's own 88 structure/door occluders, not zero)
    flipped every one of those three counts, in one case to zero. Now
    reuses _visible_testing verbatim, the same pinned method that scored
    the candidate during the actual decision, on the SAME camera config
    the decision used (see the two call sites below: the official policy's
    own camera_config for stage-1 scores, calculate_specific_pose_ig's
    near_clip=0.1/max_range=4.0 override for stage-2 - passing the wrong
    one would silently re-introduce a different fidelity gap)."""
    import calculate_uncertainty as cu
    camera = cu.Camera(config=camera_config, position=pose[:3], yaw_degrees=float(pose[3]))
    calc = UncertaintyCalculator.__new__(UncertaintyCalculator)
    visible_ids, _, _, _ = calc._visible_testing(reference_optimized_sg, camera)
    return len(visible_ids)


def top_tie_count(scored_candidates: List[Tuple[float, np.ndarray]], eps: float = 1e-9) -> int:
    if not scored_candidates:
        return 0
    top = scored_candidates[0][0]
    return sum(1 for score, _ in scored_candidates if abs(score - top) < eps)


def score_all_candidates(calc: UncertaintyCalculator, sample_observations, current_pos) -> List[Tuple[float, np.ndarray]]:
    """Same total_ig computation as the pinned _find_best_viewpoint (reuses
    its own _calculate_ig_components calls verbatim), but returns ALL
    scored candidates, not just the top 10 - needed so the risk term can
    re-rank candidates that would not have made official's own cutoff."""
    scored = []
    for group_obs_list in sample_observations:
        obj_u = calc._calculate_ig_components(group_obs_list, lambda obs: obs['names_list'])
        obj_ig = obj_u["H_y"] - obj_u["H_y_epsilon"]
        room_u = calc._calculate_ig_components(group_obs_list, lambda obs: obs['rooms_list'])
        room_ig = room_u["H_y"] - room_u["H_y_epsilon"]
        total_ig = obj_ig + calc.config.UNCERTAINTY_ROOM_WEIGHT * room_ig
        pose = group_obs_list[0]['sample']
        d = np.linalg.norm(pose[:3] - current_pos[:3])
        total_ig = total_ig - calc.config.MOVE_COST_LAMBDA * d
        scored.append((total_ig, pose))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def resolve_history_positions(run_dir: Path, up_to_stage: int) -> List[np.ndarray]:
    """Each stage's path_log.json final_path[0] (labeled "start_position")
    is the real agent position when THAT stage's planning cycle began -
    logged by the pipeline itself, not reconstructed/approximated. This
    exactly matches history_position.append(current_world_position) in
    exploration_pipeline.py, verified against the real log (gate_check.py
    reproduces stage 0's exact bounds/IG using history=[this value])."""
    history = []
    for s in range(up_to_stage + 1):
        path_log = run_dir / str(s) / "path_log.json"
        if not path_log.exists():
            break
        d = json.loads(path_log.read_text())
        history.append(np.array(d["final_path"][0]))
    return history


def replay_stage(stage_num: int, calibrator, support_tau: float, beta_values: Sequence[float]) -> Dict[str, Any]:
    stage_dir = RUN_DIR / str(stage_num)
    work_dir = OUT_DIR / f"stage{stage_num}_files"
    work_dir.mkdir(parents=True, exist_ok=True)

    history = resolve_history_positions(RUN_DIR, stage_num)
    if not history:
        return {"stage": stage_num, "error": "no history_position resolvable"}
    current_pos = history[-1]

    policy_files, node_support = build_policy_files(stage_dir, work_dir, calibrator, support_tau)
    reference_graph = yaml.safe_load(Path(REFERENCE_PATH).read_text())
    ref_targets, ref_occluders = _reference_targets_and_occluders(reference_graph)
    reference_optimized_sg = {"targets": ref_targets, "occluders": ref_occluders}

    result: Dict[str, Any] = {"stage": stage_num, "n_files_per_policy": {k: len(v) for k, v in policy_files.items()}, "policies": {}}

    # --- Official: real RNG-sampled pool (this is the one checkable against the real log) ---
    official_config = make_config(str(work_dir / "official_work"))
    Path(official_config.WORKING_DIRECTORY).mkdir(parents=True, exist_ok=True)
    official_calc = PoolReplayCalculator(official_config)
    official_files = [str(p) for p in policy_files["official"]]
    groups_official = official_calc._build_scene_graph_groups(official_files)
    mapping_official = official_calc._get_object_to_parent_mapping(official_files)
    min_pos, max_pos = official_calc._get_sampling_bounds(groups_official)
    official_sample_obs = official_calc._gather_sample_observations(groups_official, mapping_official, min_pos, max_pos)
    official_calc.mapping = mapping_official
    official_scored_all = score_all_candidates(official_calc, official_sample_obs, current_pos)
    official_top10 = [p for _, p in official_scored_all[:10]]
    official_pool_poses = np.array([obs[0]['sample'] for obs in official_sample_obs])

    stage2_official = [(official_calc.calculate_specific_pose_ig(pose, 0.0), pose) for pose in official_top10]
    stage2_official.sort(key=lambda x: x[0], reverse=True)

    result["policies"]["official"] = {
        "n_candidates_sampled": len(official_sample_obs),
        "bounds_low": min_pos.tolist(), "bounds_high": max_pos.tolist(),
        "stage1_top_ig": official_scored_all[0][0], "stage1_tie_count": top_tie_count(official_scored_all),
        "stage2_top_pose": stage2_official[0][1].tolist(), "stage2_top_ig": stage2_official[0][0],
        "reference_objects_visible": score_pose_against_reference(reference_optimized_sg, stage2_official[0][1], STAGE2_CAMERA_CONFIG),
    }

    # --- Other policies: SAME candidate pool (official_pool_poses), fresh
    # calculator instances, and each policy's own scene-graph groups. The
    # null control deliberately points at official's exact files so any
    # divergence measures this replay path rather than a graph difference. ---
    for policy_name, tau_or_none in [
        ("null_control", None),
        ("filter_only", None),
        ("calibrated_support", support_tau),
    ]:
        work_sub = work_dir / f"{policy_name}_work"
        work_sub.mkdir(parents=True, exist_ok=True)
        cfg = make_config(str(work_sub))
        calc = PoolReplayCalculator(cfg)
        files = [str(p) for p in policy_files[policy_name]]
        input_files_shared_with_official = files == official_files
        if policy_name == "null_control" and not input_files_shared_with_official:
            raise RuntimeError("null_control must reuse official's exact input files")
        groups = calc._build_scene_graph_groups(files)
        mapping = calc._get_object_to_parent_mapping(files)
        sample_obs = calc.gather_observations_for_fixed_poses(groups, mapping, official_pool_poses)
        scored_all = score_all_candidates(calc, sample_obs, current_pos)
        top10 = [p for _, p in scored_all[:10]]
        stage2 = [(calc.calculate_specific_pose_ig(pose, 0.0), pose) for pose in top10]
        stage2.sort(key=lambda x: x[0], reverse=True)
        policy_result = {
            "stage1_top_ig": scored_all[0][0], "stage1_tie_count": top_tie_count(scored_all),
            "stage2_top_pose": stage2[0][1].tolist(), "stage2_top_ig": stage2[0][0],
            "reference_objects_visible": score_pose_against_reference(reference_optimized_sg, stage2[0][1], STAGE2_CAMERA_CONFIG),
            "displacement_from_official_m": float(np.linalg.norm(stage2[0][1][:3] - stage2_official[0][1][:3])),
        }
        if policy_name == "null_control":
            policy_result["input_files_shared_with_official"] = input_files_shared_with_official
        result["policies"][policy_name] = policy_result

    # --- Combined: raw/unfiltered graph (official's own groups/mapping), risk-reweighted ---
    # R(x) does not depend on beta - compute it once per candidate, reusing
    # official_calc.optimized_groups (already preprocessed by the official
    # _gather_sample_observations call above, not recomputed here).
    risk_by_pose: Dict[int, float] = {}
    for _, pose in official_scored_all:
        visible_per_group = official_calc.visible_predicted_ids_at(official_calc.optimized_groups, pose)
        risk_terms = []
        # visible_per_group's index matches official_files'/node_support's
        # group_index exactly (both walk policies['official'] in the same
        # (scene_index, idx) order) - audit finding H6, see build_policy_files.
        for g, group_ids in enumerate(visible_per_group):
            for nid in group_ids:
                s = node_support.get((g, str(nid)))
                if s is not None:
                    risk_terms.append(1.0 - calibrator(s))
        risk_by_pose[id(pose)] = sum(risk_terms) / len(risk_terms) if risk_terms else 0.0

    combined_result = {}
    for beta in beta_values:
        risk_scored = [(total_ig - beta * risk_by_pose[id(pose)], pose, risk_by_pose[id(pose)]) for total_ig, pose in official_scored_all]
        risk_scored.sort(key=lambda x: x[0], reverse=True)
        top10_combined = [p for _, p, _ in risk_scored[:10]]
        stage2_combined = [(official_calc.calculate_specific_pose_ig(pose, 0.0), pose) for pose in top10_combined]
        stage2_combined.sort(key=lambda x: x[0], reverse=True)
        combined_result[f"beta_{beta}"] = {
            "stage1_top_score": risk_scored[0][0], "stage1_top_risk": risk_scored[0][2],
            "stage2_top_pose": stage2_combined[0][1].tolist(), "stage2_top_ig": stage2_combined[0][0],
            "reference_objects_visible": score_pose_against_reference(reference_optimized_sg, stage2_combined[0][1], STAGE2_CAMERA_CONFIG),
            "displacement_from_official_m": float(np.linalg.norm(stage2_combined[0][1][:3] - stage2_official[0][1][:3])),
        }
    result["policies"]["combined"] = combined_result
    return result


# Must match extension_policy_replay.py's SCENE_CALIBRATION_CONFIGS
# exactly (DEVIATIONS.md #61-62) - the full 4-scene LOSO calibration set.
SCENE_CALIBRATION_CONFIGS = {
    "00069": {"run": str(RUN_DIR), "reference": REFERENCE_PATH},
    "00573": {
        "run": "/workspace/runs/scene00573_seed42_calib_high32k/stages",
        "reference": "/workspace/runs/scene00573_frontier_reference/stages/53/habitat_scene_graph_original_graph0.yaml",
    },
    "00853": {
        "run": "/workspace/runs/scene00853_seed42_calib_high32k/stages",
        "reference": "/workspace/runs/scene00853_frontier_reference/stages/33/habitat_scene_graph_original_graph0.yaml",
    },
    "00871": {
        "run": "/workspace/runs/scene00871_seed42_calib_high32k/stages",
        "reference": "/workspace/runs/scene00871_frontier_reference/stages/54/habitat_scene_graph_original_graph0.yaml",
    },
}


def fit_held_out_calibrator():
    """SCENE_ID's own held-out LOSO fold - calibrator trained on the
    OTHER 3 scenes in SCENE_CALIBRATION_CONFIGS only, exactly matching
    deviations #61-62's calibration work. 2026-09-15: delegates to
    asp_offline.support_policy's shared fit_loso_calibrator/
    collect_calibration_samples (previously this function had its own,
    now-removed, independent reimplementation of the same recipe - a
    real drift risk since extension_policy_replay.py needed the
    identical fit for its own H2 fix; one implementation now serves
    both). 2026-09-17: generalized from a scene-00069-only function to
    read SCENE_ID (set by configure(), default "00069") instead of a
    hardcoded literal - the training corpus (SCENE_CALIBRATION_CONFIGS)
    is unaffected either way. Returns (calibrator, status) - status
    carries the real LOSO_CALIBRATED fields plus the by_kind room/object
    breakdown (audit finding H1) instead of a bare calibrator with no
    provenance."""
    return fit_loso_calibrator(SCENE_CALIBRATION_CONFIGS, SCENE_ID, expected_size=LLM_ENSEMBLE_COUNT)


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--scene-id", default=SCENE_ID, choices=sorted(SCENE_CALIBRATION_CONFIGS),
        help="Which SCENE_CALIBRATION_CONFIGS entry to hold OUT when fitting the calibrator (default: %(default)s).",
    )
    parser.add_argument(
        "--run", type=Path, default=RUN_DIR,
        help="stages/ dir of the run whose DECISIONS to replay - independent of --scene-id's own calibration-training run in SCENE_CALIBRATION_CONFIGS (default: %(default)s).",
    )
    parser.add_argument("--reference", default=REFERENCE_PATH, help="Reference graph for scoring this run's replayed decisions (default: %(default)s).")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument(
        "--out-filename", required=True,
        help="Never reuse an existing filename for a different run's output - always new-suffixed, this script refuses to overwrite an existing file.",
    )
    args = parser.parse_args()
    configure(scene_id=args.scene_id, run_dir=args.run, reference_path=args.reference, out_dir=args.out_dir)

    out_path = OUT_DIR / args.out_filename
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite existing {out_path} - pass a different --out-filename")

    calibrator, calibration_status = fit_held_out_calibrator()
    other_scenes = sorted(set(SCENE_CALIBRATION_CONFIGS) - {SCENE_ID})
    print(f"Fitted scene-{SCENE_ID} held-out calibrator (trained on {', '.join(other_scenes)}).")
    print(f"by_kind: {calibration_status['by_kind']}")

    support_tau = calibrator(0.75)  # beta=0 arm: calibration reaches the decision only through this filter
    print(f"calibrated_support policy tau (probability at raw support>=0.75): {support_tau:.4f}")

    beta_values = [0.0, 1.0, 5.0, 20.0]

    all_results = []
    stage_dirs = sorted((d for d in RUN_DIR.iterdir() if d.is_dir() and d.name.isdigit()), key=lambda d: int(d.name))
    for stage_dir in stage_dirs:
        stage_num = int(stage_dir.name)
        # Only stages with a resolvable path_log.json + at least one completion are replayable
        if not (stage_dir / "path_log.json").exists():
            continue
        if not list(stage_dir.glob("habitat_scene_graph_new_graph_*.yaml")):
            continue
        print(f"\n=== replaying stage {stage_num} ===")
        # 2026-09-17: a single stage's exception used to crash the whole
        # run, discarding every already-replayed stage before it (results
        # are only written to disk at the very end). Forced, no-free-
        # parameters fix, same spirit as the two skip-conditions above:
        # record which stage failed and why, keep going. Does not change
        # any stage's actual result - a stage that succeeds is scored
        # exactly as before.
        try:
            result = replay_stage(stage_num, calibrator, support_tau, beta_values)
        except Exception as exc:
            print(f"stage {stage_num} raised {exc!r} - skipping, not failing the whole run")
            result = {"stage": stage_num, "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(result, indent=2, default=str))
        all_results.append(result)

    with open(out_path, "w") as f:
        json.dump({
            "scene_id": SCENE_ID,
            "run_dir": str(RUN_DIR),
            "reference_path": str(REFERENCE_PATH),
            "calibration_trained_on": other_scenes,
            "support_tau": support_tau,
            "calibration": calibration_status,
            "beta_values": beta_values,
            "stages": all_results,
        }, f, indent=2, default=str)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
