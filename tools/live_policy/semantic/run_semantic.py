"""Driver of the pre-registered semantic test (PREREGISTRATION_SEMANTIC.md §8, §9, §10).

Per-member scores become row scores, cluster scores and cluster differences against each
comparator, then exact one-sided sign-flip p-values, 95% intervals, Holm over the family,
verdicts, the wrong-house gate, the thesis line and the detectable-difference table.

Row record (one dict per row and model; JSON-safe, all keys strings):
    row_id, cluster, scene, seed, arm, stage, round, is_gemini_row
    possible      {"L1": bool, "L2": bool, "L3": bool}      §8: can any hit occur on this row
    n_unobserved  int
    model         {member: {"L1","L2","L3": share or None, "counts": {...}, "extra": {...}}}
    comparators   {name: {member or draw key: {"L1","L2","L3": share or None}}}
                  member-paired: B3, B3L, B5, D (key = the model's member)
                  row-paired:    B1 (placebo draws), B4 (partner row's members), B2

The command line refuses to load any model output without the pre-registration hash, and
refuses Claude models until FREEZE.sha256 exists.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


def _sibling(name: str):
    pkg = __package__
    if pkg:
        return importlib.import_module(f"{pkg}.{name}")
    key = f"_semantic_sibling_{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, Path(__file__).with_name(f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


class _Lazy:
    def __init__(self, name: str):
        self._name = name
        self._mod = None

    def __getattr__(self, attr: str):
        if self._mod is None:
            self._mod = _sibling(self._name)
        return getattr(self._mod, attr)


stats = _sibling("stats")
score_levels = _sibling("score_levels")
baselines = _sibling("baselines")
extract_preds = _Lazy("extract_preds")
region_truth = _Lazy("region_truth")

HERE = Path(__file__).resolve().parent
PREREG_MD_PATH = HERE.parent / "PREREGISTRATION_SEMANTIC.md"
PREREG_HASH_PATH = HERE.parent / "PREREGISTRATION_SEMANTIC.sha256"
FREEZE_PATH = HERE / "FREEZE.sha256"
FRAME_PATH = HERE / "sample_frame.txt"

LEVELS = ("L1", "L2", "L3")
MEMBER_PAIRED = ("B3", "B3L", "B5", "D")          # one score per model member
ROW_PAIRED = ("B1", "B4", "B2")                   # the comparator's members average to a row score
HYPOTHESIS_COMPARATORS = {"L1": ("B3", "B1"), "L2": ("B3", "B1"), "L3": ("B5", "D", "B3L")}
REPORTED_COMPARATORS = {"L1": ("B2", "B4"), "L2": ("B2", "B4"), "L3": ()}
NAMED_COMPARATOR = {"L1": "B3", "L2": "B3", "L3": "D"}
DELTA = {"L1": 0.05, "L2": 0.05, "L3": 0.03}
ALPHA = 0.05
GATE_LEVELS = ("L1", "L2")
THESIS = {"holds": "The claim holds", "mixed": "Mixed", "fails": "The claim fails", "inconclusive": "Inconclusive"}


# ------------------------------------------------------------------------------- averaging

def _mean(values: Iterable[Optional[float]]) -> Optional[float]:
    vals = [float(v) for v in values if v is not None]
    return math.fsum(vals) / len(vals) if vals else None


def _scores(entries: Mapping[str, Mapping[str, Any]], level: str) -> Dict[str, float]:
    return {str(k): v[level] for k, v in entries.items() if v.get(level) is not None}


def model_row_score(record: Mapping[str, Any], level: str) -> Optional[float]:
    """§8: a row's score is the mean over its members that have one."""
    return _mean(_scores(record["model"], level).values())


def row_contrast(record: Mapping[str, Any], comparator: str, level: str) -> Optional[float]:
    """The row's difference (model minus comparator), by the pairing of §9, or None if the row has
    no score on both sides. Member-paired: the mean over members with both scores of the member's
    difference. Row-paired: the model's row score minus the comparator's row score."""
    mine = _scores(record["model"], level)
    theirs = _scores(record.get("comparators", {}).get(comparator, {}), level)
    if comparator in MEMBER_PAIRED:
        shared = [k for k in mine if k in theirs]
        return _mean(mine[k] - theirs[k] for k in shared)
    if comparator in ROW_PAIRED:
        a, b = _mean(mine.values()), _mean(theirs.values())
        return None if a is None or b is None else a - b
    raise ValueError(f"unknown comparator {comparator!r}")


def _cluster_values(pairs: Sequence[Tuple[str, float]]) -> Dict[str, float]:
    """Mean over a cluster's rows, for each cluster that has a row."""
    if not pairs:
        return {}
    ids, means = stats.cluster_means([v for _, v in pairs], [c for c, _ in pairs])
    return {c: float(m) for c, m in zip(ids, means)}


def _test_entry(cluster_d: Dict[str, float], n_rows: int, with_test: bool = True) -> Dict[str, Any]:
    d = [cluster_d[c] for c in sorted(cluster_d)]
    entry: Dict[str, Any] = {"n_clusters": len(d), "n_rows": n_rows, "clusters": dict(sorted(cluster_d.items())),
                             "mean_diff": None, "p": None, "ci": None}
    if d:
        entry["mean_diff"] = float(sum(d) / len(d))
        if with_test:
            entry["p"] = stats.sign_flip_test(d, "greater").p
            entry["ci"] = tuple(stats.sign_flip_ci(d, 0.95, "two-sided"))
    return entry


def analyse(per_row: Sequence[Mapping[str, Any]], model: str, levels: Sequence[str] = LEVELS) -> Dict[str, Any]:
    """§8 and §10 for one model.

    Returns {"model", "levels": {L: {"n_rows", "n_rows_impossible", "model_cluster_scores",
    "comparators": {name: {"n_clusters","n_rows","clusters","mean_diff","p","ci"}}}}}.
    p is the exact one-sided (model above comparator) sign-flip p over clusters; ci the 95%
    two-sided interval; both None when no cluster has the contrast. B4 gets no p or interval here
    (its pairs are dependent): it gets "pairs" for the wrong-house gate of `family`.
    """
    out: Dict[str, Any] = {"model": model, "levels": {}}
    cluster_pair = {r["cluster"]: f"s{r['seed']}_{r['arm']}" for r in per_row}
    for lv in levels:
        rows = [r for r in per_row if r["possible"][lv]]
        entry: Dict[str, Any] = {
            "n_rows": len(per_row), "n_rows_impossible": len(per_row) - len(rows),
            "model_cluster_scores": _cluster_values([(r["cluster"], s) for r in rows
                                                     if (s := model_row_score(r, lv)) is not None]),
            "comparators": {},
        }
        for name in HYPOTHESIS_COMPARATORS[lv] + REPORTED_COMPARATORS[lv]:
            diffs = [(r["cluster"], d) for r in rows if (d := row_contrast(r, name, lv)) is not None]
            cl = _cluster_values(diffs)
            comp = _test_entry(cl, len(diffs), with_test=name != "B4")
            if name == "B4":
                by_pair: Dict[str, List[float]] = {}
                for c, d in cl.items():
                    by_pair.setdefault(cluster_pair[c], []).append(d)
                comp["pairs"] = {k: float(sum(v) / len(v)) for k, v in sorted(by_pair.items())}
            entry["comparators"][name] = comp
        out["levels"][lv] = entry
    return out


# ------------------------------------------------------------------------------------ family

def wrong_house_gate(pairs: Mapping[str, float]) -> Dict[str, Any]:
    """§10: exact one-sided sign-flip over the seed x arm pairs, p < 0.05, not adjusted."""
    vals = [pairs[k] for k in sorted(pairs)]
    if not vals:
        return {"n_pairs": 0, "p": None, "pass": False}
    p = stats.sign_flip_test(vals, "greater").p
    return {"n_pairs": len(vals), "p": p, "pass": bool(p < ALPHA), "mean_diff": float(sum(vals) / len(vals))}


def family(results_by_model: Mapping[str, Mapping[str, Any]], claude_models: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """§10: hypothesis p-values (largest over comparators), Holm over all (model, level) pairs given,
    the verdicts, the wrong-house gate and the thesis line.

    A hypothesis whose comparator has no p (no shared cluster) takes p = 1 for that comparator and
    lists it under "missing"; it can then not be Supported. A missing interval for the named
    comparator counts as unbounded, so the verdict cannot be Rejected.
    The thesis rules apply in table order: holds, mixed, fails, inconclusive. It is None when no
    Claude model is present (§16).
    """
    raw: Dict[str, float] = {}
    meta: Dict[str, Dict[str, Any]] = {}
    for model, res in results_by_model.items():
        for lv, ent in res["levels"].items():
            ps, missing = [], []
            for c in HYPOTHESIS_COMPARATORS[lv]:
                p = ent["comparators"].get(c, {}).get("p")
                if p is None:
                    missing.append(c)
                    p = 1.0
                ps.append(p)
            key = f"{model}|{lv}"
            raw[key] = stats.intersection_union_p(ps)
            meta[key] = {"model": model, "level": lv, "missing": missing}
    adjusted = stats.holm(raw) if raw else {}
    hyp: Dict[str, Any] = {}
    for key, m in meta.items():
        ent = results_by_model[m["model"]]["levels"][m["level"]]
        named = NAMED_COMPARATOR[m["level"]]
        ci = ent["comparators"].get(named, {}).get("ci")
        upper = ci[1] if ci is not None else math.inf
        hyp[key] = {**m, "p": raw[key], "p_holm": adjusted[key], "named": named,
                    "ci_upper_named": None if upper == math.inf else upper,
                    "delta": DELTA[m["level"]],
                    "verdict": stats.verdict(adjusted[key], upper, DELTA[m["level"]], ALPHA)}
    gates: Dict[str, Any] = {}
    for model, res in results_by_model.items():
        for lv in GATE_LEVELS:
            if lv in res["levels"]:
                b4 = res["levels"][lv]["comparators"].get("B4", {})
                gates[f"{model}|{lv}"] = wrong_house_gate(b4.get("pairs", {}))
    cm = list(claude_models) if claude_models is not None else [m for m in results_by_model if m.startswith("claude")]
    thesis = None
    if cm:
        def v(m, lv):
            return hyp.get(f"{m}|{lv}", {}).get("verdict")
        if any(v(m, "L3") == "Supported" for m in cm):
            thesis = THESIS["holds"]
        elif any(v(m, lv) == "Supported" and gates.get(f"{m}|{lv}", {}).get("pass") for m in cm for lv in GATE_LEVELS):
            thesis = THESIS["mixed"]
        elif all(v(m, "L2") == "Rejected" and v(m, "L3") == "Rejected" for m in cm):
            thesis = THESIS["fails"]
        else:
            thesis = THESIS["inconclusive"]
    return {"hypotheses": hyp, "wrong_house_gate": gates, "thesis": thesis, "claude_models": cm,
            "m_hypotheses": len(raw), "alpha": ALPHA}


# ----------------------------------------------------------------------------------- MDD

def _member_diff_rows(records: Sequence[Mapping[str, Any]], level: str, a: Callable, b: Callable) -> List[Tuple[str, float]]:
    out = []
    for r in records:
        if not r["possible"][level]:
            continue
        sa, sb = a(r), b(r)
        shared = [k for k in sa if k in sb]
        d = _mean(sa[k] - sb[k] for k in shared)
        if d is not None:
            out.append((r["cluster"], d))
    return out


def mdd_table(placebo_records: Sequence[Mapping[str, Any]], alpha: float = ALPHA, power: float = 0.8,
              m_tests: int = 6, levels: Sequence[str] = LEVELS) -> Dict[str, Any]:
    """§10: for each level, SD across clusters of a contrast between two comparators, on the
    placebo's own members (records built with the placebo draws as the model):
    B1 - B3 at L1 and L2 (the placebo's score minus B3 for the same member), B5 - D at L3.
    MDD = (z(1 - alpha/m) + z(power)) * SD / sqrt(n). Also the interval of the contrast and its
    half-width, which shows whether "Rejected" is within reach."""
    out: Dict[str, Any] = {}
    for lv in levels:
        if lv in ("L1", "L2"):
            label = "B1-B3"
            pairs = _member_diff_rows(placebo_records, lv, lambda r: _scores(r["model"], lv),
                                      lambda r: _scores(r["comparators"].get("B3", {}), lv))
        else:
            label = "B5-D"
            pairs = _member_diff_rows(placebo_records, lv, lambda r: _scores(r["comparators"].get("B5", {}), lv),
                                      lambda r: _scores(r["comparators"].get("D", {}), lv))
        cl = _cluster_values(pairs)
        d = [cl[c] for c in sorted(cl)]
        entry: Dict[str, Any] = {"contrast": label, "n_clusters": len(d), "sd": None, "mdd": None,
                                 "ci": None, "half_width": None, "mean": float(sum(d) / len(d)) if d else None}
        if len(d) >= 2:
            sd = statistics.stdev(d)
            entry["sd"] = sd
            entry["mdd"] = stats.detectable_difference(sd, len(d), alpha=alpha, power=power, m_tests=m_tests)
            lo, hi = stats.sign_flip_ci(d, 0.95, "two-sided")
            entry["ci"] = (lo, hi)
            entry["half_width"] = (hi - lo) / 2.0 if math.isfinite(lo) and math.isfinite(hi) else None
        out[lv] = entry
    return out


# -------------------------------------------------------------------------- row records

def build_record(row, truth, state, members: Sequence, prior, placebo_members: Optional[Sequence] = None,
                 b4: Optional[Mapping[str, Mapping[str, Optional[float]]]] = None) -> Dict[str, Any]:
    """Score one row for one model: its members, and every comparator but B4 (passed in)."""
    sl, bl = score_levels, baselines
    rec: Dict[str, Any] = {
        "row_id": row.row_id, "cluster": row.cluster, "scene": row.scene, "seed": row.seed, "arm": row.arm,
        "stage": row.stage, "round": row.round, "is_gemini_row": row.is_gemini_row,
        "possible": {lv: bool(sl.possible(lv, truth, state)) for lv in LEVELS},
        "n_unobserved": len(state.unobserved),
        "model": {}, "comparators": {"B3": {}, "B3L": {}, "B5": {}, "D": {}, "B1": {}, "B2": {}, "B4": {}},
    }
    comp = rec["comparators"]
    for m in members:
        k = str(m.member)
        ms = sl.score_member(m, truth, state, row.observed)
        rec["model"][k] = {**sl.member_rates(ms), "counts": {
            "l1_hits": ms.l1_hits, "l1_n": ms.l1_n, "l2_hits": ms.l2_hits, "l2_n": ms.l2_n,
            "l3_hits": ms.l3_hits, "l3_n": ms.l3_n}, "extra": dict(ms.extra)}
        comp["B3"][k] = sl.member_rates(sl.score_member(bl.b3_member(prior, row.observed, m), truth, state, row.observed))
        comp["B3L"][k] = sl.member_rates(sl.score_member(bl.b3l_member(prior, row.observed, m), truth, state, row.observed))
        comp["B5"][k] = {"L3": bl.b5_l3(m, truth, state, seed=bl.stable_seed(row.row_id, m.member, "B5"))}
        comp["D"][k] = {"L3": bl.d_l3(m, truth, state, seed=bl.stable_seed(row.row_id, m.member, "D"))}
    for pm in placebo_members or ():
        comp["B1"][str(pm.member)] = sl.member_rates(sl.score_member(pm, truth, state, row.observed))
    comp["B2"]["0"] = sl.member_rates(sl.score_member(bl.b2_member(row.observed), truth, state, row.observed))
    for k, v in (b4 or {}).items():
        comp["B4"][str(k)] = dict(v)
    return rec


# ---------------------------------------------------------------------------- command line

class Refused(SystemExit):
    """The command line refuses to run."""


def _first_field(path: Path) -> str:
    text = Path(path).read_text().strip()
    if not text:
        raise Refused(f"refused: {path} is empty")
    return text.split()[0].lower()


def is_claude(model: str) -> bool:
    return model.startswith("claude")


def check_guards(models: Sequence[str], prereg_sha256: Optional[str]) -> None:
    """Called before any model output is read. Raises Refused unless the hash given equals the first
    field of PREREGISTRATION_SEMANTIC.sha256, and, for a Claude model, FREEZE.sha256 exists."""
    if not prereg_sha256:
        raise Refused("refused: --prereg-sha256 is required before any model output is loaded")
    if not Path(PREREG_HASH_PATH).is_file():
        raise Refused(f"refused: {PREREG_HASH_PATH} does not exist; the pre-registration is not hashed")
    if prereg_sha256.strip().lower() != _first_field(PREREG_HASH_PATH):
        raise Refused("refused: --prereg-sha256 does not equal the registered hash")
    if any(is_claude(m) for m in models) and not Path(FREEZE_PATH).is_file():
        raise Refused(f"refused: {FREEZE_PATH} does not exist; Claude output cannot be scored before the freeze")


def read_frame(path: Path = FRAME_PATH) -> List[Tuple[str, int]]:
    out = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            parts = line.split()
            out.append((parts[0], int(parts[2])))
    return out


def finished_rounds(rows: Sequence, members_by_model: Mapping[str, Mapping[str, Sequence]]) -> List[int]:
    """§10: the rounds in which every model holds at least one member on every row of the round."""
    rounds = sorted({r.round for r in rows})
    return [rd for rd in rounds
            if all(members_by_model[m].get(r.row_id) for m in members_by_model for r in rows if r.round == rd)]


def _jsonable(x: Any) -> Any:
    if isinstance(x, Mapping):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set, frozenset)):
        return [_jsonable(v) for v in (sorted(x) if isinstance(x, (set, frozenset)) else x)]
    if isinstance(x, float):
        if math.isnan(x):
            return "nan"
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
        return x
    if hasattr(x, "item") and not isinstance(x, (str, bytes)):  # numpy scalar
        return _jsonable(x.item())
    return x


def observed_path(row) -> Path:
    """The row's track-0 observed YAML, habitat_scene_graph_original_graph0.yaml: the file
    live_policy's no_llm_completions loaded as `observed` (the path _preprocess_dsg returns)."""
    run, stage, _rnd = extract_preds._frame_index(str(extract_preds.FRAME_PATH))[row.row_id]
    return Path(extract_preds.RUNS_ROOT) / run / "stages" / str(stage) / "habitat_scene_graph_original_graph0.yaml"


def _observed_raw(row) -> Dict[str, Any]:
    import yaml
    with open(observed_path(row)) as f:
        return yaml.safe_load(f) or {"nodes": [], "edges": []}


def run(models: Sequence[str], frame: Path, rounds: Optional[Sequence[int]] = None) -> Dict[str, Any]:
    """Score every model on the frame. Called only after the guards."""
    bl = baselines
    frame_rows = read_frame(frame)
    rows = [extract_preds.load_row(rid) for rid, _ in frame_rows]
    truths = {s: region_truth.load_scene_truth(s) for s in sorted({r.scene for r in rows})}
    states = {r.row_id: region_truth.stage_state(truths[r.scene], r) for r in rows}
    prior = bl.Prior()
    placebo_fn = bl.make_placebo_fn(_observed_raw, bl.reduce_via_extract_preds(extract_preds))
    placebo = {r.row_id: bl.b1_members(r, placebo_fn) for r in rows}
    members = {m: {r.row_id: list(extract_preds.members_for(r, m)) for r in rows} for m in models}

    def records_for(model_name: str, by_row: Mapping[str, Sequence], keep: Callable[[Any], bool]) -> List[Dict[str, Any]]:
        recs = []
        for r in rows:
            if not keep(r):
                continue
            b4 = {} if model_name == "placebo" else bl.b4_scores(r, rows, by_row, truths[r.scene], states[r.row_id])
            recs.append(build_record(r, truths[r.scene], states[r.row_id], by_row.get(r.row_id, ()), prior,
                                     placebo_members=placebo[r.row_id], b4=b4))
        return recs

    claude = [m for m in models if is_claude(m)]
    done = finished_rounds(rows, {m: members[m] for m in claude}) if claude else []
    use = set(rounds) if rounds is not None else set(done)
    out: Dict[str, Any] = {"models": {}, "finished_rounds": done, "rounds_used_for_family": sorted(use)}
    family_results = {}
    for m in models:
        recs = records_for(m, members[m], lambda r: True)
        entry = {"role": "confirmatory" if is_claude(m) else "exploratory", "records": recs,
                 "analysis_all_rows": analyse(recs, m)}
        if is_claude(m):
            sub = [r for r in recs if r["round"] in use]
            entry["analysis"] = analyse(sub, m)
            family_results[m] = entry["analysis"]
        out["models"][m] = entry
    placebo_recs = records_for("placebo", placebo, lambda r: True)
    out["placebo_records"] = placebo_recs
    out["mdd"] = mdd_table(placebo_recs)
    out["family"] = family(family_results, claude) if family_results else None
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--models", required=True, help="comma list: deepseek,gemini,claude-opus-5-5,claude-haiku-5-5")
    ap.add_argument("--out", required=True)
    ap.add_argument("--frame", default=str(FRAME_PATH))
    ap.add_argument("--rounds", default="auto", help="'auto' (rounds both Claude models finished) or e.g. 1,2")
    ap.add_argument("--prereg-sha256", default=None, help="must equal the first field of PREREGISTRATION_SEMANTIC.sha256")
    args = ap.parse_args(argv)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    check_guards(models, args.prereg_sha256)          # before any model output is touched
    rounds = None if args.rounds == "auto" else [int(x) for x in args.rounds.split(",")]
    result = run(models, Path(args.frame), rounds)
    result["prereg_sha256"] = args.prereg_sha256.strip().lower()
    result["prereg_file_sha256"] = hashlib.sha256(Path(PREREG_MD_PATH).read_bytes()).hexdigest() if Path(PREREG_MD_PATH).is_file() else None
    result["freeze_present"] = Path(FREEZE_PATH).is_file()
    Path(args.out).write_text(json.dumps(_jsonable(result), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
