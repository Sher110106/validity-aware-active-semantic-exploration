"""Hand-picked wall cases: builder's wall_visible vs my exact traversal."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/tmp/cvp_bench/bench/build")
sys.path.insert(0, "/tmp/cvp_bench/bench/verify")
import numpy as np
import bench as B
import verify_stages as VS
out = []
for scene in ("00853", "00871"):
    occ, org, res = VS.wallmap(scene)
    # long horizontal wall runs (constant j, consecutive i) in the union map
    cases = []
    for j in range(5, occ.shape[1] - 5):
        row = occ[:, j]
        i = 0
        while i < occ.shape[0]:
            if row[i]:
                s = i
                while i < occ.shape[0] and row[i]:
                    i += 1
                if i - s >= 30:
                    m = (s + i) // 2
                    # free column 20 cells either side?
                    above = occ[m - 1:m + 2, j + 1:j + 21].any()
                    below = occ[m - 1:m + 2, j - 20:j].any()
                    if not above and not below:
                        cases.append((m, j, i - s))
            i += 1
    print(scene, "wall runs with 1 m clear both sides:", len(cases))
    for (m, j, n) in cases[:4]:
        wx, wy = org + (np.array([m, j]) + 0.5) * res
        same_a = np.array([wx, wy + 0.4]); same_b = np.array([wx, wy + 0.95])  # same side, 0.55 m apart
        opp_a = np.array([wx, wy - 0.9]); opp_b = np.array([wx, wy + 0.9])     # across the wall
        tail = np.array([wx, wy + 0.10])                                        # object 0.10 m behind wall line (from below)
        tail2 = np.array([wx, wy - 0.10])
        far_b = np.array([wx, wy + 0.30])  # object 0.30 m past wall (wall not in last 0.15 m)
        tests = [("same side, 0.55 m", same_a, same_b, True),
                 ("across wall, 1.8 m", opp_a, opp_b, False),
                 ("across wall reversed", opp_b, opp_a, False),
                 ("object 0.10 m past wall (tail)", opp_a, tail, True),
                 ("object 0.10 m before wall, other side", opp_b, tail2, True),
                 ("object 0.30 m past wall", opp_a, far_b, False)]
        for name, c, o, expect in tests:
            b = bool(B.wall_visible(scene, c[None], o[None])[0, 0])
            v = bool(VS.wall_vis(scene, c[None], o[None])[0, 0])
            out.append((scene, (round(wx, 2), round(wy, 2)), name, expect, b, v))
            print(f"  wall at ({wx:.2f},{wy:.2f}) run {n} cells | {name}: expected {expect}, builder {b}, mine {v}")
