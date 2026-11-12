import glob, json, sys, zlib, struct
import numpy as np
def write_png(path, rgb):
    rgb = np.ascontiguousarray(rgb.astype(np.uint8)); h, w, _ = rgb.shape
    raw = b''.join(b'\x00' + rgb[i].tobytes() for i in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
scene, x0, x1, y0, y1, out = sys.argv[1], *map(float, sys.argv[2:6]), sys.argv[6]
d = np.load(f"/tmp/cvp_bench/refs/{scene}_walls.npz"); org = d["origin"]; res = float(d["res"])
S = 8
i0, i1 = int((x0 - org[0]) / res), int((x1 - org[0]) / res)
j0, j1 = int((y0 - org[1]) / res), int((y1 - org[1]) / res)
occ = d["occ"][:, i0:i1, j0:j1]
Wd, Hd = i1 - i0, j1 - j0
img = np.full((Hd * S, Wd * S, 3), 255, np.uint8)
cols = [(170, 170, 255), (0, 0, 0), (120, 120, 120)]  # 0.6 light blue, 1.1 black, 1.6 grey
for k in (0, 2, 1):
    big = np.kron(occ[k].T[::-1].astype(np.uint8), np.ones((S, S), np.uint8)).astype(bool)
    img[big] = cols[k]
def put(xy, col, r=0):
    ij = (np.asarray(xy) - org) / res - [i0, j0]
    x = (ij[:, 0] * S).astype(int); y = (Hd * S - 1 - ij[:, 1] * S).astype(int)
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            ok = (x + dx >= 0) & (x + dx < Wd * S) & (y + dy >= 0) & (y + dy < Hd * S)
            img[y[ok] + dy, x[ok] + dx] = col
for f in sorted(glob.glob(f"/tmp/cvp_review/runs/e*_{scene}_*/stages/*/executed_path.json")):
    p = np.array(json.load(open(f))["world_frame_path"], float)[:, :2]
    put(p, (220, 30, 30), 1)
refs = json.load(open("/tmp/cvp_review/refs/oracle_sets.json"))["scenes"][str(int(scene))]["objects"]
inbox = [o for o in refs if x0 <= o["position"][0] <= x1 and y0 <= o["position"][1] <= y1]
put(np.array([o["position"][:2] for o in inbox]).reshape(-1, 2), (30, 160, 30), 3)
for o in inbox: print(o["name"], np.round(o["position"], 2), np.round(o["dimension"], 2))
write_png(out, img)
