"""Region footprints for one HM3D scene, from the semantic mesh.

Runs inside the asp-noetic container (Python 3.9, numpy, PIL, scipy). No GPU, no habitat.

Usage (cwd = /workspace/runs/endsem_semantic):
    python extract_region_footprints.py <scene>        # 00853 or 00871

Method
  1. Read <scene>.semantic.txt (id, hex colour, "name", region) and the semantic glb.
  2. Give every triangle to an object by the semantic texture colour at its UV centroid
     (same rule and same vertex-texel fallback as extract_semantic_aabb.py).
  3. Move vertices asset -> habitat -> pipeline ("world") frame.
       asset -> habitat : (x, y, z) -> (x, z, -y)
       habitat -> world : code_transform(pipeline_initial_agent_state) from <scene>_raw_objects.json
  4. Rasterise onto a 0.05 m grid in the world x,y plane. World z is vertical.
  5. For every region: `floor` mask (objects named exactly "floor", any case) and `any` mask (all objects).

Outputs: <scene>_region_footprints.npz, <scene>_regions.json
Mask layout: mask[region_index, iy, ix]; cell (ix, iy) covers
    x in [origin_x + ix*cell, origin_x + (ix+1)*cell), y likewise.
"""
import sys
import os
import io
import csv
import json
import math
import struct
import hashlib
import collections

import numpy as np
from PIL import Image
from scipy import ndimage

HM3D = "/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d"
SCENES = {
    "00853": "val/00853-5cdEh9F2hJL/5cdEh9F2hJL",
    "00871": "val/00871-VBzV5z6i1WS/VBzV5z6i1WS",
}
REFS = "/workspace/runs/live_campaign/hm3d_refs_work"  # read only
CELL = 0.05
NEAR = 0.5            # check (b): within this distance of the mask counts as inside
PAD = 0.5             # grid margin around all geometry, m
A2H = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=float)  # asset -> habitat


# ---------------------------------------------------------------- frames (from frame_transform.py)
def Rx(a):
    return np.array([[1, 0, 0, 0], [0, np.cos(a), -np.sin(a), 0], [0, np.sin(a), np.cos(a), 0], [0, 0, 0, 1]])


def Rz(a):
    return np.array([[np.cos(a), -np.sin(a), 0, 0], [np.sin(a), np.cos(a), 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])


def quat_to_R(w, x, y, z):
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def code_transform(init):
    """4x4 habitat -> pipeline world. T = M_init @ Rx(-pi/2) @ Rz(pi/4); world = T^-1 habitat."""
    M = np.eye(4)
    M[:3, :3] = quat_to_R(*init["rotation_wxyz"])
    M[:3, 3] = [init["position"][0], 0.0, init["position"][2]]
    T = M @ Rx(-np.pi / 2) @ Rz(np.pi / 4)
    return np.linalg.inv(T)


# ---------------------------------------------------------------- glb parsing (from extract_semantic_aabb.py)
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    blob = open(path, "rb").read()
    struct.unpack("<4sII", blob[:12])
    off = 12
    J = BIN = None
    while off < len(blob):
        clen, ctype = struct.unpack("<I4s", blob[off:off + 8])
        data = blob[off + 8: off + 8 + clen]
        off += 8 + clen
        if ctype == b"JSON":
            J = json.loads(data)
        elif ctype == b"BIN\x00":
            BIN = data
    return J, BIN


def accessor(J, BIN, i):
    a = J["accessors"][i]
    bv = J["bufferViews"][a["bufferView"]]
    dt = np.dtype(CT[a["componentType"]])
    n = NC[a["type"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", 0) or dt.itemsize * n
    if stride == dt.itemsize * n:
        return np.frombuffer(BIN, dtype=dt, count=a["count"] * n, offset=start).reshape(a["count"], n)
    raw = np.frombuffer(BIN, dtype=np.uint8, count=stride * a["count"], offset=start).reshape(a["count"], stride)
    return raw[:, : dt.itemsize * n].copy().view(dt).reshape(a["count"], n)


def node_matrix(nd):
    if "matrix" in nd:
        return np.array(nd["matrix"], dtype=float).reshape(4, 4).T
    M = np.eye(4)
    t = nd.get("translation", [0, 0, 0])
    q = nd.get("rotation", [0, 0, 0, 1])
    s = nd.get("scale", [1, 1, 1])
    x, y, z, w = q
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M[:3, :3] = R * np.array(s)[None, :]
    M[:3, 3] = t
    return M


def read_semantic_txt(path):
    objects = {}
    with open(path) as f:
        f.readline()
        for row in csv.reader(f):
            oid, hexc, name, region = int(row[0]), row[1].strip(), row[2], int(row[3])
            rgb = (int(hexc[0:2], 16), int(hexc[2:4], 16), int(hexc[4:6], 16))
            objects[oid] = dict(rgb=rgb, name=name, region=region)
    return objects


def triangles_by_object(base, objects, Tc):
    """Returns tri_w (N,3,3) world-frame float64, tri_oid (N,) int64 (-1 = unmatched), stats."""
    color2id = collections.defaultdict(list)
    for oid, o in objects.items():
        color2id[(o["rgb"][0] << 16) | (o["rgb"][1] << 8) | o["rgb"][2]].append(oid)
    dup = sum(1 for v in color2id.values() if len(v) > 1)
    keys = np.array(sorted(color2id.keys()), dtype=np.int64)
    kid = np.array([color2id[int(k)][0] for k in keys], dtype=np.int64)

    def lookup(key):
        pos = np.clip(np.searchsorted(keys, key), 0, len(keys) - 1)
        ok = keys[pos] == key
        return ok, np.where(ok, kid[pos], -1)

    J, BIN = read_glb(base + ".semantic.glb")
    Rw, tw = Tc[:3, :3], Tc[:3, 3]
    tex_cache = {}

    def texture(mat):
        if mat not in tex_cache:
            ti = J["materials"][mat]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
            img = J["images"][J["textures"][ti]["source"]]
            bv = J["bufferViews"][img["bufferView"]]
            b0 = bv.get("byteOffset", 0)
            im = Image.open(io.BytesIO(BIN[b0: b0 + bv["byteLength"]])).convert("RGB")
            tex_cache[mat] = np.asarray(im)
        return tex_cache[mat]

    all_tri, all_oid = [], []
    recovered = 0
    for nd in J["nodes"]:
        if "mesh" not in nd:
            continue
        M = node_matrix(nd)
        for prim in J["meshes"][nd["mesh"]]["primitives"]:
            P = accessor(J, BIN, prim["attributes"]["POSITION"]).astype(np.float64)
            P = P @ M[:3, :3].T + M[:3, 3]
            UV = accessor(J, BIN, prim["attributes"]["TEXCOORD_0"]).astype(np.float64)
            idx = accessor(J, BIN, prim["indices"]).reshape(-1, 3).astype(np.int64)
            tex = texture(prim["material"])
            H, W = tex.shape[:2]
            uvc = UV[idx].mean(axis=1)
            px = np.clip(np.floor((uvc[:, 0] % 1.0) * W).astype(int), 0, W - 1)
            py = np.clip(np.floor((uvc[:, 1] % 1.0) * H).astype(int), 0, H - 1)
            col = tex[py, px].astype(np.int64)
            key = (col[:, 0] << 16) | (col[:, 1] << 8) | col[:, 2]
            known, oid = lookup(key)
            if (~known).any():
                bad = np.where(~known)[0]
                for corner in range(3):
                    uvv = UV[idx[bad, corner]]
                    qx = np.clip(np.floor((uvv[:, 0] % 1.0) * W).astype(int), 0, W - 1)
                    qy = np.clip(np.floor((uvv[:, 1] % 1.0) * H).astype(int), 0, H - 1)
                    c2 = tex[qy, qx].astype(np.int64)
                    k2 = (c2[:, 0] << 16) | (c2[:, 1] << 8) | c2[:, 2]
                    ok2, o2 = lookup(k2)
                    ok2 = ok2 & ~known[bad]
                    oid[bad[ok2]] = o2[ok2]
                    known[bad[ok2]] = True
                    recovered += int(ok2.sum())
            PW = (P @ A2H.T) @ Rw.T + tw
            all_tri.append(PW[idx])
            all_oid.append(oid)
    tri_w = np.concatenate(all_tri)
    tri_oid = np.concatenate(all_oid)
    stats = dict(total_tri=int(len(tri_oid)), unmatched_tri=int((tri_oid < 0).sum()),
                 recovered_by_vertex_texel=recovered, duplicate_colour_groups=dup)
    return tri_w, tri_oid, stats


# ---------------------------------------------------------------- rasterising
def rasterise(tris, x0, y0, nx, ny, cell=CELL):
    """tris (n,3,3) world. Marks cells of the 3 vertices, the centroid and extra interior samples."""
    m = np.zeros((ny, nx), dtype=bool)
    if len(tris) == 0:
        return m

    def mark(pts):
        ix = np.floor((pts[:, 0] - x0) / cell).astype(np.int64)
        iy = np.floor((pts[:, 1] - y0) / cell).astype(np.int64)
        ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
        m[iy[ok], ix[ok]] = True

    mark(tris.reshape(-1, 3))
    mark(tris.mean(axis=1))
    e = np.stack([np.linalg.norm(tris[:, 1] - tris[:, 0], axis=1),
                  np.linalg.norm(tris[:, 2] - tris[:, 1], axis=1),
                  np.linalg.norm(tris[:, 0] - tris[:, 2], axis=1)], axis=1).max(axis=1)
    big = np.where(e > cell)[0]
    if len(big):
        k_all = np.ceil(e[big] / (cell * 0.5)).astype(np.int64)  # lattice spacing <= cell/2
        for k in np.unique(k_all):
            sel = big[k_all == k]
            ii, jj = np.meshgrid(np.arange(k + 1), np.arange(k + 1), indexing="ij")
            keep = (ii + jj) <= k
            a = ii[keep] / float(k)
            b = jj[keep] / float(k)
            w = np.stack([1 - a - b, a, b], axis=1)            # (L,3)
            chunk = max(1, int(4_000_000 // len(w)))
            for s0 in range(0, len(sel), chunk):
                t = tris[sel[s0:s0 + chunk]]                    # (c,3,3)
                mark(np.einsum("lk,ckd->cld", w, t).reshape(-1, 3))
    return m


def fill_pinholes(m):
    """Set a cell when it is empty and all four edge neighbours are set. One pass."""
    p = np.pad(m, 1)
    add = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:] & ~m
    return m | add, int(add.sum())


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    scene = sys.argv[1]
    base = f"{HM3D}/{SCENES[scene]}"
    raw = json.load(open(f"{REFS}/{scene}_raw_objects.json"))
    ref_geo = json.load(open(f"{REFS}/{scene}_semantic_geometry.json"))["objects"]
    Tc = code_transform(raw["pipeline_initial_agent_state"])
    np.set_printoptions(precision=6, suppress=True)
    print(f"== scene {scene}")
    print("asset -> habitat  (x,y,z) -> (x,z,-y); matrix:\n", A2H)
    print("initial agent state:", raw["pipeline_initial_agent_state"])
    print("habitat -> world R (4x4 top-left):\n", Tc[:3, :3])
    print("habitat -> world t:", Tc[:3, 3])
    print("world z = habitat y? row 3 of R =", Tc[2, :3], " (so world z is the vertical axis)")

    objects = read_semantic_txt(base + ".semantic.txt")
    print("objects in semantic.txt:", len(objects))
    tri_w, tri_oid, st = triangles_by_object(base, objects, Tc)
    print("triangle stats:", st)

    # ---- per-object extraction and cross-check with the reference extraction
    known = tri_oid >= 0
    obj_min, obj_max, obj_ntri = {}, {}, collections.Counter()
    order = np.argsort(tri_oid[known], kind="stable")
    t_k = tri_w[known][order]
    o_k = tri_oid[known][order]
    cut = np.flatnonzero(np.diff(o_k)) + 1
    for chunk_t, chunk_o in zip(np.split(t_k, cut), np.split(o_k, cut)):
        oid = int(chunk_o[0])
        v = chunk_t.reshape(-1, 3)
        obj_min[oid], obj_max[oid] = v.min(0), v.max(0)
        obj_ntri[oid] = len(chunk_t)
    diffs, ntri_mismatch = [], 0
    for sid, g in ref_geo.items():
        oid = int(sid)
        if g["n_tri"] == 0:
            continue
        if obj_ntri.get(oid, 0) != g["n_tri"]:
            ntri_mismatch += 1
            continue
        diffs.append(max(np.abs(obj_min[oid] - np.array(g["world_min"])).max(),
                         np.abs(obj_max[oid] - np.array(g["world_max"])).max()))
    print(f"cross-check vs {scene}_semantic_geometry.json: objects compared {len(diffs)}, "
          f"triangle-count mismatches {ntri_mismatch}, max world-AABB difference {max(diffs):.2e} m")

    # ---- grid
    allxy = tri_w[known].reshape(-1, 3)
    x0 = math.floor((allxy[:, 0].min() - PAD) / CELL) * CELL
    y0 = math.floor((allxy[:, 1].min() - PAD) / CELL) * CELL
    nx = int(math.ceil((allxy[:, 0].max() + PAD - x0) / CELL))
    ny = int(math.ceil((allxy[:, 1].max() + PAD - y0) / CELL))
    print(f"grid: origin (x0,y0)=({x0:.2f},{y0:.2f}) cell={CELL} size nx={nx} ny={ny}")

    # ---- axis evidence
    names = np.array([objects[int(o)]["name"].lower() if o >= 0 else "" for o in tri_oid])
    fl_sel = known & (names == "floor")
    ce_sel = known & (names == "ceiling")
    zf = tri_w[fl_sel][:, :, 2].mean(1)
    zc = tri_w[ce_sel][:, :, 2].mean(1) if ce_sel.any() else np.array([np.nan])
    print(f"axis check: floor triangles world z median {np.median(zf):.2f} (p5 {np.percentile(zf,5):.2f}, "
          f"p95 {np.percentile(zf,95):.2f}); ceiling triangles z median {np.nanmedian(zc):.2f}. "
          f"Floor x span {tri_w[fl_sel][:,:,0].min():.1f}..{tri_w[fl_sel][:,:,0].max():.1f}, "
          f"y span {tri_w[fl_sel][:,:,1].min():.1f}..{tri_w[fl_sel][:,:,1].max():.1f}, "
          f"z span {zf.min():.2f}..{zf.max():.2f}.  Horizontal = (x, y); vertical = z.")

    # ---- masks per region
    region_ids = sorted(set(o["region"] for o in objects.values()))
    R = len(region_ids)
    floor_m = np.zeros((R, ny, nx), dtype=bool)
    any_m = np.zeros((R, ny, nx), dtype=bool)
    reg_info = {}
    oid2reg = np.full(max(objects) + 2, -999, dtype=np.int64)
    for oid, o in objects.items():
        oid2reg[oid] = o["region"]
    tri_reg = np.where(known, oid2reg[np.where(known, tri_oid, 0)], -999)
    for ri, rid in enumerate(region_ids):
        in_r = tri_reg == rid
        fl_r = in_r & fl_sel
        any_m[ri], n_any_fill = fill_pinholes(rasterise(tri_w[in_r], x0, y0, nx, ny))
        floor_m[ri], n_fl_fill = fill_pinholes(rasterise(tri_w[fl_r], x0, y0, nx, ny))
        reg_info[rid] = dict(n_floor_tri=int(fl_r.sum()), n_any_tri=int(in_r.sum()),
                             pinholes_filled_floor=n_fl_fill, pinholes_filled_any=n_any_fill)

    cell_area = CELL * CELL
    cnt = collections.defaultdict(collections.Counter)
    names_by_region = collections.defaultdict(collections.Counter)
    objs_by_region = collections.Counter()
    floor_objs = collections.Counter()
    for oid, o in objects.items():
        names_by_region[o["region"]][o["name"]] += 1
        objs_by_region[o["region"]] += 1
        if o["name"].lower() == "floor":
            floor_objs[o["region"]] += 1

    def centroid(mask):
        iy, ix = np.nonzero(mask)
        return [round(float(x0 + (ix.mean() + 0.5) * CELL), 3), round(float(y0 + (iy.mean() + 0.5) * CELL), 3)]

    regions_out = []
    for ri, rid in enumerate(region_ids):
        fm, am = floor_m[ri], any_m[ri]
        in_r = tri_reg == rid
        fl_r = in_r & fl_sel
        has_floor = bool(fm.any())
        zr = tri_w[in_r][:, :, 2] if in_r.any() else None
        entry = dict(
            region_id=rid,
            unassigned=(rid < 0),
            n_objects=int(objs_by_region[rid]),
            n_objects_with_geometry=int(sum(1 for oid, o in objects.items() if o["region"] == rid and obj_ntri.get(oid, 0) > 0)),
            n_floor_objects=int(floor_objs[rid]),
            categories=dict(sorted(names_by_region[rid].items(), key=lambda kv: (-kv[1], kv[0]))),
            floor_area_m2=round(float(fm.sum()) * cell_area, 3),
            any_area_m2=round(float(am.sum()) * cell_area, 3),
            has_floor_triangles=bool(fl_r.any()),
            n_floor_triangles=int(fl_r.sum()),
            floor_z_range=[round(float(tri_w[fl_r][:, :, 2].min()), 3), round(float(tri_w[fl_r][:, :, 2].max()), 3)] if fl_r.any() else None,
            z_range=[round(float(zr.min()), 3), round(float(zr.max()), 3)] if zr is not None else None,
            centroid_xy=centroid(fm) if has_floor else (centroid(am) if am.any() else None),
            centroid_source="floor_mask" if has_floor else ("any_mask" if am.any() else None),
            centroid_z=round(float(tri_w[fl_r][:, :, 2].mean()), 3) if fl_r.any() else None,
            pinholes_filled_floor=reg_info[rid]["pinholes_filled_floor"],
            pinholes_filled_any=reg_info[rid]["pinholes_filled_any"],
        )
        ov = {}
        for rj, rid2 in enumerate(region_ids):
            if rj != ri:
                ov[str(rid2)] = round(float((fm & floor_m[rj]).sum()) * cell_area, 3)
        entry["floor_overlap_m2"] = ov
        regions_out.append(entry)

    # ---- check (a): total floor area
    ass = [i for i, r in enumerate(region_ids) if r >= 0]
    sum_floor = float(floor_m[ass].sum()) * cell_area
    union_floor = float(floor_m[ass].any(axis=0).sum()) * cell_area
    multi = float((floor_m[ass].sum(axis=0) > 1).sum()) * cell_area
    print(f"\n(a) floor area, regions >=0: sum of per-region areas {sum_floor:.2f} m2; union {union_floor:.2f} m2")
    for e in regions_out:
        print(f"    region {e['region_id']:>3}: floor {e['floor_area_m2']:8.2f} m2  any {e['any_area_m2']:8.2f} m2  "
              f"floor tris {e['n_floor_triangles']:6d}  objects {e['n_objects']:3d}")

    # ---- check (b): own-region any-mask test of object centres
    n_ref = n_in = n_near = n_in_fl = n_near_fl = n_nogeo = 0
    miss = []
    rid2i = {r: i for i, r in enumerate(region_ids)}
    dist_cache = {}

    def dist_to(mask_kind, ri):
        k = (mask_kind, ri)
        if k not in dist_cache:
            mk = any_m[ri] if mask_kind == "any" else floor_m[ri]
            dist_cache[k] = ndimage.distance_transform_edt(~mk) * CELL if mk.any() else None
        return dist_cache[k]

    for o in raw["objects"]:
        rs = str(o["region_id"])
        rid = int(rs.lstrip("_")) if rs.lstrip("_").lstrip("-").isdigit() else None
        if rid is None:
            continue
        if rs == "_-1" or rid < 0:
            continue
        oid = int(o["id"])
        if oid not in obj_min:
            n_nogeo += 1
            continue
        c = (obj_min[oid] + obj_max[oid]) / 2
        ix, iy = int((c[0] - x0) // CELL), int((c[1] - y0) // CELL)
        ri = rid2i[rid]
        n_ref += 1
        da = dist_to("any", ri)
        inside = da is not None and 0 <= ix < nx and 0 <= iy < ny and any_m[ri, iy, ix]
        near = da is not None and 0 <= ix < nx and 0 <= iy < ny and da[iy, ix] <= NEAR
        n_in += int(inside)
        n_near += int(inside or near)
        df = dist_to("floor", ri)
        in_f = df is not None and 0 <= ix < nx and 0 <= iy < ny and floor_m[ri, iy, ix]
        nr_f = df is not None and 0 <= ix < nx and 0 <= iy < ny and df[iy, ix] <= NEAR
        n_in_fl += int(in_f)
        n_near_fl += int(in_f or nr_f)
        if not (inside or near):
            miss.append((oid, o["category"], rid, [round(float(c[0]), 2), round(float(c[1]), 2)]))
    print(f"\n(b) object centres vs own-region mask ({n_ref} objects with a region id >=0 and geometry; "
          f"{n_nogeo} listed objects have no geometry and are skipped)")
    print(f"    any mask: inside {n_in}/{n_ref} = {n_in/n_ref:.4f}; inside or within {NEAR} m {n_near}/{n_ref} = {n_near/n_ref:.4f}")
    print(f"    floor mask (extra): inside {n_in_fl}/{n_ref} = {n_in_fl/n_ref:.4f}; inside or within {NEAR} m {n_near_fl}/{n_ref} = {n_near_fl/n_ref:.4f}")
    print("    first misses (id, category, region, centre xy):", miss[:8])
    print("    note: raw_objects.json holds zero centres for every object, so centres come from this script's own world AABBs.")

    # ---- check (c): overlap of floor masks
    print(f"\n(c) floor area in more than one region's floor mask: {multi:.3f} m2 of {union_floor:.2f} m2 "
          f"= {multi/union_floor:.4f} (share of union); {multi/sum_floor:.4f} of the summed per-region areas")
    flag = n_near / n_ref < 0.8
    if flag:
        print("!! FRAME ERROR SUSPECTED: check (b) share below 0.8")

    # ---- save
    npz = f"{scene}_region_footprints.npz"
    np.savez_compressed(npz,
                        scene=np.array(scene),
                        origin_xy=np.array([x0, y0]), cell_size=np.array(CELL),
                        axis_names=np.array(["x", "y"]), vertical_axis=np.array("z"),
                        region_ids=np.array(region_ids, dtype=np.int64),
                        floor_masks=floor_m, any_masks=any_m,
                        habitat_to_world_R=Tc[:3, :3], habitat_to_world_t=Tc[:3, 3])
    meta = dict(
        scene=scene, grid=dict(origin_xy=[x0, y0], cell_size_m=CELL, nx=nx, ny=ny, mask_index="[region_index, iy, ix]"),
        horizontal_axes=["x", "y"], vertical_axis="z",
        transform=dict(asset_to_habitat="(x,y,z)->(x,z,-y)", habitat_to_world_R=Tc[:3, :3].tolist(),
                       habitat_to_world_t=Tc[:3, 3].tolist(), init=raw["pipeline_initial_agent_state"]),
        triangle_stats=st,
        checks=dict(
            a_floor_area_m2=dict(sum_over_regions=round(sum_floor, 3), union=round(union_floor, 3)),
            b_object_centres=dict(n=n_ref, inside_any=n_in, inside_or_within_0p5m_any=n_near,
                                  share_inside_any=round(n_in / n_ref, 4), share_inside_or_near_any=round(n_near / n_ref, 4),
                                  share_inside_floor=round(n_in_fl / n_ref, 4), share_inside_or_near_floor=round(n_near_fl / n_ref, 4),
                                  skipped_no_geometry=n_nogeo),
            c_floor_overlap=dict(multi_region_area_m2=round(multi, 3), share_of_union=round(multi / union_floor, 4),
                                 share_of_summed=round(multi / sum_floor, 4)),
            reference_cross_check=dict(objects_compared=len(diffs), tri_count_mismatches=ntri_mismatch,
                                       max_aabb_diff_m=float(max(diffs))),
        ),
        regions=regions_out,
    )
    js = f"{scene}_regions.json"
    json.dump(meta, open(js, "w"), indent=1)
    for p in (npz, js):
        print(f"wrote {p} {os.path.getsize(p)} bytes sha256 {sha256(p)}")
    if flag:
        sys.exit(2)


if __name__ == "__main__":
    main()
