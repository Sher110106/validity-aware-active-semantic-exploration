"""Four exploratory readouts from the saved semantic and M2 files (written 2026-11-19).

    .venv_offline/bin/python tools/live_policy/review_readouts.py

1. ceiling         what each comparator itself scores, and the best p a perfect model could get
2. common_rows     every source on the 8 rows that hold Gemini guesses
3. room_test_runs  the paper's room test at run level, with an exact permutation test
4. all_true        why M2's all-true arm (F0) does not gain

Readouts 1 to 3 go to results_semantic_1113/exploratory_1119/, readout 4 to
results_m2_1113/exploratory_1119/, each as .md and .json.

The semantic scorer is frozen. Nothing here edits it. Where a rule already lives in
semantic/run_semantic.py or semantic/stats.py (row score, member pairing, cluster mean,
sign-flip test, Holm), this file calls that function.
"""
from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import math
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
SEMANTIC_DIR = HERE / "semantic"
RESULTS_SEM = HERE / "results_semantic_1113"
RESULTS_M2 = HERE / "results_m2_1113"
OUT_SEM = RESULTS_SEM / "exploratory_1119"
OUT_M2 = RESULTS_M2 / "exploratory_1119"

DATE = "2026-11-19"
BANNER = (f"> **Exploratory.** Written {DATE} after every result was seen. No verdict rests on it. "
          "See `DEVIATIONS_NOVEMBER.md`.")
BANNER_TEXT = (f"Exploratory; written {DATE} after every result was seen; no verdict rests on it; "
               "see DEVIATIONS_NOVEMBER.md")

LEVELS = ("L1", "L2", "L3")
CLAUDE = ("claude-opus-5-5", "claude-haiku-5-5")
GEMINI_SOURCES = ("gemini", "claude-opus-5-5", "claude-haiku-5-5", "deepseek", "placebo")
TOL = 1e-9
ONE = 1.0 - 1e-12


class ReadoutCheckError(RuntimeError):
    """A number rebuilt here does not match the saved result. Nothing is written."""


# ------------------------------------------------------------------------- the frozen scorer, loaded

def _load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses look the module up by name
    spec.loader.exec_module(mod)
    return mod


_RS = None


def scorer():
    """semantic/run_semantic.py, loaded by path (tools/live_policy also holds a live_policy.py)."""
    global _RS
    if _RS is None:
        _RS = _load_by_path("review_readouts_run_semantic", SEMANTIC_DIR / "run_semantic.py")
    return _RS


def _ps(x: Any) -> Any:
    """JSON-safe copy."""
    if isinstance(x, dict):
        return {str(k): _ps(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_ps(v) for v in x]
    if isinstance(x, (np.floating,)):
        return _ps(float(x))
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, Fraction):
        return float(x)
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def _pct(x: Optional[float], digits: int = 1) -> str:
    return "n/a" if x is None else f"{100.0 * x:.{digits}f}%"


def _pts(x: Optional[float], digits: int = 1) -> str:
    return "n/a" if x is None else f"{100.0 * x:+.{digits}f}"


def _table(header: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def _write(out_dir: Path, name: str, doc: Mapping[str, Any], md: str) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jp, mp = out_dir / f"{name}.json", out_dir / f"{name}.md"
    body = dict(doc)
    body["banner"] = BANNER_TEXT
    jp.write_text(json.dumps(_ps(body), indent=1, sort_keys=False) + "\n")
    mp.write_text(BANNER + "\n\n" + md.rstrip() + "\n")
    return [mp, jp]


# ============================================================================== 1. ceiling

def paired_row_scores(record: Mapping[str, Any], comparator: str, level: str) -> Optional[Tuple[float, float]]:
    """(model's row score, comparator's row score) over the members or draws that pair, by the rule of
    run_semantic.row_contrast; None if the row has no score on both sides. Their difference equals
    row_contrast, which is checked."""
    rs = scorer()
    mine = rs._scores(record["model"], level)
    theirs = rs._scores(record.get("comparators", {}).get(comparator, {}), level)
    if comparator in rs.MEMBER_PAIRED:
        shared = [k for k in mine if k in theirs]
        a, b = rs._mean(mine[k] for k in shared), rs._mean(theirs[k] for k in shared)
    elif comparator in rs.ROW_PAIRED:
        a, b = rs._mean(mine.values()), rs._mean(theirs.values())
    else:
        raise ValueError(f"unknown comparator {comparator!r}")
    if a is None or b is None:
        return None
    ref = rs.row_contrast(record, comparator, level)
    if ref is None or abs((a - b) - ref) > 1e-12:
        raise ReadoutCheckError(f"row {record.get('row_id')} {comparator} {level}: paired scores disagree with row_contrast")
    return a, b


def perfect_model_p(comp_clusters: Mapping[str, float]) -> Dict[str, Any]:
    """A model scoring 1.0 in every member gives d_c = 1 - comparator_c in each cluster. Its one-sided
    sign-flip p-value is the smallest the test can return on these clusters; Holm for six tests is taken
    with that test ranked first and the other five at p = 1 (the best case), so it is min(1, 6p)."""
    rs = scorer()
    d = [1.0 - comp_clusters[c] for c in sorted(comp_clusters)]
    res = rs.stats.sign_flip_test(d, "greater")
    holm = rs.stats.holm({"this": res.p, **{f"other{i}": 1.0 for i in range(5)}})["this"]
    return {"n_clusters": res.n, "n_zero_clusters": int(sum(1 for v in d if abs(v) < 1e-12)),
            "p_min": res.p, "p_min_holm6": holm, "can_reach_alpha": bool(holm < rs.ALPHA)}


def comparator_ceiling(records: Sequence[Mapping[str, Any]], comparator: str, level: str,
                       rounds: Optional[Sequence[int]] = None) -> Dict[str, Any]:
    rs = scorer()
    rows = [r for r in records if (rounds is None or r["round"] in rounds) and r["possible"][level]]
    paired = [(r, ab) for r in rows if (ab := paired_row_scores(r, comparator, level)) is not None]
    model_cl = rs._cluster_values([(r["cluster"], ab[0]) for r, ab in paired])
    comp_cl = rs._cluster_values([(r["cluster"], ab[1]) for r, ab in paired])
    diff_cl = rs._cluster_values([(r["cluster"], ab[0] - ab[1]) for r, ab in paired])
    n = len(comp_cl)
    mean = lambda d: (math.fsum(d.values()) / len(d)) if d else None  # noqa: E731
    out: Dict[str, Any] = {
        "n_rows": len(paired), "n_clusters": n,
        "model_score": mean(model_cl), "comparator_score": mean(comp_cl),
        "mean_diff": mean(diff_cl),
        "comparator_rows_at_1": sum(1 for _, ab in paired if ab[1] >= ONE),
        "comparator_clusters_at_1": sum(1 for v in comp_cl.values() if v >= ONE),
        "max_gain_perfect_model": None if not n else 1.0 - mean(comp_cl),
        "clusters": {c: {"model": model_cl[c], "comparator": comp_cl[c]} for c in sorted(comp_cl)},
    }
    if comparator == "B3" and level in ("L1", "L2") and n:
        out["perfect_model"] = perfect_model_p(comp_cl)
    return out


def check_against_results(model: str, level: str, comparator: str, mine: Mapping[str, Any],
                          results: Mapping[str, Any]) -> Dict[str, Any]:
    """The model-minus-comparator mean, the cluster count and the row count must equal results.json."""
    try:
        saved = results["models"][model]["analysis"]["levels"][level]["comparators"][comparator]
    except KeyError as e:
        raise ReadoutCheckError(f"results.json has no {model} {level} {comparator}: {e}")
    sm = saved.get("mean_diff")
    ok_mean = (sm is None and mine["mean_diff"] is None) or (
        sm is not None and mine["mean_diff"] is not None and abs(sm - mine["mean_diff"]) <= TOL)
    ok = ok_mean and saved.get("n_clusters") == mine["n_clusters"] and saved.get("n_rows") == mine["n_rows"]
    if not ok:
        raise ReadoutCheckError(
            f"{model} {level} {comparator}: rebuilt mean_diff={mine['mean_diff']} n_clusters={mine['n_clusters']} "
            f"n_rows={mine['n_rows']}, results.json has mean_diff={sm} n_clusters={saved.get('n_clusters')} "
            f"n_rows={saved.get('n_rows')}")
    return {"mean_diff_saved": sm, "n_clusters_saved": saved.get("n_clusters"), "n_rows_saved": saved.get("n_rows"),
            "p_saved": saved.get("p"), "matches": True}


def ceiling(records_by_model: Mapping[str, Sequence[Mapping[str, Any]]], results: Mapping[str, Any],
            rounds: Optional[Sequence[int]] = None) -> Dict[str, Any]:
    rs = scorer()
    if rounds is None:
        rounds = results.get("rounds_used")
    out: Dict[str, Any] = {"readout": "ceiling", "rounds_used": list(rounds) if rounds is not None else None, "models": {}}
    for model, recs in records_by_model.items():
        out["models"][model] = {}
        for lv in LEVELS:
            ent: Dict[str, Any] = {"comparators": {}}
            for comp in rs.HYPOTHESIS_COMPARATORS[lv]:
                got = comparator_ceiling(recs, comp, lv, rounds)
                got["check"] = check_against_results(model, lv, comp, got, results)
                ent["comparators"][comp] = got
            out["models"][model][lv] = ent
    return out


def ceiling_md(doc: Mapping[str, Any]) -> str:
    L = ["# Readout 1: what each comparator itself scores", "",
         "Each comparator's own score and the model's, on the registered analysis rows "
         f"(rounds {doc['rounds_used']}), built as section 8 says: member, then row, then cluster means, "
         "on the rows where both have a score. Scores are in %. \"Max gain\" is what a model that scores 1.0 in "
         "every member could show over the comparator (100 minus the comparator's score). "
         "Every model-minus-comparator mean was checked against `claude/results.json` and matches.", ""]
    rows = []
    for model, lvls in doc["models"].items():
        for lv, ent in lvls.items():
            for comp, c in ent["comparators"].items():
                rows.append([model, lv, comp, c["n_rows"], c["n_clusters"], _pct(c["model_score"]), _pct(c["comparator_score"]),
                             _pts(c["mean_diff"]), c["comparator_rows_at_1"], c["comparator_clusters_at_1"],
                             _pct(c["max_gain_perfect_model"])])
    L.append(_table(["Model", "Level", "Comparator", "Rows", "Clusters", "Model score", "Comparator score",
                     "Diff (points)", "Rows comparator = 1.0", "Clusters comparator = 1.0", "Max gain"], rows))
    L += ["", "## Best p a perfect model could get against B3", "",
          "A model with 1.0 in every member, on the clusters of each B3 contrast. The one-sided exact sign-flip test "
          "(`semantic/stats.py`) on d = 1 minus the comparator's cluster score. This is the smallest p the test could "
          "have returned. Holm for six tests assumes that test ranks first and the other five have p = 1, so it is "
          "min(1, 6p). The registered p is the saved one for the model's real score.", ""]
    rows = []
    for model, lvls in doc["models"].items():
        for lv in ("L1", "L2"):
            c = lvls[lv]["comparators"]["B3"]
            pm = c.get("perfect_model")
            if pm:
                rows.append([model, lv, pm["n_clusters"], pm["n_zero_clusters"], f"{pm['p_min']:.6g}",
                             f"{pm['p_min_holm6']:.6g}", "yes" if pm["can_reach_alpha"] else "no", f"{c['check']['p_saved']:.4g}"])
    L.append(_table(["Model", "Level", "Clusters", "Clusters with d = 0", "Smallest p", "After Holm (6)",
                     "Could pass 0.05", "Saved p (real model)"], rows))
    L += ["", "Clusters with d = 0 are those where B3 itself scores 1.0. They stay in the test and raise the smallest p "
          "to 2^z / 2^n."]
    return "\n".join(L)


# ======================================================================= 2. common rows

def common_rows(records_by_source: Mapping[str, Sequence[Mapping[str, Any]]], anchor: str = "gemini") -> Dict[str, Any]:
    """Rows where the anchor source (Gemini) has members, and every source has a score, per level."""
    rs = scorer()
    sources = list(records_by_source)
    by_src = {s: {r["row_id"]: r for r in recs} for s, recs in records_by_source.items()}
    anchor_rows = [rid for rid, r in by_src[anchor].items() if r["model"]]
    out: Dict[str, Any] = {"readout": "common_rows", "anchor": anchor, "sources": sources,
                           "anchor_rows": sorted(anchor_rows),
                           "anchor_rounds": sorted({by_src[anchor][rid]["round"] for rid in anchor_rows}), "levels": {}}
    for lv in LEVELS:
        keep, score = [], {s: {} for s in sources}
        for rid in sorted(anchor_rows):
            if not all(rid in by_src[s] and by_src[s][rid]["possible"][lv] for s in sources):
                continue
            row_scores = {s: rs.model_row_score(by_src[s][rid], lv) for s in sources}
            if any(v is None for v in row_scores.values()):
                continue
            keep.append(rid)
            for s in sources:
                score[s][rid] = row_scores[s]
        ent: Dict[str, Any] = {"n_rows": len(keep), "rows": keep}
        ent["mean_row_score"] = {s: (math.fsum(score[s].values()) / len(keep) if keep else None) for s in sources}
        ent["anchor_vs"] = {}
        for s in sources:
            if s == anchor:
                continue
            a = sum(1 for rid in keep if score[anchor][rid] > score[s][rid] + 1e-12)
            t = sum(1 for rid in keep if abs(score[anchor][rid] - score[s][rid]) <= 1e-12)
            ent["anchor_vs"][s] = {"above": a, "tie": t, "below": len(keep) - a - t}
        b3 = []
        members = 0
        for rid in keep:
            ab = paired_row_scores(by_src[anchor][rid], "B3", lv)
            if ab is not None:
                b3.append(ab[1])
            members += len(rs._scores(by_src[anchor][rid]["model"], lv))
        ent["b3_score_anchor_members"] = math.fsum(b3) / len(b3) if b3 else None
        ent["b3_rows"] = len(b3)
        ent["anchor_members"] = members
        ent["clusters"] = sorted({by_src[anchor][rid]["cluster"] for rid in keep})
        ent["n_clusters"] = len(ent["clusters"])
        out["levels"][lv] = ent
    return out


def common_rows_md(doc: Mapping[str, Any]) -> str:
    a = doc["anchor"]
    L = ["# Readout 2: every source on the rows that hold Gemini guesses", "",
         f"Rows: the {len(doc['anchor_rows'])} rows where {a} has members (round(s) {doc['anchor_rounds']}). "
         "Per level, only rows where all five sources have a row score count. A row score is the mean over a source's "
         "members that have a score (section 8). The mean below is over those rows, each row once. "
         "B3 is the other-house prior paired with Gemini's own members on those rows.", ""]
    srcs = doc["sources"]
    rows = []
    for lv, e in doc["levels"].items():
        rows.append([lv, e["n_rows"]] + [_pct(e["mean_row_score"][s]) for s in srcs] + [_pct(e["b3_score_anchor_members"]),
                     e["anchor_members"], e["n_clusters"]])
    L.append(_table(["Level", "Rows"] + srcs + ["B3 (Gemini's members)", "Gemini members", "Clusters"], rows))
    L += ["", f"Rows where {a} is above each other source (above / tie / below):", ""]
    others = [s for s in srcs if s != a]
    rows = [[lv] + [f"{e['anchor_vs'][s]['above']} / {e['anchor_vs'][s]['tie']} / {e['anchor_vs'][s]['below']}" for s in others]
            for lv, e in doc["levels"].items()]
    L.append(_table(["Level"] + others, rows))
    L += ["", "Rows used:"] + [f"- {lv}: " + (", ".join(e["rows"]) or "none") for lv, e in doc["levels"].items()]
    return "\n".join(L)


# ===================================================================== 3. room test at run level

ROOM_FIELDS = {
    "eight_member_stages": "predicted_stages_with_8_members_typed",
    "all_stages": "predicted_all_stages_typed",
}


def run_rows(live_runs: Sequence[Mapping[str, Any]], field: str) -> List[Dict[str, Any]]:
    out = []
    for r in live_runs:
        of = int(r["n_regions_unseen_at_stage0"])
        pred = len(r[field])
        out.append({"run": r["run"], "scene": r["scene"], "seed": r["seed"], "arm": r["arm"], "of": of, "predicted": pred,
                    "rate": (pred / of) if of else None, "n_stages_with_8_members": r.get("n_stages_with_8_members"),
                    "n_stages": r.get("n_stages")})
    return out


def pooled(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    pred, of = sum(r["predicted"] for r in rows), sum(r["of"] for r in rows)
    return {"runs": len(rows), "predicted": pred, "of": of, "rate": (pred / of) if of else None}


def permutation_test(rows: Sequence[Mapping[str, Any]], arm_a: str, arm_b: str) -> Dict[str, Any]:
    """Swap the arm labels a and b among the runs of each scene. Every relabeling is enumerated: within a
    scene with n runs of which k carry a, the C(n, k) ways to choose the a-runs; across scenes, their product.
    Statistic: pooled rate of a minus pooled rate of b. Two-sided p: share of relabelings with |statistic| at
    least the observed one (the observed labeling is one of them)."""
    scenes: Dict[str, List[Mapping[str, Any]]] = {}
    for r in rows:
        if r["arm"] in (arm_a, arm_b):
            scenes.setdefault(r["scene"], []).append(r)
    if not scenes:
        raise ValueError("no runs for these arms")
    for s, rs_ in scenes.items():
        if not any(r["arm"] == arm_a for r in rs_) and not any(r["arm"] == arm_b for r in rs_):
            raise ValueError(f"scene {s} holds neither arm")
    names = sorted(scenes)
    per_scene = []
    for s in names:
        rs_ = scenes[s]
        k = sum(1 for r in rs_ if r["arm"] == arm_a)
        per_scene.append((rs_, k, list(itertools.combinations(range(len(rs_)), k))))
    total_pred = sum(r["predicted"] for rs_, _, _ in per_scene for r in rs_)
    total_of = sum(r["of"] for rs_, _, _ in per_scene for r in rs_)

    def stat(choice: Sequence[Tuple[int, ...]]) -> Fraction:
        pa = oa = 0
        for (rs_, _, _), pick in zip(per_scene, choice):
            for i in pick:
                pa += rs_[i]["predicted"]
                oa += rs_[i]["of"]
        pb, ob = total_pred - pa, total_of - oa
        if oa == 0 or ob == 0:
            raise ValueError("an arm has no regions under this relabeling")
        return Fraction(pa, oa) - Fraction(pb, ob)

    observed_choice = [tuple(i for i, r in enumerate(rs_) if r["arm"] == arm_a) for rs_, _, _ in per_scene]
    obs = stat(observed_choice)
    n = hits = 0
    for choice in itertools.product(*[c for _, _, c in per_scene]):
        n += 1
        if abs(stat(choice)) >= abs(obs):
            hits += 1
    sizes = {s: {"runs": len(rs_), arm_a: k, arm_b: len(rs_) - k, "relabelings": len(c)} for s, (rs_, k, c) in zip(names, per_scene)}
    return {"arm_a": arm_a, "arm_b": arm_b, "observed_diff": float(obs), "relabelings": n, "as_extreme": hits,
            "p_two_sided": hits / n, "per_scene": sizes}


def room_test_runs(room_doc: Mapping[str, Any], arms: Sequence[str] = ("official", "filter_only"), control: str = "placebo") -> Dict[str, Any]:
    live = room_doc["live"]["runs"]
    out: Dict[str, Any] = {"readout": "room_test_runs", "n_runs": len(live),
                           "source": "results_semantic_1113/claude/room_test.json, live.runs[]",
                           "fields": {"regions that could be predicted": "n_regions_unseen_at_stage0",
                                      **{f"predicted before found, {k}": v for k, v in ROOM_FIELDS.items()}},
                           "rule": "type matched; at least 2 of 8 members put a new room of that type within 2.5 m of the "
                                   "region centre before the region is first seen (section 11)",
                           "views": {}}
    for view, field in ROOM_FIELDS.items():
        rows = run_rows(live, field)
        arms_present = sorted({r["arm"] for r in rows})
        v: Dict[str, Any] = {"field": field, "runs": rows,
                             "pooled": {a: pooled([r for r in rows if r["arm"] == a]) for a in arms_present}, "tests": {}}
        for a in arms:
            v["tests"][f"{a}_vs_{control}"] = permutation_test(rows, a, control)
        out["views"][view] = v
    return out


def room_test_runs_md(doc: Mapping[str, Any]) -> str:
    L = ["# Readout 3: the paper's room test at run level", "",
         f"**Source.** `{doc['source']}`. Its live part is the same in `exploratory/room_test.json` (checked). "
         "Per live run I read `n_regions_unseen_at_stage0` (rooms that could be predicted before found) and the length of the "
         "list in the field named below (rooms predicted before found, type matched).", "",
         f"**Rule.** {doc['rule']}. The first view, \"eight_member_stages\", is the section 11 rule: it counts only stages that hold "
         "all 8 members. The second, \"all_stages\", counts every stage that has members. Both use the type-matched lists; "
         "no field of the untyped count is used.", ""]
    for view, v in doc["views"].items():
        L += [f"## View `{view}`: field `{v['field']}`", ""]
        L.append(_table(["Run", "Scene", "Arm", "Could be", "Predicted", "Rate", "Stages with 8 members", "Stages"],
                        [[r["run"], r["scene"], r["arm"], r["of"], r["predicted"], _pct(r["rate"]),
                          r["n_stages_with_8_members"], r["n_stages"]] for r in v["runs"]]))
        L += ["", "Pooled rate per arm (sum of predicted over sum of could-be):", ""]
        L.append(_table(["Arm", "Runs", "Predicted", "Could be", "Rate"],
                        [[a, p["runs"], p["predicted"], p["of"], _pct(p["rate"])] for a, p in v["pooled"].items()]))
        L += ["", "Exact permutation test. Arm labels are swapped between runs within a scene; every relabeling is "
              "enumerated. Statistic: pooled rate of the arm minus pooled rate of placebo. Two-sided p.", ""]
        L.append(_table(["Test", "Observed difference (points)", "Relabelings", "As extreme or more", "p (two-sided)"],
                        [[k, _pts(t["observed_diff"]), t["relabelings"], t["as_extreme"], f"{t['p_two_sided']:.4f}"]
                         for k, t in v["tests"].items()]))
        L += ["", "Relabelings per scene: " + "; ".join(
            f"{k}: " + ", ".join(f"{s} {d['relabelings']}" for s, d in t["per_scene"].items()) for k, t in v["tests"].items()), ""]
    L += ["**Caution.** Official runs hold few 8-member stages (4 to 11 of 17 to 21) and filter_only runs fewer still (2 to 7 of 15 to 20); "
          "placebo runs hold all of them. The 8-member view gives those runs fewer stages in which to predict a room, so the arms "
          "do not have equal chances under that rule. Runs are the unit; seeds are not paired, as asked."]
    return "\n".join(L)


# ======================================================================= 4. the all-true arm

_SF = None


def _summarise_factorial():
    global _SF
    if _SF is None:
        _SF = _load_by_path("review_readouts_m2_summarise", HERE / "m2" / "summarise_factorial.py")
    return _SF


def all_true(rows: Sequence[Mapping[str, Any]], all_true_arm: str = "F0", no_guess_arm: str = "F6",
             bits_cap: float = 2.0) -> Dict[str, Any]:
    """rows: one dict per stage with arms -> {"ig": [per candidate]}, as in factorial_stages.jsonl."""
    rho = _summarise_factorial()._rho_copy
    max_by_arm: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        for arm, v in r["arms"].items():
            ig = np.asarray(v["ig"], float)
            i = int(np.argmax(ig))
            ent = max_by_arm.setdefault(arm, {"max_ig": -math.inf, "at": None, "stages": 0, "n_values": 0, "above_cap": 0})
            ent["stages"] += 1
            ent["n_values"] += int(ig.size)
            ent["above_cap"] += int(np.count_nonzero(ig > bits_cap + 1e-9))
            if ig[i] > ent["max_ig"]:
                ent["max_ig"], ent["at"] = float(ig[i]), {"run": r["run"], "stage": r["stage"], "candidate": i}
    rhos, undefined = [], []
    for r in rows:
        if all_true_arm in r["arms"] and no_guess_arm in r["arms"]:
            x = rho(r["arms"][all_true_arm]["ig"], r["arms"][no_guess_arm]["ig"])
            if x is None:
                undefined.append((r["run"], r["stage"]))
            else:
                rhos.append(x)
    ent = {"arms": max_by_arm, "bits_cap": bits_cap}
    for arm in (all_true_arm, no_guess_arm):
        a = max_by_arm.get(arm)
        ent[f"{arm}_exceeds_cap"] = None if a is None else bool(a["above_cap"] > 0)
    stages_with_both = sum(1 for r in rows if all_true_arm in r["arms"] and no_guess_arm in r["arms"])
    ent["spearman"] = {"pair": [all_true_arm, no_guess_arm], "score_column": "ig", "n_stages": len(rows),
                       "n_stages_with_both_arms": stages_with_both, "n_used": len(rhos), "n_undefined": len(undefined),
                       "undefined_stages": [list(u) for u in undefined],
                       "mean": (math.fsum(rhos) / len(rhos)) if rhos else None,
                       "median": float(np.median(rhos)) if rhos else None}
    return {"readout": "all_true", **ent}


def all_true_md(doc: Mapping[str, Any], sources: Optional[Mapping[str, str]] = None) -> str:
    sp = doc["spearman"]
    a, b = sp["pair"]
    L = ["# Readout 4: why the all-true arm does not gain", "",
         "**Layout read.** One line per stage in `factorial_stages.jsonl`: `arms[<arm>]['ig']` is a list of 300 values, one per "
         f"first-stage candidate. Arms: F1 oracle graphs, F5a/F5b placebo sets, F6 no guesses (the no-guess arm), F0 the all-true "
         "anchor, F-room, F3-deepseek/-haiku/-opus. `ig` is the members' disagreement about a candidate, read in bits "
         f"as the brief does. The cap tested is {doc['bits_cap']:.1f}.", ""]
    if sources:
        L.append("**Files.** " + "; ".join(f"{k}: `{v}`" for k, v in sources.items()) +
                 ". Pass 2's file holds only F3-haiku and F3-opus; F0 and F6 are in pass 1's, so both files were read "
                 "(merged by run and stage, as `summarise_factorial.load_rows` does).")
        L.append("")
    rows = []
    for arm, e in doc["arms"].items():
        rows.append([arm, e["stages"], f"{e['max_ig']:.4f}", f"{e['at']['run']} stage {e['at']['stage']} cand {e['at']['candidate']}",
                     e["above_cap"]])
    L.append(_table(["Arm", "Stages", "Largest ig (bits)", "Where", f"Values above {doc['bits_cap']:.1f}"], rows))
    L += ["", f"- {a} exceeds {doc['bits_cap']:.1f} bits: **{'yes' if doc[f'{a}_exceeds_cap'] else 'no'}**; "
              f"{b} exceeds it: **{'yes' if doc[f'{b}_exceeds_cap'] else 'no'}**. "
              f"Largest {a}: {doc['arms'][a]['max_ig']:.4f}; largest {b}: {doc['arms'][b]['max_ig']:.4f}.",
          f"- Spearman correlation of {a}'s `ig` with {b}'s `ig` across the candidates of a stage, mean over stages: "
          f"**{sp['mean']:+.4f}** (median {sp['median']:+.4f}) on **{sp['n_used']}** stages. "
          f"{sp['n_undefined']} of {sp['n_stages_with_both_arms']} stages have no defined correlation (a constant `ig` in one arm, "
          "as in `_rho_copy`) and are left out."]
    return "\n".join(L)


# ====================================================================================== the run

def _load_json(path: Path):
    with open(path) as f:
        return json.load(f)


def run_all(results_dir: Path = RESULTS_SEM, m2_dir: Path = RESULTS_M2, out_sem: Path = OUT_SEM, out_m2: Path = OUT_M2) -> Dict[str, Any]:
    results = _load_json(results_dir / "claude" / "results.json")
    recs = {m: _load_json(results_dir / "claude" / f"records_{m}.json")["records"] for m in CLAUDE}
    expl = {m: _load_json(results_dir / "exploratory" / f"records_{m}.json")["records"] for m in ("deepseek", "gemini", "placebo")}
    written: List[Path] = []

    doc1 = ceiling(recs, results)
    written += _write(out_sem, "ceiling", doc1, ceiling_md(doc1))

    by_source = {"gemini": expl["gemini"], **recs, "deepseek": expl["deepseek"], "placebo": expl["placebo"]}
    doc2 = common_rows({s: by_source[s] for s in GEMINI_SOURCES})
    written += _write(out_sem, "common_rows", doc2, common_rows_md(doc2))

    rt_claude = _load_json(results_dir / "claude" / "room_test.json")
    rt_expl = _load_json(results_dir / "exploratory" / "room_test.json")
    if rt_claude["live"] != rt_expl["live"]:
        raise ReadoutCheckError("the live room-test parts of claude/room_test.json and exploratory/room_test.json differ")
    doc3 = room_test_runs(rt_claude)
    written += _write(out_sem, "room_test_runs", doc3, room_test_runs_md(doc3))

    sf = _summarise_factorial()
    p1, p2 = m2_dir / "pass1" / "factorial_stages.jsonl", m2_dir / "pass2" / "factorial_stages.jsonl"
    rows = sf.load_verified_rows([str(p1), str(p2)])
    doc4 = all_true(rows)
    doc4["files"] = {"pass1": str(p1.relative_to(HERE.parent.parent)), "pass2": str(p2.relative_to(HERE.parent.parent))}
    written += _write(out_m2, "all_true", doc4, all_true_md(doc4, {"pass 1": "tools/live_policy/results_m2_1113/pass1/factorial_stages.jsonl",
                                                                     "pass 2": "tools/live_policy/results_m2_1113/pass2/factorial_stages.jsonl"}))
    return {"ceiling": doc1, "common_rows": doc2, "room_test_runs": doc3, "all_true": doc4, "written": written}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", type=Path, default=RESULTS_SEM)
    ap.add_argument("--m2", type=Path, default=RESULTS_M2)
    ap.add_argument("--out-semantic", type=Path, default=OUT_SEM)
    ap.add_argument("--out-m2", type=Path, default=OUT_M2)
    a = ap.parse_args(argv)
    res = run_all(a.results, a.m2, a.out_semantic, a.out_m2)
    for p in res["written"]:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
