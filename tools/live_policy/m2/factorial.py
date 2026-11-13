#!/usr/bin/env python3
"""M2 factorial arms (PREREGISTRATION_M2.md, sha256 5b8a8400..., §3 and §4) on the October bench's stages.

For each bench stage this builds new member graphs, scores the SAME 300 first-stage candidates with the
SAME replay and scorer the bench uses (work_A/fastig.py `Scorer`), and returns per candidate: the R1 score
`ig - 0.2 * d` (ig = sum of the scorer's two columns, d = 3-D distance from the current pose, as bench.py
computes R1), `ig` alone, and the yardsticks Uwall, Ucone (the bench's U_wall_cone, PRIMARY), Ucone_audit
(the audit's U_cone, no wall test) and U360; plus R1 regret under Uwall and Ucone as bench.py defines it.

Arms: F1 (bench oracle graphs), F5a/F5b (bench placebo graphs), F6 (observed graph of the track), F0 (all
unmapped reference objects, rooms of the track's first F1 graph), F3-<model> (F1 with every oracle object
moved), F-room (typical objects in the unseen typed regions).

Registered code is imported, never edited: bench.py (`wall_visible`, `cone_mask`, `write_yaml`, `RUNS`,
`RUN_IDX`, `SALT`, `BENCH_SEED`, `CALIB`), audit.py (`mapped_masks`, `ref_geom`, `vis`, `vis360`,
`observed_nodes`, `REF`), replay/replay2 (`P`, `stage_meta`, `gids_for`, `current_pos`, `load`, `lp`), fastig
(`Scorer`), live_policy (`oracle_graph`, `placebo_graph`). Lines COPIED, each marked where it stands:
bench.stage B:213-260 (set-up, replay check, yardsticks), B:272-284 (the F1/F5 loop), B:288-295 and B:311
(scoring, R1), B:320-323 (regret), bench.main B:366-374 (stage list); bench.guessed (B:151); the floor/room
height lines of placebo_graph (LP:216-219); the object node and parent-room lines of oracle_graph
(LP:347-357). The copies let the graph builders run without the bench's /tmp farm.

RULE: the CLI refuses to run unless PREREGISTRATION_M2.sha256 holds the sha256 of PREREGISTRATION_M2.md.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.dont_write_bytecode = True
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
LP_DIR = HERE.parent

# =====================================================================================
# Values fixed by PREREGISTRATION_M2.md
# =====================================================================================
MASTER_SEED = 20261113            # §4: default_rng([20261113, run_idx, k, g, c])
ARM_CODE = {"F-room": 11, "F3-deepseek": 21, "F3-haiku": 22, "F3-opus": 23}   # c, §4
LAMBDA = 0.2                      # §3; checked equal to bench.LAMBDA
FARM = "/tmp/cvp_review"
BENCH_PATH = Path(os.environ.get("M2_BENCH_PATH") or LP_DIR / "review_2026-10-29" / "bench" / "build" / "bench.py")
PREREG = LP_DIR / "PREREGISTRATION_M2.md"
PREREG_SHA = LP_DIR / "PREREGISTRATION_M2.sha256"
YARDSTICKS = ("Uwall", "Ucone", "Ucone_audit", "U360")   # Ucone is primary
REGRET_YARDSTICKS = ("Uwall", "Ucone")
MODELS = ("deepseek", "haiku", "opus")

# =====================================================================================
# Readings where the file is silent (listed in the report)
# =====================================================================================
# F0 "every unmapped reference object": the bench's yardstick mask `un` (au.mapped_masks primary, over both
#     tracks' observed nodes), the same for both tracks of a stage.
# F0 "the track's first F1 graph": the first id of that track in rp2.gids_for(run, k) order.
# F-room: the room node's name is "an image of a <type>" (the scorer never reads it); room nodes carry no
#     edge; the "other scene" for n_T is the other of 00853/00871; a type with no region there pools all its
#     typed regions (regions with at least one scored type); n_T is not rounded; weights of a type with an
#     empty label pool are 0; if every weight is 0 the member gets rooms and no objects.
FROOM_ROOM_NAME = {
    "bathroom": "an image of a bathroom", "bedroom": "an image of a bedroom",
    "kitchen": "an image of a kitchen", "laundry": "an image of a laundry room",
    "living": "an image of a living room"}
FROOM_OTHER_SCENE = {"00853": "00871", "00871": "00853"}

# =====================================================================================
# Lazy loaders
# =====================================================================================
_REG: Dict[str, Any] = {}
_MODS: Dict[str, Any] = {}


def _load_file(alias: str, path: Path):
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(alias, None)
        raise
    return mod


def lp():
    """live_policy.py by file path (the folder has no __init__.py)."""
    if "lp" not in _MODS:
        _MODS["lp"] = _load_file("m2_live_policy", LP_DIR / "live_policy.py")
    return _MODS["lp"]


def sem():
    """semantic.region_truth (rt), semantic.extract_preds (ep), semantic.model (M), by file path."""
    if "rt" not in _MODS:
        sd = LP_DIR / "semantic"
        _MODS["rt"] = _load_file("m2_region_truth", sd / "region_truth.py")
        _MODS["ep"] = _load_file("m2_extract_preds", sd / "extract_preds.py")
        _MODS["M"] = sys.modules["semantic_model"]
    return _MODS["rt"], _MODS["ep"], _MODS["M"]


def reg() -> Dict[str, Any]:
    """The registered bench and its imports. Needs the /tmp farm."""
    if not _REG:
        mod = _load_file("bench_registered", BENCH_PATH)
        _REG.update(bench=mod, au=mod.au, rp=mod.rp, rp2=mod.rp2, fastig=mod.fastig)
        if mod.LAMBDA != LAMBDA:
            raise RuntimeError(f"bench LAMBDA {mod.LAMBDA} differs from this file's {LAMBDA}")
    return _REG


# =====================================================================================
# Pure parts: seeds, error sample, displacement
# =====================================================================================
def seed_key(run_idx: int, stage: int, gid: int, code: int) -> List[int]:
    """§4: [20261113, run_idx, k, g, c]."""
    return [MASTER_SEED, int(run_idx), int(stage), int(gid), int(code)]


def f3_code(model: str) -> int:
    return ARM_CODE[f"F3-{model}"]


def load_error_sample(path: str) -> np.ndarray:
    """The error file: distances in metres. Chosen format: a JSON list of numbers, e.g. [0.31, 1.2, 0.07].
    Also read: JSON {"distances": [...]}, .npy, and text with numbers separated by commas, spaces or new
    lines (# starts a comment). Every value must be finite and >= 0; the file must not be empty."""
    p = Path(path)
    if p.suffix == ".json":
        doc = json.loads(p.read_text())
        vals = doc["distances"] if isinstance(doc, dict) else doc
    elif p.suffix == ".npy":
        vals = np.load(p)
    else:
        vals = []
        for line in p.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                vals += [float(x) for x in re.split(r"[,\s]+", line) if x]
    arr = np.asarray(vals, dtype=float).ravel()
    if arr.size == 0:
        raise ValueError(f"{path}: empty error sample")
    if not np.all(np.isfinite(arr)) or np.any(arr < 0):
        raise ValueError(f"{path}: distances must be finite and >= 0")
    return arr


def draw_displacements(sample: np.ndarray, n: int, rng) -> tuple:
    """n displacements: distances drawn from `sample` with replacement, angles uniform on [0, 2 pi).
    Order: all n distances, then all n angles. Returns (dx, dy, dist, theta)."""
    dist = np.asarray(sample, float)[rng.integers(0, len(sample), size=n)]
    theta = rng.uniform(0.0, 2.0 * math.pi, size=n)
    return dist * np.cos(theta), dist * np.sin(theta), dist, theta


def guessed(graph: dict, obs_ids: set) -> List[dict]:
    """Copied from bench.guessed (B:151): object nodes with a position whose id is not an observed id."""
    return [n for n in graph["nodes"] if n.get("node_type") == "object" and n["id"] not in obs_ids and "position" in n]


def displace_oracle_graph(graph: dict, obs_ids: set, sample: np.ndarray, rng, move: bool = True) -> tuple:
    """F3-m for one member: a copy of its F1 graph in which every guessed object takes its own draw
    (distance with replacement from the sample, direction uniform) and moves horizontally. z, id, label,
    size and edges stay. No rejection. move=False (a member whose oracle draw fell back to placebo objects)
    returns a copy and draws nothing."""
    g = {k: copy.deepcopy(v) for k, v in graph.items()}
    idx = [i for i, n in enumerate(g["nodes"])
           if n.get("node_type") == "object" and n["id"] not in obs_ids and "position" in n]
    if not move or not idx:
        return g, {"n_moved": 0, "mean_dist": None}
    dx, dy, dist, _ = draw_displacements(sample, len(idx), rng)
    L = lp()
    for j, i in enumerate(idx):
        x, y, z = L._vec(g["nodes"][i]["position"])
        g["nodes"][i]["position"] = L._fmt([x + float(dx[j]), y + float(dy[j]), z])
    return g, {"n_moved": len(idx), "mean_dist": float(np.mean(dist))}


# =====================================================================================
# Pure parts: F0
# =====================================================================================
def build_f0_graph(f1_graph: dict, obs_ids: set, refs: Sequence[dict], unmapped: np.ndarray) -> tuple:
    """F0 for one track: the rooms of the track's first F1 graph (its observed nodes and its hypothesised
    rooms; its guessed objects and their edges are dropped) plus EVERY unmapped reference object at its
    true place, each linked to the nearest room (object lines copied from oracle_graph LP:347-357)."""
    L = lp()
    keep = [n for n in f1_graph["nodes"] if not (n.get("node_type") == "object" and n["id"] not in obs_ids and "position" in n)]
    ids = {n["id"] for n in keep}
    edges = [list(e) for e in f1_graph.get("edges") or [] if e[0] in ids and e[1] in ids]
    rooms = [n for n in keep if n.get("node_type") == "room" and "position" in n]
    next_id = max(int(n["id"]) for n in keep) + 1
    new = []
    for i in np.nonzero(np.asarray(unmapped, bool))[0]:
        c = refs[int(i)]
        new.append({"id": next_id, "name": c["name"], "node_type": "object", "is_predicted": True,
                    "dimension": L._fmt(c["dimension"]),
                    "orientation": "[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]",
                    "position": L._fmt(c["position"])})
        if rooms:
            parent = min(rooms, key=lambda r: (L._vec(r["position"])[0] - c["position"][0]) ** 2
                         + (L._vec(r["position"])[1] - c["position"][1]) ** 2)
            edges.append([next_id, parent["id"]])
        next_id += 1
    g = {k: copy.deepcopy(v) for k, v in f1_graph.items() if k not in ("nodes", "edges")}
    g["nodes"] = copy.deepcopy(keep) + new
    g["edges"] = edges
    return g, {"n_objects": len(new)}


# =====================================================================================
# Pure parts: F-room
# =====================================================================================
def detector_label_of(raw_name: str, labels) -> Optional[str]:
    """The detector's word for an annotated object, or None if it has none in the vocabulary.
    The detector table (labels._DETECTOR_LABEL, a private name) first; else the object's own canonical
    class if that is a detector class; else the first class it answers to that is one."""
    vocab = labels.detector_vocab()
    tbl = getattr(labels, "_DETECTOR_LABEL", None) or {}
    w = tbl.get(str(raw_name).lower())
    if w is not None and labels.normalise(w) in vocab:
        return w
    c = labels.normalise(raw_name)
    if c is not None and c in vocab:
        return c
    cs = sorted(labels.answers_to(raw_name) & vocab)
    return cs[0] if cs else None


def froom_tables(truth_other, labels, room_types: Sequence[str]) -> Dict[str, dict]:
    """Per scored type T, from the OTHER scene: n = mean number of detector-vocabulary reference objects
    per region of type T (not rounded) and the pool of those objects' detector labels, one entry per
    object. If the other scene has no region of type T, n and the pool come from all its typed regions
    pooled (regions with at least one scored type); "pooled" is then True."""
    def stats(regs):
        pool, counts = [], []
        for r in regs:
            labs = [detector_label_of(o.raw_name, labels) for o in r.ref_objects]
            labs = [x for x in labs if x is not None]
            counts.append(len(labs))
            pool += labs
        return (float(np.mean(counts)) if regs else 0.0), pool, len(regs)

    typed = [r for r in truth_other.regions.values() if any(t in r.types for t in room_types)]
    out = {}
    for T in room_types:
        regs = [r for r in truth_other.regions.values() if T in r.types]
        pooled = not regs
        n, pool, n_regs = stats(typed if pooled else regs)
        out[T] = {"n": n, "pool": pool, "n_regions": n_regs, "pooled": pooled}
    return out


def region_floor_cells(truth, rid: int) -> tuple:
    """(ix, iy) of the region's floor mask (its `any` mask if it has no floor). Reads GridSceneTruth's
    private `_floor` and `_index`, which already hold that fallback."""
    i = truth._index[int(rid)]
    iy, ix = np.nonzero(truth._floor[i])
    return ix, iy


def sample_in_floor(truth, rid: int, rng, n: int) -> np.ndarray:
    """n points uniform in the region's floor mask: a uniform cell, then a uniform point in the cell."""
    ix, iy = region_floor_cells(truth, rid)
    if len(ix) == 0 or n <= 0:
        return np.zeros((0, 2))
    pick = rng.integers(0, len(ix), size=n)
    u = rng.uniform(0.0, 1.0, size=(n, 2))
    cs = truth._cs
    return np.column_stack([truth._ox + (ix[pick] + u[:, 0]) * cs, truth._oy + (iy[pick] + u[:, 1]) * cs])


def froom_categories(truth, state, scored_types: Sequence[str]) -> List[tuple]:
    """(region id, type) for each unseen region and each scored type it has, in order of region id and
    then type. A region with two types appears once for each."""
    return [(rid, T) for rid in sorted(state.unseen) for T in sorted(t for t in truth.regions[rid].types if t in scored_types)]


def build_froom_graph(observed: dict, rng, calib: dict, truth, state, tables: Dict[str, dict], n_objects: int,
                      scored_types: Sequence[str]) -> tuple:
    """F-room for one member, on its own track's observed graph (PREREGISTRATION_M2.md §4).
    Categories (region, type) over the unseen typed regions; the member's N = `n_objects` (the count its F1
    graph holds) are shared among them in proportion to n_T by ONE multinomial draw (the first draw from
    `rng`); then, per category in order: labels (with replacement from the type's pool), places (uniform in
    the region's floor mask), sizes (calibration dims_pool). Height follows placebo_graph. Room nodes first,
    ids from max observed id + 1 in category order (so the same in every member of a track), then objects;
    each object has one edge, to its region's first room node. No unseen typed region: the observed graph
    unchanged (the member's F6 graph)."""
    L = lp()
    nodes = list(observed.get("nodes") or [])
    edges = [list(e) for e in observed.get("edges") or []]
    cats = froom_categories(truth, state, scored_types)
    info = {"n_categories": len(cats), "n_rooms": 0, "n_objects": 0, "no_unseen_typed": not cats,
            "n_target": int(n_objects), "counts": []}
    positioned = [n for n in nodes if "position" in n]
    if not cats or not positioned:
        info["no_unseen_typed"] = not cats
        return {"nodes": nodes, "edges": edges}, info
    rooms = [n for n in positioned if n.get("node_type") == "room"]
    objects = [n for n in nodes if n.get("node_type") == "object" and "dimension" in n]
    # copied from placebo_graph (LP:216-219)
    floor_z = min((L._vec(n["position"])[2] - L._vec(n["dimension"])[2] / 2 for n in objects), default=0.0)
    room_z = sorted(L._vec(n["position"])[2] for n in rooms)[len(rooms) // 2] if rooms else floor_z + 1.3
    next_id = max(int(n["id"]) for n in nodes) + 1
    dims_pool = calib["dims_pool"]
    w = np.array([tables[T]["n"] if tables[T]["pool"] else 0.0 for _, T in cats], float)
    counts = rng.multinomial(int(n_objects), w / w.sum()) if w.sum() > 0 else np.zeros(len(cats), int)
    info["counts"] = [int(c) for c in counts]
    room_of_region: Dict[int, int] = {}
    new_rooms, new_objects = [], []
    for rid, T in cats:
        cx, cy = truth.regions[rid].centroid_xy
        new_rooms.append({"id": next_id, "name": FROOM_ROOM_NAME[T], "node_type": "room",
                          "position": L._fmt([cx, cy, room_z])})
        room_of_region.setdefault(rid, next_id)
        next_id += 1
    for (rid, T), c in zip(cats, counts):
        c = int(c)
        if c == 0:
            continue
        pool = tables[T]["pool"]
        labs = rng.integers(0, len(pool), size=c)
        xy = sample_in_floor(truth, rid, rng, c)
        dix = rng.integers(0, len(dims_pool), size=c)
        for j in range(c):
            dims = [float(x) for x in dims_pool[int(dix[j])]]
            new_objects.append({
                "id": next_id, "name": pool[int(labs[j])], "node_type": "object", "is_predicted": True,
                "dimension": L._fmt(dims), "orientation": "[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]",
                "position": L._fmt([float(xy[j][0]), float(xy[j][1]), floor_z + dims[2] / 2])})
            edges.append([next_id, room_of_region[rid]])
            next_id += 1
    info["n_rooms"], info["n_objects"] = len(new_rooms), len(new_objects)
    return {"nodes": nodes + new_rooms + new_objects, "edges": edges}, info


# =====================================================================================
# Stage: set-up (copied from bench.stage), arms, outcomes
# =====================================================================================
def regret_r1(score: np.ndarray, U: np.ndarray) -> float:
    """bench.stage B:320-323: max U - U[pick], pick = argmax of the R1 score."""
    return float(int(np.max(U)) - U[int(np.argmax(score))])


def stage_context(run: str, k: int, meta: dict) -> dict:
    """Everything an arm needs for one stage. Copied from bench.stage B:213-260 (the replay check, the
    unmapped mask, U_wall, U_cone, U_360, d), without the sensitivity variants; adds the audit's wall-less
    U_cone (audit.py AU:171, 173) as Ucone_audit."""
    R = reg()
    bench, au, rp, rp2, fastig = R["bench"], R["au"], R["rp"], R["rp2"], R["fastig"]
    scene = run.split("_")[1]
    seed = rp.P[run]["cfg"]["SEED"]
    ridx = bench.RUN_IDX[run]
    gids = rp2.gids_for(run, k, meta)
    sd = f"{rp.RUNS}/{run}/stages/{k}"
    cur = rp.current_pos(run, k)
    act_files = [f"{sd}/habitat_scene_graph_new_graph_{g}.yaml" for g in gids]
    scorer = fastig.Scorer(act_files, seed)
    kept, sc, total, order = scorer.first_stage(seed, meta["nprior"], cur)
    tops = rp.P[run]["stages"][str(k)]["pose_tops"][-1]["top"]
    top_rep = [kept[i] for i in order[:10]]
    match = len(tops) == len(top_rep) and all(np.allclose(a, b, atol=1e-6) for a, b in zip(tops, top_rep))
    ctx = {"run": run, "stage": k, "scene": scene, "seed": seed, "run_idx": ridx, "gids": gids, "sd": sd,
           "cur": cur, "kept": kept, "n_cand": int(len(kept)), "top10_match": bool(match), "arm_of_run": rp.arm_of(run)}
    if not match or len(kept) == 0:
        ctx["drop"] = "top10 mismatch" if len(kept) else "no candidates"
        return ctx
    refs = au.REF[str(int(scene))]["objects"]
    nodes = au.observed_nodes(run, k)
    m_prim, _ = au.mapped_masks(refs, nodes)
    un = ~m_prim
    rxy = np.array([o["position"][:2] for o in refs], float)
    wv = bench.wall_visible(scene, kept[:, :2], rxy)
    Uw_set = wv & un[None, :]
    cone = bench.cone_mask(kept, refs)
    Uw = Uw_set.sum(1)
    Uc = (Uw_set & cone).sum(1)
    geom_obs, _ = au.ref_geom(refs, nodes)
    v360 = au.vis360(geom_obs, kept, fastig.second_cfg())
    U3 = (v360 & un).sum(1)
    Uca = (au.vis(geom_obs, kept, fastig.cu.CameraConfig()) & un).sum(1)
    d = np.linalg.norm(kept[:, :3] - cur[:3], axis=1)
    obs_paths = {t: f"{sd}/habitat_scene_graph_original_graph{t}.yaml" for t in sorted({g // 4 for g in gids})}
    obs_graph = {t: rp.load(p) for t, p in obs_paths.items()}
    ctx.update(refs=refs, un=un, yard={"Uwall": Uw, "Ucone": Uc, "Ucone_audit": Uca, "U360": U3}, d=d,
               obs_paths=obs_paths, obs_graph=obs_graph,
               obs_ids={t: {n["id"] for n in g["nodes"]} for t, g in obs_graph.items()},
               n_ref=len(refs), n_unmapped=int(un.sum()))
    return ctx


def _stage_row_for_semantic(ctx: dict, track: int):
    """semantic.model.Row for this stage, as extract_preds.load_row builds it: the observed graph of
    `track`, and the path = start pose + every executed-path point of stages 1..k."""
    rt, ep, M = sem()
    rp = reg()["rp"]
    run_dir = Path(rp.RUNS) / ctx["run"]
    observed = ep.read_graph(run_dir / "stages" / str(ctx["stage"]) / f"habitat_scene_graph_original_graph{track}.yaml")
    first = ep._world_path(run_dir / "stages" / "1")
    path = [first[0]]
    for j in range(1, ctx["stage"] + 1):
        p = run_dir / "stages" / str(j)
        if (p / "executed_path.json").exists():
            path.extend(ep._world_path(p))
    return M.Row(row_id=f"{ctx['run']}:{ctx['stage']}", scene=ctx["scene"], seed=int(ctx["seed"]), arm=ctx["arm_of_run"],
                 stage=ctx["stage"], cluster=f"{ctx['scene']}_s{ctx['seed']}_{ctx['arm_of_run']}", round=0,
                 is_gemini_row=False, observed=observed, path_xy=tuple(path))


_TRUTH: Dict[str, Any] = {}
_TABLES: Dict[str, Any] = {}


def froom_resources(scene: str) -> tuple:
    """(truth of this scene, tables built from the other scene)."""
    rt, ep, M = sem()
    if scene not in _TRUTH:
        _TRUTH[scene] = rt.load_scene_truth(scene)
    other = FROOM_OTHER_SCENE[scene]
    if other not in _TRUTH:
        _TRUTH[other] = rt.load_scene_truth(other)
    if scene not in _TABLES:
        _TABLES[scene] = froom_tables(_TRUTH[other], rt.labels, M.ROOM_TYPES)
    return _TRUTH[scene], _TABLES[scene]


def build_sets(ctx: dict, arms: Sequence[str], error_samples: Dict[str, np.ndarray], wdir: str) -> Dict[str, dict]:
    """Per arm: {"files", "graphs", "info"}. One graph per id in ctx["gids"], from the observed graph of
    track id // 4. F1 is always built (F3, F0 and F-room need it). F1/F5a/F5b: copied from bench.stage
    B:272-284 (same keys [BENCH_SEED, run_idx, k, g, salt], builders and yaml writer)."""
    R = reg()
    bench, rp = R["bench"], R["rp"]
    gids, ridx, k = ctx["gids"], ctx["run_idx"], ctx["stage"]
    obs_graph, obs_paths, obs_ids = ctx["obs_graph"], ctx["obs_paths"], ctx["obs_ids"]
    os.makedirs(wdir, exist_ok=True)
    out: Dict[str, dict] = {}
    salt = {"F5a": bench.SALT["placebo_A"], "F5b": bench.SALT["placebo_B"], "F1": bench.SALT["oracle"]}
    for name in ("F1", "F5a", "F5b"):
        if name != "F1" and name not in arms:
            continue
        graphs, files, seeds, orc = [], [], {}, []
        for g in gids:
            key = [bench.BENCH_SEED, ridx, k, g, salt[name]]
            seeds[str(g)] = key
            rng = np.random.default_rng(key)
            if name == "F1":
                gr, inf = rp.lp.oracle_graph(obs_graph[g // 4], rng, bench.CALIB, ctx["refs"])
                orc.append({"gid": g, **inf})
            else:
                gr = rp.lp.placebo_graph(obs_graph[g // 4], rng, bench.CALIB)
            graphs.append(gr)
            files.append(bench.write_yaml(gr, os.path.join(wdir, f"{name}_{g}.yaml")))
        out[name] = {"graphs": graphs, "files": files, "info": {"seeds": seeds, "oracle_info": orc}}
    if "F6" in arms:
        out["F6"] = {"graphs": [obs_graph[g // 4] for g in gids], "files": [obs_paths[g // 4] for g in gids], "info": {}}
    if "F0" in arms:
        per_track, per = {}, []
        for g, g1 in zip(gids, out["F1"]["graphs"]):
            t = g // 4
            if t not in per_track:   # the track's first F1 graph: its first id in gids order
                per_track[t] = build_f0_graph(g1, obs_ids[t], ctx["refs"], ctx["un"])
        graphs, files = [], []
        for g in gids:
            gr, inf = per_track[g // 4]
            graphs.append(gr)
            files.append(bench.write_yaml(gr, os.path.join(wdir, f"F0_{g}.yaml")))
            per.append({"gid": g, **inf})
        out["F0"] = {"graphs": graphs, "files": files, "info": {"per_member": per}}
    for name in arms:
        if not name.startswith("F3-"):
            continue
        model = name[3:]
        sample = error_samples[model]
        graphs, files, per = [], [], []
        for g, g1, orc in zip(gids, out["F1"]["graphs"], out["F1"]["info"]["oracle_info"]):
            rng = np.random.default_rng(seed_key(ridx, k, g, f3_code(model)))
            gr, inf = displace_oracle_graph(g1, obs_ids[g // 4], sample, rng, move=not orc["fallback"])
            graphs.append(gr)
            files.append(bench.write_yaml(gr, os.path.join(wdir, f"{name}_{g}.yaml")))
            per.append({"gid": g, "fallback": bool(orc["fallback"]), **inf})
        out[name] = {"graphs": graphs, "files": files,
                     "info": {"per_member": per, "seed_code": f3_code(model), "n_sample": int(len(sample)),
                              "n_fallback_members": int(sum(p["fallback"] for p in per))}}
    if "F-room" in arms:
        rt, ep, M = sem()
        truth, tables = froom_resources(ctx["scene"])
        states: Dict[int, Any] = {}
        graphs, files, per = [], [], []
        for g, g1 in zip(gids, out["F1"]["graphs"]):
            t = g // 4        # unseen regions judged on the member's own track
            if t not in states:
                states[t] = rt.stage_state(truth, _stage_row_for_semantic(ctx, t))
            n1 = len(guessed(g1, obs_ids[t]))   # the count its F1 graph holds
            rng = np.random.default_rng(seed_key(ridx, k, g, ARM_CODE["F-room"]))
            gr, inf = build_froom_graph(obs_graph[t], rng, bench.CALIB, truth, states[t], tables, n1, M.ROOM_TYPES)
            graphs.append(gr)
            files.append(bench.write_yaml(gr, os.path.join(wdir, f"F-room_{g}.yaml")))
            per.append({"gid": g, **inf})
        out["F-room"] = {"graphs": graphs, "files": files,
                         "info": {"per_member": per, "seed_code": ARM_CODE["F-room"],
                                  "n_members_no_unseen_typed": int(sum(p["no_unseen_typed"] for p in per)),
                                  "tables": {T: {"n": v["n"], "n_pool": len(v["pool"]), "n_regions": v["n_regions"],
                                                 "pooled": v["pooled"]} for T, v in tables.items()}}}
    for name, s in out.items():
        s["n_obj"] = [len(guessed(gr, obs_ids[g // 4])) for g, gr in zip(gids, s["graphs"])]
    return out


def score_sets(ctx: dict, sets: Dict[str, dict], arms: Optional[Sequence[str]] = None) -> Dict[str, dict]:
    """Per arm: ig and the R1 score for the stage's candidates. Copied from bench.stage B:288-295, 311.
    Arms built only to feed others (F1 in a later pass) are not scored unless named in `arms`."""
    fastig = reg()["fastig"]
    cam1 = fastig.cu.CameraConfig()
    out = {}
    for name, s in sets.items():
        if arms is not None and name not in arms:
            continue
        t0 = time.time()
        S, _ = fastig.Scorer(s["files"], ctx["seed"]).score(ctx["kept"], cam1)
        ig = S[:, 0] + S[:, 1]
        out[name] = {"ig": ig, "score": ig - LAMBDA * ctx["d"], "secs": round(time.time() - t0, 2)}
    return out


def outcomes(ctx: dict, scored: Dict[str, dict]) -> Dict[str, dict]:
    """R1 pick and regret under U_wall and U_wall_cone, per arm."""
    return {name: {"pick": int(np.argmax(s["score"])),
                   "regret": {u: regret_r1(s["score"], ctx["yard"][u]) for u in REGRET_YARDSTICKS}}
            for name, s in scored.items()}


def run_stage(run: str, k: int, meta: dict, arms: Sequence[str], error_samples: Dict[str, np.ndarray], workdir: str) -> dict:
    t0 = time.time()
    ctx = stage_context(run, k, meta)
    row = {"run": run, "arm": ctx["arm_of_run"], "scene": ctx["scene"], "seed": ctx["seed"], "stage": k,
           "run_idx": ctx["run_idx"], "n_cand": ctx["n_cand"], "top10_match": ctx["top10_match"], "gids": ctx["gids"]}
    if "drop" in ctx:
        row["drop"] = ctx["drop"]
        return row
    wdir = os.path.join(workdir, "tmp", f"{run}_{k}")
    try:
        sets = build_sets(ctx, arms, error_samples, wdir)
        scored = score_sets(ctx, sets, arms)
        outs = outcomes(ctx, scored)
        row.update({"n_ref": ctx["n_ref"], "n_unmapped": ctx["n_unmapped"], "d": ctx["d"].tolist(),
                    "yard": {u: v.tolist() for u, v in ctx["yard"].items()},
                    "arms": {n: {"ig": scored[n]["ig"].tolist(), "score": scored[n]["score"].tolist(),
                                 "pick": outs[n]["pick"], "regret": outs[n]["regret"], "secs": scored[n]["secs"],
                                 "n_obj": sets[n]["n_obj"], "info": sets[n]["info"]} for n in scored}})
    finally:
        shutil.rmtree(wdir, ignore_errors=True)
    row["secs"] = round(time.time() - t0, 1)
    return row


# =====================================================================================
# Study driver
# =====================================================================================
def stage_list(only: Sequence[str] = ()) -> list:
    """The bench's stage list (bench.main B:366-374)."""
    R = reg()
    bench, rp = R["bench"], R["rp"]
    used = [json.loads(l) for l in open(f"{FARM}/audit/audit/stages.jsonl")]
    used = {(r["run"], r["stage"]) for r in used if r.get("top10_match") and "rho_total_U360" in r}
    jobs = []
    for run in bench.RUNS:
        meta = rp.stage_meta(run)
        jobs += [(run, k, meta[k]) for k in sorted(meta) if (run, k) in used]
    if only:
        jobs = [j for j in jobs if any(f"{j[0]}:{j[1]}" == o or (":" not in o and o in j[0]) for o in only)]
    return jobs


_CFG: Dict[str, Any] = {}


def _init(cfg):
    _CFG.update(cfg)
    _CFG["samples"] = {m: load_error_sample(p) for m, p in cfg["error_files"].items()}


def job(a):
    run, k, meta = a
    try:
        return run_stage(run, k, meta, _CFG["arms"], _CFG["samples"], _CFG["workdir"])
    except Exception as e:  # one stage's failure must not stop the study
        import traceback
        return {"run": run, "stage": k, "error": repr(e), "tb": traceback.format_exc()[-2000:]}


def check_hashed() -> str:
    """Refuse to run unless PREREGISTRATION_M2.sha256 holds the sha256 of PREREGISTRATION_M2.md."""
    if not PREREG_SHA.exists():
        raise SystemExit(f"{PREREG_SHA.name} does not exist: the M2 rules are not hashed")
    m = re.search(r"\b([0-9a-f]{64})\b", PREREG_SHA.read_text())
    actual = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    if not m or m.group(1) != actual:
        raise SystemExit(f"{PREREG_SHA.name} does not match {PREREG.name} (file {actual}); refusing to run")
    return actual


def expand_arms(spec: Sequence[str], models: Sequence[str]) -> List[str]:
    arms = []
    for a in spec:
        if a == "F5":
            arms += ["F5a", "F5b"]
        elif a == "F3":
            arms += [f"F3-{m}" for m in models]
        else:
            arms.append(a)
    return list(dict.fromkeys(arms))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="output folder (factorial_stages.jsonl, factorial_meta.json)")
    ap.add_argument("--arms", default="F1,F5,F6,F0,F-room,F3",
                    help="comma list of F1,F5,F6,F0,F-room,F3 (F3 runs for the models of --error-file)")
    ap.add_argument("--error-file", action="append", default=[], metavar="MODEL=PATH",
                    help=f"error sample per model, MODEL in {MODELS}; JSON list of distances in metres")
    ap.add_argument("--nproc", type=int, default=int(os.environ.get("NPROC", 48)))
    ap.add_argument("--only", nargs="*", default=[], help="run:stage or a run-name part")
    args = ap.parse_args(argv)
    if args.nproc > 48:
        raise SystemExit("--nproc above 48 is not allowed on the shared host")
    prereg_sha = check_hashed()
    error_files = dict(x.split("=", 1) for x in args.error_file)
    for m, p in error_files.items():
        if m not in MODELS:
            raise SystemExit(f"model {m!r} is not one of {MODELS}")
        load_error_sample(p)   # fail now, not in a worker
    spec = args.arms.split(",")
    if "F3" in spec and not error_files:
        raise SystemExit("F3 needs at least one --error-file")
    arms = expand_arms(spec, sorted(error_files))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = stage_list(args.only)
    cfg = {"arms": arms, "error_files": error_files, "workdir": str(out)}
    meta = {"prereg_sha256": prereg_sha, "arms": arms, "n_jobs": len(jobs), "argv": sys.argv,
            "error_files": {m: {"path": p, "sha256": hashlib.sha256(Path(p).read_bytes()).hexdigest(),
                                "n": int(len(load_error_sample(p)))} for m, p in error_files.items()},
            "arm_code": ARM_CODE, "master_seed": MASTER_SEED, "lambda": LAMBDA,
            "numpy": np.__version__, "python": sys.version.split()[0]}
    (out / "factorial_meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print("jobs", len(jobs), "arms", arms, flush=True)
    t0 = time.time()
    import multiprocessing as mp
    with mp.Pool(args.nproc, initializer=_init, initargs=(cfg,)) as pool, open(out / "factorial_stages.jsonl", "w") as f:
        for i, res in enumerate(pool.imap_unordered(job, jobs)):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(i + 1, res["run"], res["stage"], res.get("error") or res.get("drop") or res.get("secs"),
                  round(time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
