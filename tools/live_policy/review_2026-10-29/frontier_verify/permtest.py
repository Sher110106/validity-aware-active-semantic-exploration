"""Own scene-blocked exact permutation test, Holm, permutation-inverted CI."""
import itertools
import json

import numpy as np

S = json.load(open("/tmp/cvp_verify_step7/scores.json"))["runs"]
SCENES = ("00853", "00871")
TOL = 1e-12


def counted(arm):
    """Seeds 42-44, final path >= 50 m; one counted run per (scene, seed) cell."""
    cells, dropped = {}, []
    for n, r in S.items():
        if r.get("arm") != arm or r["seed"] not in (42, 43, 44):
            continue
        if r["final_path_m"] < 50.0:
            dropped.append((n, f"final path {r['final_path_m']:.2f} m < 50 m"))
            continue
        key = (r["scene"], r["seed"])
        if key in cells:
            raise SystemExit(f"two counted runs in cell {key}: {cells[key]} and {n}")
        cells[key] = n
    return cells, dropped


def groups(arm, metric, shift=0.0):
    cells, _ = counted(arm)
    fr, _ = counted("frontier")
    out = {}
    for sc in SCENES:
        a = [S[n][metric] - shift for (s, _), n in sorted(cells.items()) if s == sc]
        b = [S[n][metric] for (s, _), n in sorted(fr.items()) if s == sc]
        out[sc] = (np.array(a), np.array(b))
    return out


def stat_of(g):
    return float(np.mean([a.mean() - b.mean() for a, b in g.values()]))


def perm_dist(g):
    per_scene = []
    for sc in SCENES:
        a, b = g[sc]
        pool = np.concatenate([a, b])
        n, na = len(pool), len(a)
        diffs = []
        for idx in itertools.combinations(range(n), na):
            m = np.zeros(n, bool)
            m[list(idx)] = True
            diffs.append(pool[m].mean() - pool[~m].mean())
        per_scene.append(np.array(diffs))
    # all combinations across scenes
    tot = np.add.outer(per_scene[0], per_scene[1]).ravel() / len(SCENES)
    return tot


def test(g):
    obs = stat_of(g)
    dist = perm_dist(g)
    p = float(np.mean(np.abs(dist) >= abs(obs) - TOL))
    return obs, p, len(dist)


def ci(arm, metric, alpha=0.05):
    obs = stat_of(groups(arm, metric))
    grid = np.arange(obs - 0.3, obs + 0.3, 0.00005)
    keep = [d for d in grid if test(groups(arm, metric, shift=d))[1] > alpha]
    return (min(keep), max(keep)) if keep else (None, None)


res = {}
for arm in ("official", "placebo"):
    cells, dropped = counted(arm)
    r = {"counted": sorted(cells.values()), "dropped": dropped}
    for metric in ("auc60", "auc50"):
        obs, p, n = test(groups(arm, metric))
        r[metric] = {"stat": obs, "p": p, "n_relabel": n,
                     "per_scene": {sc: float(a.mean() - b.mean()) for sc, (a, b) in groups(arm, metric).items()}}
    r["auc60"]["ci95"] = ci(arm, "auc60")
    r["auc50"]["ci95"] = ci(arm, "auc50")
    res[arm] = r

# Holm over the two 60 m p-values
ps = sorted((res[a]["auc60"]["p"], a) for a in res)
m = len(ps)
running = 0.0
for i, (p, a) in enumerate(ps):
    adj = min(1.0, max(running, (m - i) * p))
    running = adj
    res[a]["auc60"]["holm_p"] = adj
for a in res:
    res[a]["sign_agree_60_50"] = bool(np.sign(res[a]["auc60"]["stat"]) == np.sign(res[a]["auc50"]["stat"]))

fr, frd = counted("frontier")
res["frontier_counted"] = sorted(fr.values())
res["frontier_dropped"] = frd
json.dump(res, open("/tmp/cvp_verify_step7/perm_results.json", "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
