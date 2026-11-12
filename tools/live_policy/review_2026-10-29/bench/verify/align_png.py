import glob, json, zlib, struct, sys
import numpy as np
def write_png(path, rgb):
    rgb = np.ascontiguousarray(rgb.astype(np.uint8)); h, w, _ = rgb.shape
    raw = b''.join(b'\x00' + rgb[i].tobytes() for i in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
S = 3
for scene in ("00853", "00871"):
    d = np.load(f"/tmp/cvp_bench/refs/{scene}_walls.npz")
    occ = d["occ"].max(0) > 0; org = d["origin"]; res = float(d["res"])
    W, H = occ.shape
    img = np.full((H * S, W * S, 3), 255, np.uint8)
    big = np.kron(occ.T[::-1].astype(np.uint8), np.ones((S, S), np.uint8)).astype(bool)
    img[big] = 0
    def put(xy, col, r=0):
        ij = (np.asarray(xy) - org) / res * S
        x = ij[:, 0].astype(int); y = (H * S - 1 - ij[:, 1]).astype(int)
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                ok = (x + dx >= 0) & (x + dx < W * S) & (y + dy >= 0) & (y + dy < H * S)
                img[y[ok] + dy, x[ok] + dx] = col
    for f in sorted(glob.glob(f"/tmp/cvp_review/runs/e1_{scene}_s42_official_60m/stages/*/executed_path.json")):
        p = np.array(json.load(open(f))["world_frame_path"], float)[:, :2]
        pts = np.concatenate([a + np.linspace(0, 1, 50)[:, None] * (b - a) for a, b in zip(p[:-1], p[1:])]) if len(p) > 1 else p
        put(pts, (220, 30, 30))
    refs = json.load(open("/tmp/cvp_review/refs/oracle_sets.json"))["scenes"][str(int(scene))]["objects"]
    put(np.array([o["position"][:2] for o in refs]), (30, 160, 30), 2)
    write_png(f"/tmp/cvp_bench/bench/verify/align_{scene}.png", img)
    print(img.shape)
