#!/usr/bin/env python3
"""Outcome, summary and reading rule of PREREGISTRATION_M2.md §5 and §6 (sha256 5b8a8400...), from factorial.py's output.

    python -B summarise_factorial.py PASS1/factorial_stages.jsonl [PASS2/factorial_stages.jsonl ...] \
        --left-out PASS1/left_out_stages.json --out summary_factorial.json

Per stage and arm: the Spearman correlation (the audit's `rho`) between the arm's score and the yardstick over
the stage's candidates; F5's value is the mean of its two sets' correlations. A stage where the correlation is
undefined for F1, either F5 set, F6, F-room or F3-DeepSeek is left out for every arm and counted. That list is
fixed on the first pass: if --left-out names an existing file it is read and used as it stands, else it is
computed from the data and written there. Per run: the mean over its stages of the per-stage difference between
two arms; summary: the mean over runs, each run weighing the same. Interval: wild cluster bootstrap over runs,
D_r the run's mean difference, D-bar their mean, each of 9,999 draws the mean over runs of D-bar + w_r (D_r - D-bar),
Rademacher w_r, seed 20261113, 2.5th and 97.5th percentiles. §6 reads A = F1 - F5, B_m = F3-m - F5, C = F-room - F5
(F0 takes no part). Also: median per-stage correlation; everything again with `ig` alone, with the audit's U_cone
and with U_360; R1 regret under U_wall and U_wall_cone; the official-arm stages alone; runs clustered by scene and
seed; objects per member in each arm. Several jsonl files (passes) are merged by (run, stage).
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.dont_write_bytecode = True
import numpy as np  # noqa: E402

# =====================================================================================
# Values fixed by PREREGISTRATION_M2.md
# =====================================================================================
BOOT_DRAWS = 9999                 # §5
BOOT_SEED = 20261113              # §5
BOOT_PCT = (2.5, 97.5)            # §5
EXCLUSION_ARMS = ("F1", "F5", "F6", "F-room", "F3-deepseek")   # §5; F5 stands for both of its sets
SUFFICIENT_FRACTION = 0.5         # §6: X - 0.5 A
VERDICT_NOT_SUFFICIENT = "not shown sufficient, on a provisional yardstick"   # §6
OFFICIAL_ARM = "official"
# (score column, yardstick): the main reading and the three repeats of §5
VARIANTS = OrderedDict([("main", ("score", "Ucone")), ("ig_alone", ("ig", "Ucone")),
                        ("audit_Ucone", ("score", "Ucone_audit")), ("U360", ("score", "U360"))])
REGRET_YARDSTICKS = ("Uwall", "Ucone")   # "U_wall and U_wall_cone"
LEFT_OUT_YARDSTICK = ("score", "Ucone")  # the left-out list is decided on the main reading


# =====================================================================================
# rho: the audit's, else its copy
# =====================================================================================
def _rho_copy(a, b):
    """Copied from audit.rho (AU:129-136)."""
    from scipy.stats import spearmanr
    a, b = np.asarray(a, float), np.asarray(b, float)
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = spearmanr(a, b).statistic
    return None if not np.isfinite(r) else float(r)


def get_rho():
    """(function, source). The audit's `rho` if the bench farm lets audit.py import; else the copy."""
    try:
        sys.path.insert(0, "/tmp/cvp_review/audit/audit")
        import audit as au  # noqa: WPS433
        return au.rho, "audit.rho"
    except Exception:
        return _rho_copy, "copy of audit.rho"
    finally:
        if sys.path and sys.path[0] == "/tmp/cvp_review/audit/audit":
            sys.path.pop(0)


# =====================================================================================
# Bootstrap (§5 exactly)
# =====================================================================================
def rademacher(n_runs: int, draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> np.ndarray:
    """(draws, n_runs) of +1/-1, one matrix for every statistic so that they are paired."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2, size=(draws, n_runs)).astype(float) * 2.0 - 1.0


def boot_ci(x: Sequence[float], W: np.ndarray) -> Dict[str, float]:
    """x: D_r per run. Each draw is the mean over runs of D-bar + w_r (D_r - D-bar); interval = the 2.5th and
    97.5th percentiles of the draws."""
    x = np.asarray(x, float)
    if W.shape[1] != len(x):
        raise ValueError(f"weights have {W.shape[1]} columns, x has {len(x)}")
    xbar = float(x.mean())
    draws = (xbar + W * (x - xbar)[None, :]).mean(axis=1)
    lo, hi = np.percentile(draws, BOOT_PCT)
    return {"mean": xbar, "lo": float(lo), "hi": float(hi), "n_runs": int(len(x))}


# =====================================================================================
# §6
# =====================================================================================
def wholly_above(ci: Dict[str, float]) -> bool:
    return ci["lo"] > 0.0


def wholly_below(ci: Dict[str, float]) -> bool:
    return ci["hi"] < 0.0


def read_outcome(ci_A: Dict[str, float], ci_X: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """§6 on intervals. ci_A: interval of A. ci_X: for each X (B_m, C) the interval of X - 0.5 A.
    1. A not wholly above 0: M2 is not read further. 2. Else each X: sufficient if wholly above 0,
    not shown sufficient if wholly below 0, inconclusive otherwise."""
    if not wholly_above(ci_A):
        return {"step": 1, "A_separates": False, "read_further": False,
                "reading": "the ceiling does not separate from the floor on this yardstick; M2 is not read further",
                "verdicts": {}}
    v = {}
    for name, ci in ci_X.items():
        v[name] = "sufficient" if wholly_above(ci) else (VERDICT_NOT_SUFFICIENT if wholly_below(ci) else "inconclusive")
    return {"step": 2, "A_separates": True, "read_further": True, "reading": None, "verdicts": v}


# =====================================================================================
# Rows
# =====================================================================================
def load_rows(paths: Sequence[str]) -> List[dict]:
    """Rows of one or more passes merged by (run, stage): arms are united. The yardsticks of two passes must be equal."""
    merged: "OrderedDict[tuple, dict]" = OrderedDict()
    for p in paths:
        for line in open(p):
            r = json.loads(line)
            key = (r["run"], r["stage"])
            if key not in merged:
                merged[key] = r
                continue
            m = merged[key]
            if "arms" in r and "arms" in m:
                if r["yard"] != m["yard"]:
                    raise ValueError(f"{key}: the passes disagree on the yardsticks")
                m["arms"].update(r["arms"])
            elif "arms" in r:
                merged[key] = r
    return list(merged.values())


def _usable(rows):
    return [r for r in rows if "error" not in r and "drop" not in r and "arms" in r]


def _key(r):
    return f"{r['run']}:{r['stage']}"


def arm_names(rows) -> List[str]:
    """Every arm in the data, F5a/F5b replaced by F5; order F1, F5, F6, F0, F3-*, F-room."""
    out = []
    for r in rows:
        for a in r["arms"]:
            a2 = "F5" if a in ("F5a", "F5b") else a
            if a2 not in out:
                out.append(a2)
    order = ["F1", "F5", "F6", "F0"]
    return sorted(out, key=lambda a: (order.index(a), a) if a in order else ((4 if a.startswith("F3-") else 5), a))


def stage_rho(row: dict, score_key: str, yard: str, rho) -> Dict[str, Optional[float]]:
    """arm -> Spearman correlation of the arm's score column with the yardstick (None if undefined).
    F5 is the mean of its two sets' correlations, None if either is None."""
    y = np.asarray(row["yard"][yard], float)
    out: Dict[str, Optional[float]] = {a: rho(np.asarray(v[score_key], float), y) for a, v in row["arms"].items()}
    if "F5a" in out or "F5b" in out:
        parts = [out.pop("F5a", None), out.pop("F5b", None)]
        out["F5"] = None if any(p is None for p in parts) else float(np.mean(parts))
    return out


def stage_regret(row: dict, yard: str) -> Dict[str, float]:
    reg: Dict[str, float] = {a: float(v["regret"][yard]) for a, v in row["arms"].items()}
    if "F5a" in reg or "F5b" in reg:
        parts = [reg.pop("F5a", None), reg.pop("F5b", None)]
        reg["F5"] = float(np.mean([p for p in parts if p is not None]))
    return reg


def compute_left_out(rows: list, rho) -> Dict[str, Any]:
    """The first pass: stages where the main correlation is undefined for F1, either F5 set, F6, F-room or F3-DeepSeek."""
    rows = _usable(rows)
    present = arm_names(rows)
    missing = [a for a in EXCLUSION_ARMS if a not in present]
    if missing:
        raise ValueError(f"the left-out list needs arms {missing}, which the data lack")
    out = []
    for r in rows:
        rr = stage_rho(r, *LEFT_OUT_YARDSTICK, rho)
        bad = [a for a in EXCLUSION_ARMS if rr.get(a) is None]
        if bad:
            out.append({"key": _key(r), "run": r["run"], "stage": r["stage"], "undefined_for": bad})
    return {"rule": "main correlation (R1 score vs Ucone) undefined for any of: " + ", ".join(EXCLUSION_ARMS),
            "arms": list(EXCLUSION_ARMS), "n_matched": len(rows), "n_left_out": len(out), "left_out": out}


def load_or_make_left_out(rows: list, path: Optional[str], rho) -> Dict[str, Any]:
    if path and Path(path).exists():
        d = json.loads(Path(path).read_text())
        d["source"] = "read from " + str(path)
        return d
    d = compute_left_out(rows, rho)
    d["source"] = "computed on this pass"
    if path:
        Path(path).write_text(json.dumps(d, indent=1))
        d["source"] = "computed on this pass and written to " + str(path)
    return d


# =====================================================================================
# One analysis (a variant on a set of rows)
# =====================================================================================
def _ci_block(series: Dict[str, np.ndarray], W: np.ndarray) -> Dict[str, dict]:
    out = {}
    for k, v in series.items():
        v = np.asarray(v, float)
        ok = np.isfinite(v)
        if not ok.any():
            out[k] = {"error": "no run has a value"}
            continue
        out[k] = boot_ci(v[ok], W[:, ok])
        if not ok.all():
            out[k]["n_runs_without_value"] = int((~ok).sum())
    return out


def _run_mean(vals_by_run: "OrderedDict[str, List[Optional[float]]]") -> np.ndarray:
    return np.array([np.mean([v for v in vs if v is not None]) if any(v is not None for v in vs) else np.nan
                     for vs in vals_by_run.values()])


def analyse(rows: list, left_out_keys: set, variant: str, rho, cluster_of=None, with_regret: bool = False) -> Dict[str, Any]:
    """§5 for one variant on one set of usable rows."""
    score_key, yard = VARIANTS[variant]
    arms = arm_names(rows)
    kept_rows = [r for r in rows if _key(r) not in left_out_keys]
    must = [a for a in EXCLUSION_ARMS if a in arms]
    stages = []
    n_extra = 0
    undef_extra = {a: 0 for a in arms}
    for r in kept_rows:
        rr = stage_rho(r, score_key, yard, rho)
        if any(rr.get(a) is None for a in must):     # undefined here (another yardstick or score): paired drop
            n_extra += 1
            continue
        for a in arms:
            if rr.get(a) is None:
                undef_extra[a] += 1
        stages.append((r, rr))
    out: Dict[str, Any] = {"variant": variant, "score": score_key, "yardstick": yard, "n_stages_matched": len(rows),
                           "n_left_out_by_list": len(rows) - len(kept_rows), "n_dropped_extra_undefined": n_extra,
                           "n_stages_kept": len(stages), "n_undefined_after_list_by_arm": undef_extra, "arms": arms}
    if not stages:
        out["error"] = "no stage kept"
        return out
    by_run: "OrderedDict[str, list]" = OrderedDict()
    for r, rr in sorted(stages, key=lambda s: (s[0]["run_idx"], s[0]["stage"])):
        by_run.setdefault(r["run"], []).append((r, rr))
    runs = list(by_run)
    out["runs"], out["n_runs"] = runs, len(runs)
    if cluster_of is None:
        W = rademacher(len(runs))
    else:
        cl = [cluster_of(by_run[r][0][0]) for r in runs]
        names = sorted(set(cl))
        Wc = rademacher(len(names))
        W = Wc[:, [names.index(c) for c in cl]]
        out["clusters"] = [list(c) for c in names]
    def per_run(fn):
        return _run_mean(OrderedDict((run, [fn(rr) for _, rr in ss]) for run, ss in by_run.items()))
    mean = {a: per_run(lambda rr, a=a: rr.get(a)) for a in arms}
    out["per_run_mean_rho"] = {run: {a: (None if np.isnan(mean[a][i]) else float(mean[a][i])) for a in arms}
                               for i, run in enumerate(runs)}
    out["arm_mean_rho"] = _ci_block(mean, W)
    out["median_stage_rho"] = {a: float(np.median([rr[a] for _, rr in stages if rr.get(a) is not None]))
                               if any(rr.get(a) is not None for _, rr in stages) else None for a in arms}
    if "F1" in arms and "F5" in arms:
        def diff(a):
            return per_run(lambda rr: None if rr.get(a) is None or rr.get("F5") is None else rr[a] - rr["F5"])
        diffs = {"A": diff("F1")}
        reading_series = {}
        for a in arms:
            if a in ("F1", "F5"):
                continue
            d = diff(a)
            if a == "F-room":
                name = "C"
            elif a.startswith("F3-"):
                name = f"B_{a[3:]}"
            else:
                name = f"{a}-F5"          # F6 and F0: reported, not read
            diffs[name] = d
            if name == "C" or name.startswith("B_"):
                reading_series[name] = d - SUFFICIENT_FRACTION * diffs["A"]
        out["differences"] = _ci_block(diffs, W)
        out["reading_series"] = _ci_block(reading_series, W)
        if "error" in out["differences"]["A"] or any("error" in v for v in out["reading_series"].values()):
            out["reading"] = {"error": "a series has no value"}
        else:
            out["reading"] = read_outcome(out["differences"]["A"], out["reading_series"])
    else:
        out["reading"] = {"error": "F1 or F5 missing"}
    if with_regret:
        out["regret_R1"] = {}
        for u in REGRET_YARDSTICKS:
            regs = [(r, stage_regret(r, u)) for r, _ in stages]
            by = OrderedDict()
            for r, rg in sorted(regs, key=lambda s: (s[0]["run_idx"], s[0]["stage"])):
                by.setdefault(r["run"], []).append(rg)
            rm = {a: _run_mean(OrderedDict((run, [rg.get(a) for rg in ss]) for run, ss in by.items())) for a in arms}
            rd = {f"{a}-F5": rm[a] - rm["F5"] for a in arms if a != "F5"} if "F5" in rm else {}
            out["regret_R1"][u] = {"arm_mean": _ci_block(rm, W), "difference_to_F5": _ci_block(rd, W),
                                   "median_stage": {a: float(np.median([rg[a] for _, rg in regs if a in rg])) for a in arms}}
    return out


# =====================================================================================
# Counts reported beside the outcome
# =====================================================================================
def counts(rows: list, kept_keys: Optional[set] = None) -> Dict[str, Any]:
    """Objects per member in each arm, the share of stages where ig is 0 for every candidate, F-room members
    with no unseen typed region, and F3 members that fell back to placebo objects (not moved)."""
    out: Dict[str, Any] = {"n_stages": len(rows)}
    names = sorted({a for r in rows for a in r["arms"]})
    obj, zero = {}, {}
    for a in names:
        per_stage_mean, members, nz, n = [], [], 0, 0
        for r in rows:
            if a not in r["arms"]:
                continue
            v = r["arms"][a]
            n += 1
            per_stage_mean.append(float(np.mean(v["n_obj"])))
            members += list(v["n_obj"])
            nz += int(np.all(np.abs(np.asarray(v["ig"], float)) < 1e-12))
        obj[a] = {"mean_per_member": float(np.mean(members)), "mean_of_stage_means": float(np.mean(per_stage_mean)),
                  "min": int(np.min(members)), "max": int(np.max(members)), "n_members": len(members)}
        zero[a] = {"stages_ig_zero_for_every_candidate": nz, "n_stages": n, "share": nz / n if n else None}
    out["objects_per_member"], out["ig_zero_stage_share"] = obj, zero
    fr = [(r, r["arms"]["F-room"]["info"]["per_member"]) for r in rows if "F-room" in r["arms"]]
    if fr:
        out["froom_no_unseen_typed"] = {
            "members": int(sum(p["no_unseen_typed"] for _, pm in fr for p in pm)),
            "members_total": int(sum(len(pm) for _, pm in fr)),
            "stages_with_a_member": int(sum(any(p["no_unseen_typed"] for p in pm) for _, pm in fr)),
            "stages_all_members": int(sum(all(p["no_unseen_typed"] for p in pm) for _, pm in fr)),
            "stages_total": len(fr)}
    for a in names:
        if a.startswith("F3-"):
            pm = [(r, r["arms"][a]["info"]["per_member"]) for r in rows if a in r["arms"]]
            out.setdefault("f3_fallback_members_not_moved", {})[a] = {
                "members": int(sum(p["fallback"] for _, m in pm for p in m)),
                "members_total": int(sum(len(m) for _, m in pm)),
                "stages_with_one": int(sum(any(p["fallback"] for p in m) for _, m in pm)), "stages_total": len(pm)}
    return out


def scene_seed(row: dict) -> tuple:
    return (str(row["scene"]), int(row["seed"]))


def summarise(rows: list, rho=None, left_out_path: Optional[str] = None) -> Dict[str, Any]:
    rho_src = "given"
    if rho is None:
        rho, rho_src = get_rho()
    usable = _usable(rows)
    left = load_or_make_left_out(usable, left_out_path, rho)
    keys = {x["key"] for x in left["left_out"]}
    official = [r for r in usable if r.get("arm") == OFFICIAL_ARM]
    res: Dict[str, Any] = {
        "rho_source": rho_src, "n_rows": len(rows), "n_rows_usable": len(usable),
        "n_rows_error": sum(1 for r in rows if "error" in r), "n_rows_dropped_replay": sum(1 for r in rows if "drop" in r),
        "left_out": {k: v for k, v in left.items() if k != "left_out"} | {"keys": sorted(keys)},
        "counts_all_stages": counts(usable), "counts_official_stages": counts(official) if official else None,
        "analysis": {}, "clustered_by_scene_seed": {}}
    for name in VARIANTS:
        res["analysis"][name] = {
            "all": analyse(usable, keys, name, rho, with_regret=(name == "main")),
            "official": analyse(official, keys, name, rho, with_regret=(name == "main")) if official else None}
        res["clustered_by_scene_seed"][name] = analyse(usable, keys, name, rho, cluster_of=scene_seed)
    return res


def format_text(res: Dict[str, Any]) -> str:
    L = [f"stages: {res['n_rows_usable']} usable of {res['n_rows']} rows; left out by the list: {res['left_out']['n_left_out']} "
         f"({res['left_out']['source']}); rho: {res['rho_source']}"]
    def block(title, a):
        L.append(f"== {title}: {a['n_stages_kept']} stages kept, {a.get('n_runs', 0)} runs")
        if "error" in a:
            L.append("   " + a["error"])
            return
        for arm, ci in a["arm_mean_rho"].items():
            if "error" not in ci:
                L.append(f"   {arm:14s} mean {ci['mean']:+.3f} [{ci['lo']:+.3f}, {ci['hi']:+.3f}]  median {a['median_stage_rho'][arm]:+.3f}")
        for nm, ci in a.get("differences", {}).items():
            if "error" not in ci:
                L.append(f"   {nm:14s} {ci['mean']:+.3f} [{ci['lo']:+.3f}, {ci['hi']:+.3f}]")
        rd = a.get("reading", {})
        L.append("   reading: " + (rd.get("reading") or json.dumps(rd.get("verdicts") or rd)))
    for name in VARIANTS:
        block(f"{name} (all stages)", res["analysis"][name]["all"])
    block("main (official-arm stages)", res["analysis"]["main"]["official"] or {"n_stages_kept": 0, "error": "none"})
    block("main (clustered by scene and seed)", res["clustered_by_scene_seed"]["main"])
    z = res["counts_all_stages"]["ig_zero_stage_share"]
    L.append("share of stages with ig = 0 for every candidate: " + ", ".join(f"{a} {v['share']:.2f}" for a, v in z.items()))
    L.append("objects per member: " + ", ".join(f"{a} {v['mean_per_member']:.1f}" for a, v in res["counts_all_stages"]["objects_per_member"].items()))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stages", nargs="+", help="factorial_stages.jsonl of one or more passes")
    ap.add_argument("--left-out", help="the left-out list: read if it exists, else computed and written")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    res = summarise(load_rows(args.stages), left_out_path=args.left_out)
    Path(args.out).write_text(json.dumps(res, indent=1))
    print(format_text(res))


if __name__ == "__main__":
    main()
