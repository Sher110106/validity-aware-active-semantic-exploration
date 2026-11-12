import importlib.util, json
import numpy as np
spec = importlib.util.spec_from_file_location("pt", "/tmp/cvp_verify_step7/permtest_lib.py")
pt = importlib.util.module_from_spec(spec); spec.loader.exec_module(pt)
for arm in ("official", "placebo"):
    for metric in ("auc60", "auc50"):
        g = pt.groups(arm, metric)
        gr = {s: (np.round(a, 4), np.round(b, 4)) for s, (a, b) in g.items()}
        obs, p, n = pt.test(g)
        obsr, pr, _ = pt.test(gr)
        # how many relabelings sit within 1e-6 of |obs| (near-ties)
        dist = pt.perm_dist(g)
        near = np.sort(np.abs(np.abs(dist) - abs(obs)))[:6]
        print(f"{arm} {metric}: full p={p} (stat {obs:.7f}); rounded-4dp p={pr} (stat {obsr:.7f}); closest |stat| gaps {near}")
        if p != pr:
            dr = pt.perm_dist(gr)
            idx = np.where((np.abs(dr) >= abs(obsr) - 1e-12) != (np.abs(dist) >= abs(obs) - 1e-12))[0]
            for i in idx:
                print("   flipped relabeling", i, "full", dist[i], "rounded", dr[i], "obs full", obs, "obs rounded", obsr)
