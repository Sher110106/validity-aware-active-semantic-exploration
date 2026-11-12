"""Wall map for the offline yardstick: slice the HM3D scene mesh with horizontal
planes and rasterise the cuts into a 2D occupancy grid in the pipeline world frame.

Mesh: <scene>.semantic.glb (the same geometry extract_semantic_aabb.py reads).
Frames: asset -> habitat is (x, z, -y); habitat -> pipeline world uses code_R and
code_t from frame_transform.json. In the pipeline frame the floor near the start
is z = 0 and the camera rides at z = 1.1, so planes at z = 0.6, 1.1 and 1.6 m
catch walls and tall furniture that can block a view.

Usage: slice_walls.py <scene> <out.npz>
"""
import sys, json, struct
import numpy as np

HM3D = "/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d"
SCENES = {"00853": "val/00853-5cdEh9F2hJL/5cdEh9F2hJL", "00871": "val/00871-VBzV5z6i1WS/VBzV5z6i1WS"}
REFS = "/workspace/runs/live_campaign/hm3d_refs_work"
HEIGHTS = (0.6, 1.1, 1.6)
RES = 0.05

scene, out = sys.argv[1], sys.argv[2]
ft = json.load(open(f"{REFS}/frame_transform.json"))[scene]
R, t = np.array(ft["code_R"]), np.array(ft["code_t"])
A2H = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=float)

blob = open(f"{HM3D}/{SCENES[scene]}.semantic.glb", "rb").read()
off, J, BIN = 12, None, None
while off < len(blob):
    clen, ctype = struct.unpack("<I4s", blob[off:off + 8]); data = blob[off + 8: off + 8 + clen]; off += 8 + clen
    if ctype == b"JSON": J = json.loads(data)
    elif ctype == b"BIN\x00": BIN = data
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
def accessor(i):
    a = J["accessors"][i]; bv = J["bufferViews"][a["bufferView"]]
    dt = np.dtype(CT[a["componentType"]]); n = NC[a["type"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", 0) or dt.itemsize * n
    if stride == dt.itemsize * n:
        return np.frombuffer(BIN, dtype=dt, count=a["count"] * n, offset=start).reshape(a["count"], n)
    raw = np.frombuffer(BIN, dtype=np.uint8, count=stride * a["count"], offset=start).reshape(a["count"], stride)
    return raw[:, : dt.itemsize * n].copy().view(dt).reshape(a["count"], n)
def node_matrix(nd):
    if "matrix" in nd: return np.array(nd["matrix"], dtype=float).reshape(4, 4).T
    M = np.eye(4); tr = nd.get("translation", [0, 0, 0]); q = nd.get("rotation", [0, 0, 0, 1]); s = nd.get("scale", [1, 1, 1])
    x, y, z, w = q
    Rq = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    M[:3, :3] = Rq * np.array(s)[None, :]; M[:3, 3] = tr
    return M

tris = []
for nd in J["nodes"]:
    if "mesh" not in nd: continue
    M = node_matrix(nd)
    for prim in J["meshes"][nd["mesh"]]["primitives"]:
        P = accessor(prim["attributes"]["POSITION"]).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
        W = (P @ A2H.T) @ R.T + t
        idx = accessor(prim["indices"]).reshape(-1, 3).astype(np.int64)
        tris.append(W[idx])
T = np.concatenate(tris)  # (n, 3, 3) pipeline world
print(scene, "triangles", len(T), "z range", float(T[..., 2].min()), float(T[..., 2].max()))

def cut(T, h):
    """Segments where triangles cross the plane z = h."""
    z = T[..., 2] - h
    segs = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        za, zb = z[:, a], z[:, b]
        m = (za * zb) < 0
        f = za[m] / (za[m] - zb[m])
        segs.append((np.where(m)[0], T[m, a, :2] + f[:, None] * (T[m, b, :2] - T[m, a, :2])))
    pts = {}
    for ids, xy in segs:
        for i, p in zip(ids, xy):
            pts.setdefault(i, []).append(p)
    return [np.array(v[:2]) for v in pts.values() if len(v) >= 2]

xy_all = T[..., :2].reshape(-1, 2)
lo = np.floor(xy_all.min(0) / RES) * RES - 1.0
hi = np.ceil(xy_all.max(0) / RES) * RES + 1.0
shape = tuple(((hi - lo) / RES).astype(int) + 1)
occ = np.zeros((len(HEIGHTS),) + shape, dtype=np.uint8)
for k, h in enumerate(HEIGHTS):
    near = np.abs(T[..., 2].mean(1) - h) < 3.0
    for seg in cut(T[near], h):
        n = max(2, int(np.linalg.norm(seg[1] - seg[0]) / (RES / 2)) + 1)
        s = seg[0] + np.linspace(0, 1, n)[:, None] * (seg[1] - seg[0])
        ij = np.floor((s - lo) / RES).astype(int)
        occ[k, ij[:, 0], ij[:, 1]] = 1
    print(" height", h, "occupied cells", int(occ[k].sum()))
np.savez_compressed(out, occ=occ, heights=np.array(HEIGHTS), origin=lo, res=RES)

try:
    from PIL import Image, ImageDraw
    import glob
    img = Image.fromarray((255 - 255 * occ.max(0).T[::-1]).astype(np.uint8)).convert("RGB")
    d = ImageDraw.Draw(img)
    for f in sorted(glob.glob(f"/workspace/runs/live_campaign/e1_{scene}_s42_*_60m/stages/*/executed_path.json")):
        p = np.array(json.load(open(f))["world_frame_path"])
        if len(p) < 2: continue
        ij = ((p[:, :2] - lo) / RES)
        d.line([(x, img.size[1] - 1 - y) for x, y in ij], fill=(220, 30, 30), width=2)
    img.save(out.replace(".npz", "_check.png"))
except Exception as e:
    print("png skipped:", e)
