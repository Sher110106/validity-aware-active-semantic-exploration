"""Offline replay of ASP's first viewpoint decision ($0; no pipeline, no host).

Uses the pinned calculate_uncertainty.py for perturbation, grouping, room mapping
and entropy, and a vectorised copy of its visibility test (checked against the
pinned _visible_testing in validate()). Reachability (nvblox/A*) cannot be
replayed offline, so the "final" pick assumes every top-10 candidate is reachable
at its own pose and re-scores it with calculate_specific_pose_ig's camera
(near 0.1 m, range 4 m, no move cost), as exploration_pipeline.py:779-833 does
for reachable candidates.
"""
import importlib.util, os, sys, copy, json, math, types, glob
from collections import Counter
import numpy as np
np.set_printoptions(legacy="1.25")  # host numpy<2: str(list(arr)) must give plain floats for the pinned perturbation code
import yaml

PINNED = "/tmp/cvp_review/pipeline_pinned_copy/scripts/calculate_uncertainty.py"
spec = importlib.util.spec_from_file_location("cu_pinned", PINNED)
cu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cu)

SCRATCH = "/tmp/cvp_review/work_B/scratch"
os.makedirs(SCRATCH, exist_ok=True)


def make_config(seed):
    return types.SimpleNamespace(
        SEED=seed, UNCERTAINTY_PERTURBATIONS=3, UNCERTAINTY_NOISE_LOW=-0.25, UNCERTAINTY_NOISE_HIGH=0.25,
        UNCERTAINTY_SAMPLES=300, CAMERA_CONFIG=cu.CameraConfig(), AGENT_HEIGHT=1.1,
        UNCERTAINTY_ROOM_WEIGHT=1.0, MOVE_COST_LAMBDA=0.2, MINIMUM_DISTANCE_DIFFERENCE=1.0,
        WORKING_DIRECTORY=SCRATCH)


def _ray_hits(cam, dirs, dists, occ):
    """Vectorised _ray_intersects_obb for rays (n,3) against occluders; returns (n,) occluded."""
    if len(occ) == 0 or len(dirs) == 0:
        return np.zeros(len(dirs), dtype=bool)
    occluded = np.zeros(len(dirs), dtype=bool)
    for o in occ:
        inv = o['orient'].T
        ol = inv @ (cam - o['pos'])               # (3,)
        dl = dirs @ inv.T                          # (n,3)
        half = o['dims'] / 2.0
        tmin = np.zeros(len(dirs)); tmax = np.full(len(dirs), np.inf); miss = np.zeros(len(dirs), dtype=bool)
        for i in range(3):
            par = np.abs(dl[:, i]) < 1e-6
            outside = (ol[i] < -half[i]) | (ol[i] > half[i])
            miss |= par & outside
            with np.errstate(divide='ignore', invalid='ignore'):
                t1 = (-half[i] - ol[i]) / dl[:, i]
                t2 = (half[i] - ol[i]) / dl[:, i]
            lo = np.where(par, -np.inf, np.minimum(t1, t2))
            hi = np.where(par, np.inf, np.maximum(t1, t2))
            tmin = np.maximum(tmin, lo); tmax = np.minimum(tmax, hi)
        hit = (~miss) & (tmin <= tmax) & (tmax >= 0)
        occluded |= hit & (np.maximum(0.0, tmin) < dists)
    return occluded


class Graph:
    """One (possibly perturbed) scene graph prepared for fast visibility."""
    def __init__(self, opt_sg):
        t = opt_sg['targets']
        self.ids = [x['id'] for x in t]
        self.names = [x['name'] for x in t]
        self.pos = np.array([x['pos'] for x in t]).reshape(-1, 3)
        if len(t):
            corners = []
            for x in t:
                half = x['dims'] / 2.0
                cl = np.array([[sx * half[0], sy * half[1], sz * half[2]] for sz in (-1, 1) for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
                corners.append(np.vstack([x['pos'][None, :], (x['orient'] @ cl.T).T + x['pos']]))
            self.pts = np.array(corners)  # (n,9,3)
        else:
            self.pts = np.zeros((0, 9, 3))
        self.occ = opt_sg['occluders']


def visible(g, camera):
    """Vectorised _visible_testing: returns (visible ids in target order, name->count dict)."""
    if len(g.ids) == 0:
        return [], {}
    V = camera.view_matrix
    pc = g.pts @ V[:3, :3].T + V[:3, 3]           # (n,9,3)
    cfg = camera.config
    valid = (pc[..., 2] > cfg.near_clip) & (np.linalg.norm(pc, axis=2) < cfg.max_range)
    dots = pc @ camera.frustum_normals.T           # (n,9,4)
    inside = np.all(dots <= 0, axis=2)
    inview = np.any(valid & inside, axis=1)
    idx = np.nonzero(inview)[0]
    if len(idx) == 0:
        return [], {}
    vec = g.pos[idx] - camera.position
    dist = np.linalg.norm(vec, axis=1)
    tiny = dist < 1e-6
    dirs = vec / np.where(tiny, 1.0, dist)[:, None]
    occl = _ray_hits(camera.position, dirs, dist, g.occ)
    ids, counts = [], {}
    for j, ii in enumerate(idx):
        if tiny[j]:
            ids.append(g.ids[ii]); continue
        if not occl[j]:
            ids.append(g.ids[ii]); counts[g.names[ii]] = counts.get(g.names[ii], 0) + 1
    return ids, counts


class Scorer:
    def __init__(self, files, seed):
        self.cfg = make_config(seed)
        self.uc = cu.UncertaintyCalculator(self.cfg)
        groups = self.uc._build_scene_graph_groups(files)
        self.mapping = self.uc._get_object_to_parent_mapping(files)
        self.opt = self.uc._preprocess_groups(groups)
        self.uc.optimized_groups = self.opt
        self.uc.mapping = self.mapping
        self.G = [[Graph(sg) for sg in grp] for grp in self.opt]
        self.bounds = self.uc._get_sampling_bounds(groups)

    def observe(self, pose, near=None, rng_=None):
        cam_cfg = self.cfg.CAMERA_CONFIG
        if near is not None:
            cam_cfg = copy.deepcopy(cam_cfg); cam_cfg.near_clip = near; cam_cfg.max_range = rng_
        cam = cu.Camera(config=cam_cfg, position=np.asarray(pose[:3], float), yaw_degrees=float(pose[3]))
        obs, anyv = [], False
        for i, grp in enumerate(self.G):
            names_list, rooms_list = [], []
            for g in grp:
                ids, counts = visible(g, cam)
                if counts:
                    anyv = True
                room = set()
                if ids:
                    parents = [self.mapping[i][o] for o in ids if o in self.mapping[i]]
                    if parents:
                        room = {Counter(parents).most_common(1)[0][0]}
                names_list.append(counts); rooms_list.append(room)
            obs.append({'sample': np.asarray(pose), 'names_list': names_list, 'rooms_list': rooms_list})
        return obs, anyv

    def ig(self, obs):
        o = self.uc._calculate_ig_components(obs, lambda x: x['names_list'])
        r = self.uc._calculate_ig_components(obs, lambda x: x['rooms_list'])
        return o['H_y'] - o['H_y_epsilon'], r['H_y'] - r['H_y_epsilon']

    def candidates(self, U):
        """U: (3000,4) standard uniforms. Same mapping as Generator.uniform(low, high)."""
        lo = np.append(self.bounds[0], 0.0); hi = np.append(self.bounds[1], 360.0)
        cand = lo + (hi - lo) * U
        objs = np.array([t['pos'] for t in self.opt[0][0]['targets']]).reshape(-1, 3)
        if len(objs):
            d2 = ((cand[:, None, :3] - objs[None, :, :]) ** 2).sum(-1).min(1)
            cand = cand[d2 < (self.cfg.CAMERA_CONFIG.max_range + 0.5) ** 2]
        return cand

    def decide(self, U, current, history, tie_rng=None):
        kept = []
        for s in self.candidates(U):
            if len(kept) >= self.cfg.UNCERTAINTY_SAMPLES:
                break
            obs, anyv = self.observe(s)
            if anyv:
                oi, ri = self.ig(obs)
                kept.append((oi + ri - self.cfg.MOVE_COST_LAMBDA * np.linalg.norm(s[:3] - current[:3]), s, oi, ri))
        kept.sort(key=lambda x: x[0], reverse=True)
        top = kept[:10]
        filt = [t for t in top if all(np.linalg.norm(t[1][:3] - h) > 1.0 for h in history)] or top
        best, bl = -np.inf, []
        for t in filt:
            obs, _ = self.observe(t[1], near=0.1, rng_=4.0)
            oi, ri = self.ig(obs)
            f = oi + ri
            if f - best > 1e-6:
                best, bl = f, [t[1]]
            elif abs(f - best) <= 1e-6:
                bl.append(t[1])
        choice = bl[0] if tie_rng is None else bl[int(tie_rng.integers(len(bl)))]
        return dict(kept=kept, top=top, filt=filt, final_ig=best, ties=len(bl), choice=choice,
                    best_first=top[0][0] if top else None)


def validate(files, seed, n=40):
    """Compare vectorised visibility with the pinned _visible_testing on random poses."""
    S = Scorer(files, seed)
    rng = np.random.default_rng(123)
    lo, hi = np.append(S.bounds[0], 0.0), np.append(S.bounds[1], 360.0)
    bad = 0
    for _ in range(n):
        p = lo + (hi - lo) * rng.random(4)
        cam = cu.Camera(config=S.cfg.CAMERA_CONFIG, position=p[:3], yaw_degrees=float(p[3]))
        for i, grp in enumerate(S.opt):
            for j, sg in enumerate(grp):
                ids0, _, _, c0 = S.uc._visible_testing(sg, cam)
                ids1, c1 = visible(S.G[i][j], cam)
                if ids0 != ids1 or c0 != c1:
                    bad += 1
    return bad
