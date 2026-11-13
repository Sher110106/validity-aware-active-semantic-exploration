import json, sys, numpy as np, warnings
from scipy.stats import spearmanr
import os
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(p): return {(r["run"], r["stage"]): r for r in map(json.loads, open(f"{B}/{p}/factorial_stages.jsonl"))}
P1, P2 = load("pass1"), load("pass2")
assert P1.keys() == P2.keys()
keys = sorted(P1, key=lambda k: (P1[k]["run_idx"], k[1]))
left = json.load(open(f"{B}/pass1/left_out_stages.json"))["left_out"]

def rho(a, b):  # own: scipy spearmanr (average ranks), None if either side constant or nan
    a, b = np.asarray(a, float), np.asarray(b, float)
    if np.ptp(a) == 0 or np.ptp(b) == 0: return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore"); r = spearmanr(a, b)[0]
    return float(r) if np.isfinite(r) else None

ARMS = {"F1": ["F1"], "F5": ["F5a", "F5b"], "F6": ["F6"], "F0": ["F0"], "F-room": ["F-room"],
        "F3-deepseek": ["F3-deepseek"], "F3-haiku": ["F3-haiku"], "F3-opus": ["F3-opus"]}
RULE = ["F1", "F5a", "F5b", "F6", "F-room", "F3-deepseek"]

def arm(k, s):
    return P1[k]["arms"].get(s) or P2[k]["arms"][s]

maxdiff = 0.0
def per_stage(k, scorekind, yard):
    global maxdiff
    r = P1[k]; d = np.asarray(r["d"]); y = r["yard"][yard]; out = {}; sub = {}
    for s in sum(ARMS.values(), []):
        a = arm(k, s); ig = np.asarray(a["ig"])
        sc = ig - 0.2 * d
        maxdiff = max(maxdiff, np.max(np.abs(sc - np.asarray(a["score"]))))
        sub[s] = rho(sc if scorekind == "score" else ig, y)
    for A, ss in ARMS.items():
        v = [sub[s] for s in ss]
        out[A] = None if any(x is None for x in v) else float(np.mean(v))
    return out, sub

CONTR = {"A": ("F1",), "B_deepseek": ("F3-deepseek",), "B_haiku": ("F3-haiku",), "B_opus": ("F3-opus",),
         "C": ("F-room",), "F0-F5": ("F0",), "F6-F5": ("F6",)}

def boot(D, seedvariant=0):
    D = np.asarray(D); n = len(D); m = D.mean()
    rng = np.random.default_rng(20261113)
    if seedvariant == 0: w = rng.choice([-1.0, 1.0], size=(9999, n))
    elif seedvariant == 1: w = rng.integers(0, 2, size=(9999, n)) * 2 - 1.0
    else: w = np.where(rng.random((9999, n)) < 0.5, -1.0, 1.0)
    draws = m + (w * (D - m)).mean(1)
    return float(m), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))

def summary(scorekind="score", yard="Ucone", only_official=False, pairing="rule", sv=0):
    ks = [k for k in keys if not (only_official and P1[k]["arm"] != "official")]
    vals = {k: per_stage(k, scorekind, yard) for k in ks}
    undefined_rule = [k for k in ks if any(vals[k][1][s] is None for s in RULE)]
    undefined_any = {A: [k for k in ks if vals[k][0][A] is None] for A in ARMS}
    if pairing == "rule": use = [k for k in ks if k not in undefined_rule and list(k) not in left]
    else: use = [k for k in ks if list(k) not in left]
    runs = sorted({P1[k]["run_idx"] for k in use})
    def runmeans(f):
        R = []
        for ri in runs:
            v = [f(k) for k in use if P1[k]["run_idx"] == ri]
            v = [x for x in v if x is not None]
            if v: R.append(np.mean(v))
        return R
    res = {"n_stages": len(use), "n_runs": len(runs), "undefined_rule": len(undefined_rule),
           "undefined_per_arm": {A: len(v) for A, v in undefined_any.items()}}
    res["arm_mean"] = {A: float(np.mean(runmeans(lambda k, A=A: vals[k][0][A]))) for A in ARMS}
    res["arm_median_stage"] = {A: float(np.median([vals[k][0][A] for k in use if vals[k][0][A] is not None])) for A in ARMS}
    def diff(k, X, Y="F5", half=False):
        a, b = vals[k][0][X], vals[k][0][Y]
        if a is None or b is None: return None
        dv = a - b
        if half:
            f1, f5 = vals[k][0]["F1"], vals[k][0]["F5"]
            if f1 is None: return None
            dv -= 0.5 * (f1 - f5)
        return dv
    res["contrasts"] = {}; DR = {}
    for c, (X,) in CONTR.items():
        DR[c] = runmeans(lambda k, X=X: diff(k, X)); res["contrasts"][c] = boot(DR[c], sv) + (len(DR[c]),)
    for c in ["B_deepseek", "B_haiku", "B_opus", "C"]:
        X = CONTR[c][0]
        D = runmeans(lambda k, X=X: diff(k, X, half=True)); DR[c + "-0.5A"] = D
        res["contrasts"][c + "-0.5A"] = boot(D, sv) + (len(D),)
    lo = res["contrasts"]["A"][1]
    res["verdicts"] = {}
    for c in ["B_deepseek", "B_haiku", "B_opus", "C"]:
        if lo <= 0: res["verdicts"][c] = "not read (A interval not above 0)"; continue
        m, l, h, _ = res["contrasts"][c + "-0.5A"]
        res["verdicts"][c] = "sufficient" if l > 0 else ("not shown sufficient" if h < 0 else "inconclusive")
    res["run_D"] = {c: [float(x) for x in v] for c, v in DR.items()}
    return res

out = {}
out["main"] = summary()
for sv in (1, 2): out[f"main_seedvariant{sv}"] = {"contrasts": summary(sv=sv)["contrasts"]}
out["ig_alone"] = summary(scorekind="ig")
out["Ucone_audit"] = summary(yard="Ucone_audit")
out["U360"] = summary(yard="U360")
out["Uwall"] = summary(yard="Uwall")
out["official"] = summary(only_official=True)
for v in ["ig_alone", "Ucone_audit", "U360"]:
    out[v + "_pairwise"] = summary(scorekind="ig" if v == "ig_alone" else "score",
                                   yard={"ig_alone": "Ucone"}.get(v, v), pairing="pair")
F0zero = sum(all(x == 0 for x in P1[k]["arms"]["F0"]["ig"]) for k in keys)
out["F0_ig_all_zero"] = [F0zero, len(keys), F0zero / len(keys)]
out["max_abs_score_minus_filed_score"] = float(maxdiff)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mine.json"), "w"), indent=1)
for name in ["main", "ig_alone", "Ucone_audit", "U360", "official", "ig_alone_pairwise", "Ucone_audit_pairwise", "U360_pairwise"]:
    r = out[name]; print("==", name, r["n_stages"], r["n_runs"], "undef_rule", r["undefined_rule"], r["undefined_per_arm"])
    print("  means", {k: round(v, 4) for k, v in r["arm_mean"].items()})
    print("  medians", {k: round(v, 4) for k, v in r["arm_median_stage"].items()})
    for c, t in r["contrasts"].items(): print(f"  {c:16s} {t[0]:+.4f} [{t[1]:+.4f}, {t[2]:+.4f}] n={t[3]}")
    print("  verdicts", r["verdicts"])
for sv in (1, 2): print("seedvariant", sv, {c: [round(x, 4) for x in t[:3]] for c, t in out[f"main_seedvariant{sv}"]["contrasts"].items()})
print("F0 ig all zero", out["F0_ig_all_zero"], "maxdiff score", maxdiff)
