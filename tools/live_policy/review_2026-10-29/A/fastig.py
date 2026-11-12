#!/usr/bin/env python3
"""Vectorized re-implementation of the pinned first- and second-stage IG.

Uses the pinned module for everything except the per-camera visibility loop:
  - groups and perturbations: pinned _build_scene_graph_groups (seed SEED+k);
  - object -> room mapping: pinned _get_object_to_parent_mapping;
  - targets/occluders: pinned _preprocess_groups;
  - entropies: same dict-order arithmetic as _calculate_ig_components.
The visibility test (frustum + ray/OBB occlusion) is vectorized over cameras.
check_against_pinned() compares IG values with the pinned loop.
"""
import sys

sys.path.insert(0, "/tmp/cvp_review/work_A")
import math  # noqa: E402

import numpy as np  # noqa: E402

np.set_printoptions(legacy="1.25")
import pinned_harness as ph  # noqa: E402

cu = ph.cu
PITCH = -np.pi / 18


def cam_frames(poses):
    """Rotation rows (N,3,3) and translations (N,3) exactly as Camera._build_view_matrix."""
    poses = np.asarray(poses, dtype=float)
    yaw = np.radians(poses[:, 3])
    z = np.stack([np.cos(yaw) * np.cos(PITCH), np.sin(yaw) * np.cos(PITCH),
                  np.full_like(yaw, np.sin(PITCH))], axis=1)
    z = z / np.linalg.norm(z, axis=1, keepdims=True)
    up = np.array([0.0, 0.0, 1.0])
    x = np.cross(z, up)
    x = x / np.linalg.norm(x, axis=1, keepdims=True)
    y = np.cross(z, x)
    y = y / np.linalg.norm(y, axis=1, keepdims=True)
    R = np.stack([x, y, z], axis=1)  # rows
    pos = poses[:, :3]
    t = -np.einsum("nij,nj->ni", R, pos)
    return R, t, pos


def frustum_normals(cfg):
    sf = cfg.fx / cfg.fy
    p_tl = np.array([-cfg.cx, -cfg.cy * sf, cfg.fx])
    p_tr = np.array([cfg.width - cfg.cx, -cfg.cy * sf, cfg.fx])
    p_br = np.array([cfg.width - cfg.cx, (cfg.height - cfg.cy) * sf, cfg.fx])
    p_bl = np.array([-cfg.cx, (cfg.height - cfg.cy) * sf, cfg.fx])
    n = np.zeros((4, 3))
    n[0] = np.cross(p_tr, p_tl)
    n[1] = np.cross(p_br, p_tr)
    n[2] = np.cross(p_bl, p_br)
    n[3] = np.cross(p_tl, p_bl)
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def corners(dims, pos, orient):
    h = dims / 2.0
    loc = np.array([[-h[0], -h[1], -h[2]], [h[0], -h[1], -h[2]], [h[0], h[1], -h[2]], [-h[0], h[1], -h[2]],
                    [-h[0], -h[1], h[2]], [h[0], -h[1], h[2]], [h[0], h[1], h[2]], [-h[0], h[1], h[2]]])
    return (orient @ loc.T).T + pos


class GraphGeom:
    def __init__(self, opt_sg):
        tg = opt_sg["targets"]
        oc = opt_sg["occluders"]
        self.ids = [t["id"] for t in tg]
        self.names = [t["name"] for t in tg]
        self.T = len(tg)
        if self.T:
            self.pts = np.stack([np.vstack((t["pos"].reshape(1, 3), corners(t["dims"], t["pos"], t["orient"])))
                                 for t in tg])  # (T,9,3)
            self.tpos = np.stack([t["pos"] for t in tg])
        self.O = len(oc)
        if self.O:
            self.oc_c = np.stack([o["pos"] for o in oc])
            self.oc_h = np.stack([o["dims"] / 2.0 for o in oc])
            self.oc_RT = np.stack([o["orient"].T for o in oc])


def visible(geom, R, t, cpos, cfg, normals):
    """(N,T) bool: target visible (in frustum and not occluded), plus (N,T) bool for dist<1e-6 ids."""
    N = R.shape[0]
    if geom.T == 0:
        return np.zeros((N, 0), bool), np.zeros((N, 0), bool)
    P = geom.pts  # (T,9,3)
    pc = np.einsum("nij,tkj->ntki", R, P) + t[:, None, None, :]  # (N,T,9,3)
    zv = pc[..., 2]
    valid = (zv > cfg.near_clip) & (np.linalg.norm(pc, axis=-1) < cfg.max_range)
    dots = np.einsum("fi,ntki->ntkf", normals, pc)
    inside = np.all(dots <= 0, axis=-1)
    infr = np.any(valid & inside, axis=-1)  # (N,T)
    diff = geom.tpos[None, :, :] - cpos[:, None, :]
    dist = np.linalg.norm(diff, axis=-1)  # (N,T)
    zero = infr & (dist < 1e-6)
    cand = infr & ~zero
    vis = cand.copy()
    if geom.O and cand.any():
        nn, tt = np.nonzero(cand)
        d = dist[nn, tt]
        rd = diff[nn, tt] / d[:, None]  # (M,3)
        org = cpos[nn]  # (M,3)
        # local frames: (M,O,3)
        ol = np.einsum("oij,moj->moi", geom.oc_RT, org[:, None, :] - geom.oc_c[None, :, :])
        dl = np.einsum("oij,mj->moi", geom.oc_RT, rd)
        h = geom.oc_h[None, :, :]
        par = np.abs(dl) < 1e-6
        with np.errstate(divide="ignore", invalid="ignore"):
            t1 = (-h - ol) / dl
            t2 = (h - ol) / dl
        lo = np.minimum(t1, t2)
        hi = np.maximum(t1, t2)
        lo = np.where(par, -np.inf, lo)
        hi = np.where(par, np.inf, hi)
        out_par = np.any(par & ((ol < -h) | (ol > h)), axis=-1)
        tmin = np.maximum(0.0, np.max(lo, axis=-1))
        tmax = np.min(hi, axis=-1)
        hit = (~out_par) & (tmin <= tmax) & (tmax >= 0)
        occl = np.any(hit & (tmin < d[:, None]), axis=-1)
        vis[nn[occl], tt[occl]] = False
    return vis, zero


class Scorer:
    """Score poses for a fixed set of hypothesis files."""

    def __init__(self, files, seed):
        calc = ph.make_calc(seed, 0, "/tmp/cvp_review/work_A/tmp")
        groups = calc._build_scene_graph_groups(files)
        self.groups = groups
        self.mapping = calc._get_object_to_parent_mapping(files)
        self.opt = calc._preprocess_groups(groups)
        self.geoms = [[GraphGeom(sg) for sg in og] for og in self.opt]
        self.lo, self.hi = calc._get_sampling_bounds(groups)
        self.first_targets = [t["pos"] for t in self.opt[0][0]["targets"]]

    def observations(self, poses, cfg):
        """Per pose: list over groups of (name_obs list, room_obs list), plus any_visible flags."""
        R, t, cpos = cam_frames(poses)
        normals = frustum_normals(cfg)
        N = len(poses)
        name_obs = [[[] for _ in self.geoms] for _ in range(N)]
        room_obs = [[[] for _ in self.geoms] for _ in range(N)]
        anyv = np.zeros(N, bool)
        for gi, gg in enumerate(self.geoms):
            mp = self.mapping[gi]
            for geom in gg:
                vis, zero = visible(geom, R, t, cpos, cfg, normals)
                for n in range(N):
                    idx = np.nonzero(vis[n])[0] if geom.T else []
                    zidx = np.nonzero(zero[n])[0] if geom.T else []
                    counts = {}
                    for i in idx:
                        nm = geom.names[i]
                        counts[nm] = counts.get(nm, 0) + 1
                    if counts:
                        anyv[n] = True
                    # ids in node order: visible or zero-distance
                    all_idx = sorted(set(idx.tolist() if len(idx) else []) | set(zidx.tolist() if len(zidx) else []))
                    room = set()
                    if all_idx:
                        pn = [mp[geom.ids[i]] for i in all_idx if geom.ids[i] in mp]
                        if pn:
                            best, bc = None, -1
                            cnt = {}
                            for p in pn:
                                cnt[p] = cnt.get(p, 0) + 1
                            for p, c in cnt.items():  # insertion order = first occurrence
                                if c > bc:
                                    best, bc = p, c
                            room = {best}
                    name_obs[n][gi].append(counts)
                    room_obs[n][gi].append(room)
        return name_obs, room_obs, anyv

    @staticmethod
    def _ig(per_group):
        total = {}
        ents = []
        for lst in per_group:
            gc = {}
            for item in lst:
                obs = frozenset(item.items() if isinstance(item, dict) else item)
                gc[obs] = gc.get(obs, 0) + 1
                total[obs] = total.get(obs, 0) + 1
            gt = sum(gc.values())
            ents.append(-sum((c / gt) * math.log2(c / gt) for c in gc.values()) if gt > 0 else 0.0)
        hye = float(sum(ents) / max(len(ents), 1))
        tot = sum(total.values())
        hy = -sum((c / tot) * math.log2(c / tot) for c in total.values()) if tot > 0 else 0.0
        return hy - hye

    def score(self, poses, cfg):
        """(N,2) array of (obj_ig, room_ig)."""
        if len(poses) == 0:
            return np.zeros((0, 2)), np.zeros(0, bool)
        no, ro, anyv = self.observations(poses, cfg)
        out = np.array([[self._ig(no[n]), self._ig(ro[n])] for n in range(len(poses))], dtype=float)
        return out, anyv

    def first_stage(self, seed, nprior, cur, lam=0.2, samples=300, chunk=600):
        rng = np.random.default_rng(seed)
        for _ in range(nprior):
            rng.uniform(low=np.zeros(4), high=np.ones(4), size=(samples * 10, 4))
        lo = np.append(self.lo, 0.0)
        hi = np.append(self.hi, 360.0)
        cands = rng.uniform(low=lo, high=hi, size=(samples * 10, 4))
        obj = np.array(self.first_targets) if self.first_targets else np.empty((0, 3))
        if len(obj):
            d2 = np.sum((cands[:, None, :3] - obj[None, :, :]) ** 2, axis=2)
            prom = cands[np.min(d2, axis=1) < (3.0 + 0.5) ** 2]
        else:
            prom = cands
        cfg = cu.CameraConfig()
        kept, scores = [], []
        for s in range(0, len(prom), chunk):
            block = prom[s:s + chunk]
            sc, anyv = self.score(block, cfg)
            for i in range(len(block)):
                if len(kept) >= samples:
                    break
                if anyv[i]:
                    kept.append(block[i])
                    scores.append(sc[i])
            if len(kept) >= samples:
                break
        kept = np.array(kept)
        scores = np.array(scores)
        if len(kept) == 0:
            return kept, scores, np.zeros(0), []
        dist = np.linalg.norm(kept[:, :3] - np.asarray(cur[:3], float), axis=1)
        total = scores[:, 0] + scores[:, 1] - lam * dist
        order = sorted(range(len(total)), key=lambda i: total[i], reverse=True)
        return kept, scores, total, order


def second_cfg():
    import copy
    c = copy.deepcopy(cu.CameraConfig())
    c.near_clip = 0.1
    c.max_range = 4.0
    return c
