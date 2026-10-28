"""Live completion policies for the 2026-10-28 DeepSeek 1017 campaign.

The pinned pipeline uses LLM completions in one place only: the list that
LLMManager.complete_scene_graph returns feeds select_next_target and the
global planner. A policy here rewrites those completion YAML files in place,
after the ensemble finishes and before planning, so every arm runs the same
pinned code and differs only in which nodes the planner sees.

Each policy is a keep-set over the raw author YAML, the same transform the
decision replay used (tools/decision_replay.py write_keep_set_yaml), so every
pinned-only field of a surviving node is left untouched:

- official: keep everything (the author's policy).
- filter_only: keep observed nodes plus predicted nodes that pass the
  geometric validator (decision_replay.build_policy_files "filter_only").
- unanimity: filter_only, further limited to predicted nodes that all four
  members of the track propose (support 1.0 over the raw ensemble, the
  static headline's validator_plus_unanimity_raw_tau_1_0).
- observed_only: no LLM call at all; every completion file is a copy of the
  observed graph. A $0 control, but not "ASP without predictions": with
  identical members the information gain only sees graph0/graph1
  disagreement, so unexplored space scores zero.
- placebo: no LLM call; each member gets the observed graph plus its own
  random hypotheses with the 1017 model's measured shape statistics
  (placebo_calibration.json: counts, label and size frequencies, rooms
  1.5-3.5 m from an observed room and linked like the LLM's, objects around
  new or observed rooms, rooms unflagged and objects flagged as the LLM
  does), drawn independently per member. official vs placebo asks whether
  the LLM's scene-conditioned content matters, not merely whether
  hypotheses exist.

The two no-LLM arms sleep per planning step (ASP_LIVE_NO_LLM_DELAY_SCHEDULE,
seconds for stages 0, 1, ..., last value repeating) so Hydra gets about the
catch-up time the LLM arms get while they wait.

Raw completions are archived under <stage>/live_policy_raw/attempt_<n>/ so
nothing the evaluators glob for changes name or place.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import time
from typing import Any, Dict, List, Optional, Sequence, Set

import yaml

POLICIES = ("official", "filter_only", "unanimity", "observed_only", "placebo")
NO_LLM_POLICIES = ("observed_only", "placebo")
ENV_VAR = "ASP_LIVE_POLICY"
DELAY_ENV_VAR = "ASP_LIVE_NO_LLM_DELAY_S"
SCHEDULE_ENV_VAR = "ASP_LIVE_NO_LLM_DELAY_SCHEDULE"
SUMMARY_NAME = "live_policy.jsonl"
RAW_DIR_NAME = "live_policy_raw"



def policy_from_env() -> str:
    """Fail closed: an unset or unknown policy stops the run before it starts."""
    policy = os.environ.get(ENV_VAR, "").strip()
    if policy not in POLICIES:
        raise SystemExit(f"{ENV_VAR} must be one of {POLICIES}, got {policy!r}")
    return policy


def graph_id_of(path: str) -> int:
    stem = os.path.splitext(os.path.basename(path))[0]
    return int(stem.rsplit("_", 1)[1])


def _load_raw(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f) or {"nodes": [], "edges": []}


def write_keep_set_yaml(raw_graph: Dict[str, Any], keep_ids: Optional[Set[Any]], out_path: str) -> None:
    """Same contract as tools/decision_replay.py write_keep_set_yaml."""
    nodes = raw_graph.get("nodes") or []
    edges = raw_graph.get("edges") or []
    kept_nodes = nodes if keep_ids is None else [n for n in nodes if n["id"] in keep_ids]
    kept = {n["id"] for n in kept_nodes}
    kept_edges = [e for e in edges if e[0] in kept and e[1] in kept]
    with open(out_path, "w") as f:
        yaml.safe_dump({"nodes": kept_nodes, "edges": kept_edges}, f)


def track_keep_sets(policy: str, observed_path: str, raw_paths: Sequence[str], ensemble_size: int) -> List[Optional[Set[Any]]]:
    """Keep-set of raw node ids for each completion in one scene track.
    None means keep everything."""
    if policy == "official":
        return [None for _ in raw_paths]

    from asp_offline.author_io import load_author_graph
    from asp_offline.support_policy import support_filtered_graph
    from asp_offline.validator import ValidationConfig, validate_completion

    observed = load_author_graph(observed_path, observed=True)
    ensemble = [load_author_graph(p) for p in raw_paths]
    config = ValidationConfig(allow_parsed_mapping=True)
    keep_sets: List[Optional[Set[Any]]] = []
    for raw_path, completion in zip(raw_paths, ensemble):
        raw_graph = _load_raw(raw_path)
        result = validate_completion(completion, observed, config)
        observed_ids = {str(n["id"]) for n in result.graph["nodes"] if n.get("observed", False)}
        valid_predicted = {str(n["id"]) for n in result.graph["nodes"] if not n.get("observed", False)}
        if policy == "filter_only":
            keep = observed_ids | valid_predicted
        elif policy == "unanimity":
            support_graph = support_filtered_graph(observed, completion, ensemble, 1.0, expected_size=ensemble_size)
            unanimous = {str(n["id"]) for n in support_graph["nodes"] if not n.get("observed", False)}
            keep = observed_ids | (valid_predicted & unanimous)
        else:
            raise ValueError(f"no keep-set rule for policy {policy!r}")
        keep_sets.append({n["id"] for n in raw_graph.get("nodes") or [] if str(n["id"]) in keep})
    return keep_sets


def _archive_dir(working_dir: str) -> str:
    root = os.path.join(working_dir, RAW_DIR_NAME)
    os.makedirs(root, exist_ok=True)
    attempt = len([d for d in os.listdir(root) if d.startswith("attempt_")])
    path = os.path.join(root, f"attempt_{attempt}")
    os.makedirs(path)
    return path


def _counts(raw_graph: Dict[str, Any], keep: Optional[Set[Any]]) -> Dict[str, int]:
    nodes = raw_graph.get("nodes") or []
    predicted = [n for n in nodes if n.get("is_predicted")]
    kept = nodes if keep is None else [n for n in nodes if n["id"] in keep]
    return {
        "nodes": len(nodes),
        "predicted": len(predicted),
        "kept_nodes": len(kept),
        "kept_predicted": len([n for n in kept if n.get("is_predicted")]),
    }


def apply_policy(policy: str, working_dir: str, generated_files: Sequence[str], ensemble_size: int,
                 llm_wait_s: Optional[float] = None) -> Dict[str, Any]:
    """Rewrite the completion files in place and append a summary line."""
    record: Dict[str, Any] = {"ts": time.time(), "policy": policy, "working_dir": working_dir, "tracks": {},
                              "llm_wait_s": llm_wait_s}
    if policy != "official":
        archive = _archive_dir(working_dir)
        record["raw_archive"] = archive
    by_track: Dict[int, List[str]] = {}
    for path in generated_files:
        by_track.setdefault(graph_id_of(path) // ensemble_size, []).append(path)
    for track, paths in sorted(by_track.items()):
        paths = sorted(paths, key=graph_id_of)
        observed_path = os.path.join(working_dir, f"habitat_scene_graph_original_graph{track}.yaml")
        keep_sets = track_keep_sets(policy, observed_path, paths, ensemble_size)
        members = []
        for path, keep in zip(paths, keep_sets):
            raw_graph = _load_raw(path)
            if policy != "official":
                shutil.copy2(path, os.path.join(archive, os.path.basename(path)))
                write_keep_set_yaml(raw_graph, keep, path)
            members.append({"graph_id": graph_id_of(path), **_counts(raw_graph, keep)})
        record["tracks"][str(track)] = {"available": len(paths), "members": members}
    with open(os.path.join(working_dir, SUMMARY_NAME), "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def _vec(value: Any) -> List[float]:
    import ast

    return [float(x) for x in (ast.literal_eval(value) if isinstance(value, str) else value)]


def _fmt(values: Sequence[float]) -> str:
    return "[" + ", ".join(f"{v:.3f}" for v in values) + "]"


CALIBRATION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "placebo_calibration.json")


def load_calibration(path: str = CALIBRATION_PATH) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _weighted(rng: Any, table: Dict[str, int]) -> str:
    keys = sorted(table)
    weights = [float(table[k]) for k in keys]
    total = sum(weights)
    return keys[int(rng.choice(len(keys), p=[w / total for w in weights]))]


def placebo_graph(observed: Dict[str, Any], rng: Any, calib: Dict[str, Any]) -> Dict[str, Any]:
    """Placebo v2: hypotheses with the 1017 model's measured shape statistics
    (how many, which labels and sizes, how far from the map, how linked, how
    flagged) but no conditioning on this scene's content. No navmesh or
    structure check: the LLM has neither."""
    nodes = list(observed.get("nodes") or [])
    edges = [list(e) for e in observed.get("edges") or []]
    positioned = [n for n in nodes if "position" in n]
    if not positioned:
        return {"nodes": nodes, "edges": edges}
    obs_xy = [_vec(n["position"])[:2] for n in positioned]
    obs_obj_xy = [_vec(n["position"])[:2] for n in positioned if n.get("node_type") == "object"]
    rooms = [n for n in positioned if n.get("node_type") == "room"]
    anchors = rooms or positioned
    objects = [n for n in nodes if n.get("node_type") == "object" and "dimension" in n]
    floor_z = min((_vec(n["position"])[2] - _vec(n["dimension"])[2] / 2 for n in objects), default=0.0)
    room_z = sorted(_vec(n["position"])[2] for n in rooms)[len(rooms) // 2] if rooms else floor_z + 1.3
    next_id = max(int(n["id"]) for n in nodes) + 1

    def dist2(xy, others):
        return min(((xy[0] - a) ** 2 + (xy[1] - b) ** 2 for a, b in others), default=float("inf"))

    def around(center, lo, hi):
        theta = rng.uniform(0.0, 2.0 * math.pi)
        r = rng.uniform(lo, hi)
        return [center[0] + r * math.cos(theta), center[1] + r * math.sin(theta)]

    def nearest_rooms(xy, k):
        ranked = sorted(rooms, key=lambda n: dist2(xy, [_vec(n["position"])[:2]]))
        return ranked[:k]

    new_rooms: List[Dict[str, Any]] = []
    n_rooms = 2 if rng.random() < calib["rooms_p2"] else 1
    for _ in range(n_rooms):
        for _attempt in range(100):
            anchor = anchors[int(rng.integers(len(anchors)))]
            xy = around(_vec(anchor["position"]), *calib["room_radius_m"])
            if dist2(xy, obs_xy) >= calib["room_min_clearance_m"] ** 2:
                break
        else:
            continue
        room = {"id": next_id, "name": _weighted(rng, calib["room_names"]), "node_type": "room",
                "position": _fmt([xy[0], xy[1], room_z])}
        links = nearest_rooms(xy, 2)
        if links:
            edges.append([next_id, links[0]["id"]])
            if len(links) > 1 and rng.random() < calib["room_second_link_p"]:
                edges.append([next_id, links[1]["id"]])
        new_rooms.append(room)
        next_id += 1

    n_objects = int(min(calib["objects_max"], max(calib["objects_min"], rng.poisson(calib["objects_poisson_mean"]))))
    new_objects: List[Dict[str, Any]] = []
    for _ in range(n_objects):
        use_new = bool(new_rooms) and rng.random() < calib["object_new_room_frac"]
        for _attempt in range(100):
            if use_new:
                parent = new_rooms[int(rng.integers(len(new_rooms)))]
                xy = around(_vec(parent["position"]), *calib["object_new_room_radius_m"])
            else:
                parent = anchors[int(rng.integers(len(anchors)))]
                xy = around(_vec(parent["position"]), *calib["object_observed_room_radius_m"])
            if dist2(xy, obs_obj_xy) >= calib["object_min_clearance_m"] ** 2:
                break
        else:
            continue
        dims = [float(x) for x in calib["dims_pool"][int(rng.integers(len(calib["dims_pool"])))]]
        node = {"id": next_id, "name": _weighted(rng, calib["labels"]), "node_type": "object", "is_predicted": True,
                "dimension": _fmt(dims), "orientation": "[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]",
                "position": _fmt([xy[0], xy[1], floor_z + dims[2] / 2])}
        if parent.get("node_type") == "room":
            edges.append([next_id, parent["id"]])
        new_objects.append(node)
        next_id += 1
    return {"nodes": nodes + new_rooms + new_objects, "edges": edges}


def pacing_delay(stage: int) -> float:
    """Per-stage sleep for the no-LLM arms. ASP_LIVE_NO_LLM_DELAY_SCHEDULE is
    a comma list for stages 0, 1, ...; its last value repeats. Falls back to
    the single ASP_LIVE_NO_LLM_DELAY_S."""
    schedule = [float(x) for x in os.environ.get(SCHEDULE_ENV_VAR, "").split(",") if x.strip()]
    if schedule:
        return schedule[min(stage, len(schedule) - 1)]
    return float(os.environ.get(DELAY_ENV_VAR, "0") or 0)


def _stage_number(working_dir: str) -> int:
    name = os.path.basename(os.path.normpath(working_dir))
    return int(name) if name.isdigit() else 0


def _rerun_index(working_dir: str) -> int:
    """n for a run directory named ..._rerun<n> (stage dirs sit in <run>/stages/<k>), else 0."""
    run = os.path.basename(os.path.dirname(os.path.dirname(os.path.normpath(working_dir))))
    m = re.search(r"_rerun(\d+)$", run)
    return int(m.group(1)) if m else 0


def no_llm_completions(manager: Any, initial_dsg_paths: Sequence[str], policy: str) -> List[str]:
    """Stand-in for complete_scene_graph that makes no LLM call. observed_only
    copies the observed graph to every member; placebo gives every member its
    own random hypotheses (seeded by SEED, stage and graph id)."""
    import numpy as np

    config = manager.config
    working_dir = config.WORKING_DIRECTORY
    ensemble_size = config.LLM_ENSEMBLE_COUNT
    t0 = time.time()
    processed = [manager._preprocess_dsg(p, scene_index=i) for i, p in enumerate(initial_dsg_paths)]
    calib = load_calibration() if policy == "placebo" else None
    # The pipeline retries a planning step that fails (e.g. every candidate
    # viewpoint unreachable). The LLM arm then gets fresh samples, so the
    # placebo must too: retries draw with the attempt number added to the
    # seed; first attempts keep the original seed (2026-10-28 fix).
    summary_path = os.path.join(working_dir, SUMMARY_NAME)
    attempt = sum(1 for _ in open(summary_path)) if os.path.exists(summary_path) else 0
    # A rerun of an excluded run (run dir ..._rerun<n>) must not replay the
    # original's draws, as an LLM rerun would not. The salt goes last and is
    # never 0: numpy seeds [a, b] and [a, b, 0] identically.
    rerun = _rerun_index(working_dir)
    out = []
    record: Dict[str, Any] = {"ts": t0, "policy": policy, "working_dir": working_dir, "tracks": {}, "attempt": attempt, "rerun": rerun}
    for track, observed_path in enumerate(processed):
        observed = _load_raw(observed_path)
        members = []
        for member in range(ensemble_size):
            graph_id = track * ensemble_size + member
            dst = os.path.join(working_dir, f"habitat_scene_graph_new_graph_{graph_id}.yaml")
            if policy == "observed_only":
                shutil.copyfile(observed_path, dst)
                members.append({"graph_id": graph_id, **_counts(observed, None)})
            else:
                key = [int(config.SEED), _stage_number(working_dir), graph_id]
                key += [attempt, rerun] if rerun else ([attempt] if attempt else [])
                rng = np.random.default_rng(key)
                graph = placebo_graph(observed, rng, calib)
                with open(dst, "w") as f:
                    yaml.safe_dump(graph, f)
                members.append({"graph_id": graph_id, **_counts(graph, None)})
            out.append(dst)
        record["tracks"][str(track)] = {"available": ensemble_size, "members": members}
    delay = pacing_delay(_stage_number(working_dir))
    remaining = delay - (time.time() - t0)
    if remaining > 0:
        time.sleep(remaining)
    record["delay_s"] = delay
    with open(os.path.join(working_dir, SUMMARY_NAME), "a") as f:
        f.write(json.dumps(record) + "\n")
    return out


def observed_only_completions(manager: Any, initial_dsg_paths: Sequence[str]) -> List[str]:
    return no_llm_completions(manager, initial_dsg_paths, "observed_only")


def install(manager_cls: Any, policy: str) -> None:
    """Wrap LLMManager.complete_scene_graph with the chosen policy."""
    original = manager_cls.complete_scene_graph

    def complete_scene_graph(self, initial_dsg_paths):
        if policy in NO_LLM_POLICIES:
            return no_llm_completions(self, initial_dsg_paths, policy)
        t0 = time.time()
        files = original(self, initial_dsg_paths)
        if not files:
            return files
        try:
            apply_policy(policy, self.config.WORKING_DIRECTORY, files, self.config.LLM_ENSEMBLE_COUNT,
                         llm_wait_s=round(time.time() - t0, 3))
        except Exception as e:
            # Planning on unfiltered graphs would silently turn a policy arm
            # into the official arm. Fail the stage instead; the pipeline's
            # own retry loop and the watcher's stall check take it from here.
            print(f"[live_policy] FAILED to apply {policy}: {e!r}", flush=True)
            raise
        return files

    complete_scene_graph.__wrapped__ = original
    manager_cls.complete_scene_graph = complete_scene_graph
