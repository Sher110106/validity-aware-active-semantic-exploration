"""Pre-registered analysis for the live campaign's confirmatory contrasts.

Input: the JSON list that live_score.py prints. Run names follow
e<k>_<scene>_s<seed>_<arm>_<budget>m. For each pair of arms (default
official vs placebo):

- unit: run; statistic: mean over scenes of (mean arm A - mean arm B) of
  author-faithful object F1 AUC over 0 to <budget> m (af_f1, tracks averaged);
- primary test: scene-blocked permutation of arm labels within each scene
  (exact enumeration), two-sided;
- secondary: seed-paired sign-flip test over (scene, seed) cells that have
  both arms (exact);
- scene-blocked bootstrap 95% CI of the statistic (runs resampled within
  scene and arm);
- minimum detectable effect at alpha 0.05 and power 0.8 from the pooled
  within-scene, within-arm SD (normal approximation).
Runs below the budget, or flagged excluded in the exclusions file, are
dropped and listed. Never read "no detectable difference" as "equal".

Usage: python3 e1_analysis.py scores.json [--a official --b placebo]
       [--metric af_f1] [--budget 60] [--exclude exclusions.json]
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import re
import statistics
import sys
from collections import defaultdict

NAME = re.compile(r"e\d+_(?P<scene>\d{5})_s(?P<seed>\d+)_(?P<arm>[a-z_]+)_(?P<budget>\d+)m$")


def parse(run_dir: str):
    m = NAME.search(run_dir.rstrip("/").split("/")[-1])
    return (m.group("scene"), int(m.group("seed")), m.group("arm")) if m else None


def stat(groups: dict, a: str, b: str) -> float:
    diffs = [statistics.mean(v[a]) - statistics.mean(v[b]) for v in groups.values() if v[a] and v[b]]
    return statistics.mean(diffs) if diffs else float("nan")


def blocked_permutation(groups: dict, a: str, b: str) -> tuple[float, int]:
    observed = stat(groups, a, b)
    per_scene = []
    for scene, v in groups.items():
        pooled = v[a] + v[b]
        n_a = len(v[a])
        per_scene.append([(list(c), [pooled[i] for i in range(len(pooled)) if i not in c])
                          for c in itertools.combinations(range(len(pooled)), n_a)])
    count = total = 0
    for combo in itertools.product(*per_scene):
        diffs = []
        for (scene, v), (idx_a, rest_vals) in zip(groups.items(), combo):
            pooled = v[a] + v[b]
            vals_a = [pooled[i] for i in idx_a]
            diffs.append(statistics.mean(vals_a) - statistics.mean(rest_vals))
        s = statistics.mean(diffs)
        total += 1
        if abs(s) >= abs(observed) - 1e-12:
            count += 1
    return count / total, total


def paired_signflip(cells: dict, a: str, b: str) -> tuple[float, int, list]:
    d = [v[a] - v[b] for v in cells.values() if a in v and b in v]
    if not d:
        return float("nan"), 0, d
    obs = abs(statistics.mean(d))
    count = sum(1 for signs in itertools.product((1, -1), repeat=len(d))
                if abs(statistics.mean(s * x for s, x in zip(signs, d))) >= obs - 1e-12)
    return count / 2 ** len(d), len(d), d


def bootstrap_ci(groups: dict, a: str, b: str, n: int = 10000, seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        g = {s: {a: [rng.choice(v[a]) for _ in v[a]], b: [rng.choice(v[b]) for _ in v[b]]} for s, v in groups.items()}
        vals.append(stat(g, a, b))
    vals.sort()
    return vals[int(0.025 * n)], vals[int(0.975 * n) - 1]


def mde(groups: dict, a: str, b: str) -> float:
    resid = []
    for v in groups.values():
        for arm in (a, b):
            if len(v[arm]) > 1:
                m = statistics.mean(v[arm])
                resid += [(x - m) for x in v[arm]]
    dof = sum(max(len(v[a]) - 1, 0) + max(len(v[b]) - 1, 0) for v in groups.values())
    if dof <= 0:
        return float("nan")
    sd = math.sqrt(sum(r * r for r in resid) / dof)
    n_scenes = sum(1 for v in groups.values() if v[a] and v[b])
    n_a = statistics.mean(len(v[a]) for v in groups.values())
    n_b = statistics.mean(len(v[b]) for v in groups.values())
    se = sd * math.sqrt(1 / n_a + 1 / n_b) / math.sqrt(n_scenes)
    return (1.96 + 0.84) * se


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scores")
    ap.add_argument("--a", default="official")
    ap.add_argument("--b", default="placebo")
    ap.add_argument("--metric", default="af_f1")
    ap.add_argument("--budget", type=int, default=60)
    ap.add_argument("--exclude", default=None)
    ap.add_argument("--ref", default="hm3d_", help="key prefix: 'hm3d_' (annotation reference) or '' (frontier reference)")
    ap.add_argument("--min-path", type=float, default=50.0, help="pre-registered exclusion: runs stopping below this")
    args = ap.parse_args()
    runs = json.load(open(args.scores))
    excluded = set(json.load(open(args.exclude))) if args.exclude else set()
    key = f"{args.ref}auc_{args.metric}_to_{args.budget}m"
    groups: dict = defaultdict(lambda: {args.a: [], args.b: []})
    cells: dict = defaultdict(dict)
    dropped = []
    for r in runs:
        parsed = parse(r["run_dir"])
        if not parsed or parsed[2] not in (args.a, args.b):
            continue
        name = r["run_dir"].rstrip("/").split("/")[-1]
        if name in excluded or key not in r or r.get("final_path_m", 0) < args.min_path:
            reason = "excluded" if name in excluded else (f"no {key}" if key not in r else f"stopped at {r.get('final_path_m')} m")
            dropped.append({"run": name, "reason": reason})
            continue
        scene, seed, arm = parsed
        groups[scene][arm].append(r[key])
        cells[(scene, seed)][arm] = r[key]
    groups = {s: v for s, v in sorted(groups.items()) if v[args.a] and v[args.b]}
    out = {"contrast": f"{args.a} - {args.b}", "metric": key, "dropped": dropped,
           "per_scene": {s: {args.a: v[args.a], args.b: v[args.b],
                             "diff_of_means": statistics.mean(v[args.a]) - statistics.mean(v[args.b])} for s, v in groups.items()}}
    if groups:
        out["statistic"] = stat(groups, args.a, args.b)
        out["blocked_permutation_p"], out["n_relabelings"] = blocked_permutation(groups, args.a, args.b)
        out["seed_paired_signflip_p"], out["n_pairs"], out["pair_diffs"] = paired_signflip(cells, args.a, args.b)
        out["bootstrap_95ci"] = bootstrap_ci(groups, args.a, args.b)
        out["mde_alpha05_power80"] = mde(groups, args.a, args.b)
        out["min_attainable_p"] = 1 / out["n_relabelings"] * 2 if out["n_relabelings"] else None
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
