import json, numpy as np
import os
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L1 = [json.loads(l) for l in open(f"{B}/pass1/factorial_stages.jsonl")]
L2 = {(r["run"], r["stage"]): r for r in map(json.loads, open(f"{B}/pass2/factorial_stages.jsonl"))}
two = sum(len({g // 4 for g in r["gids"]}) > 1 for r in L1); print("stages with >1 track", two, len(L1))
nm = sum(r["arms"]["F-room"]["info"]["n_members_no_unseen_typed"] for r in L1)
tot = sum(len(r["gids"]) for r in L1)
st = sum(r["arms"]["F-room"]["info"]["n_members_no_unseen_typed"] > 0 for r in L1)
allm = sum(r["arms"]["F-room"]["info"]["n_members_no_unseen_typed"] == len(r["gids"]) for r in L1)
print("F-room no unseen typed members", nm, "of", tot, "stages", st, "all", allm)
for a in ["F1", "F5a", "F5b", "F6", "F0", "F3-deepseek", "F-room"]:
    v = sum((r["arms"][a]["n_obj"] for r in L1), []); print(a, round(np.mean(v), 2), min(v), max(v))
for a in ["F3-haiku", "F3-opus"]:
    v = sum((r["arms"][a]["n_obj"] for r in L2.values()), []); print(a, round(np.mean(v), 2), min(v), max(v))
fb = sum(r["arms"]["F3-deepseek"]["info"]["n_fallback_members"] for r in L1) + sum(r["arms"][a]["info"]["n_fallback_members"] for r in L2.values() for a in ["F3-haiku", "F3-opus"])
print("F3 fallback members", fb)
for m, p in [("deepseek", "pass1"), ("haiku", "pass2"), ("opus", "pass2")]:
    e = json.load(open(f"{B}/{p}/err_{m}.json")); e = e if isinstance(e, list) else e.get("distances", e)
    print(m, len(e), round(float(np.median(e)), 2))
# regret means over runs, with bootstrap on difference vs F5
rng_seed = 20261113
runs = sorted({r["run_idx"] for r in L1})
def arm(r, a): return r["arms"].get(a) or L2[(r["run"], r["stage"])]["arms"][a]
for y in ["Uwall", "Ucone"]:
    def val(r, a):
        return np.mean([arm(r, "F5a")["regret"][y], arm(r, "F5b")["regret"][y]]) if a == "F5" else arm(r, a)["regret"][y]
    out = {}
    for a in ["F1", "F5", "F6", "F0", "F3-deepseek", "F3-haiku", "F3-opus", "F-room"]:
        R = np.array([np.mean([val(r, a) for r in L1 if r["run_idx"] == ri]) for ri in runs]); out[a] = R
    print(y, {a: round(v.mean(), 2) for a, v in out.items()})
    for a in out:
        if a == "F5": continue
        D = out[a] - out["F5"]; m = D.mean()
        w = np.random.default_rng(rng_seed).choice([-1.0, 1.0], size=(9999, len(D)))
        dr = m + (w * (D - m)).mean(1)
        print("  ", a, "-F5", round(m, 3), np.round(np.percentile(dr, [2.5, 97.5]), 3))
