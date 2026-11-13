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
import dataclasses
import hashlib
import importlib
import importlib.util
import json
import math
import os
import platform
import statistics
import sys
import time
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
validity = _Lazy("validity")
room_test = _Lazy("room_test")

HERE = Path(__file__).resolve().parent
PREREG_MD_PATH = HERE.parent / "PREREGISTRATION_SEMANTIC.md"
PREREG_HASH_PATH = HERE.parent / "PREREGISTRATION_SEMANTIC.sha256"
FREEZE_PATH = HERE / "FREEZE.sha256"
FRAME_PATH = HERE / "sample_frame.txt"

LEVELS = ("L1", "L2", "L3")
SENSITIVITY_B3 = ("B3_seen", "B3_size", "B3_seen_size")   # §9: the two sensitivity forms of B3 (and both at once)
MEMBER_PAIRED = ("B3", "B3L", "B5", "D") + SENSITIVITY_B3     # one score per model member
ROW_PAIRED = ("B1", "B4", "B2")                   # the comparator's members average to a row score
HYPOTHESIS_COMPARATORS = {"L1": ("B3", "B1"), "L2": ("B3", "B1"), "L3": ("B5", "D", "B3L")}
REPORTED_COMPARATORS = {"L1": ("B2", "B4") + SENSITIVITY_B3, "L2": ("B2", "B4") + SENSITIVITY_B3, "L3": ()}
REGISTERED_CLAUDE = ("claude-opus-5-5", "claude-haiku-5-5")
EXPLORATORY_MODELS = ("deepseek", "gemini", "placebo")
ALL_MODELS = EXPLORATORY_MODELS + REGISTERED_CLAUDE
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
    # §10: the family is {Opus, Haiku} x {L1, L2, L3}, six hypotheses, whatever was run. A registered
    # hypothesis that was not run has no p-value: it takes 1, so it cannot be Supported and the Holm
    # steps still count six.
    expected = [f"{m}|{lv}" for m in REGISTERED_CLAUDE for lv in LEVELS]
    padded = dict(raw)
    if any(k in raw for k in expected):
        for k in expected:
            padded.setdefault(k, 1.0)
    adjusted = stats.holm(padded) if padded else {}
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
        elif all(v(m, "L2") == "Rejected" and v(m, "L3") == "Rejected" for m in cm) and \
                (not set(cm) <= set(REGISTERED_CLAUDE) or set(cm) == set(REGISTERED_CLAUDE)):
            # "Every Claude model" is both registered models: one model alone cannot make the claim fail
            thesis = THESIS["fails"]
        else:
            thesis = THESIS["inconclusive"]
    return {"hypotheses": hyp, "wrong_house_gate": gates, "thesis": thesis, "claude_models": cm,
            "m_hypotheses": len(padded), "alpha": ALPHA}


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

META_KEYS = ("row_id", "cluster", "scene", "seed", "arm", "stage", "round", "is_gemini_row")


def _rates(ms) -> Dict[str, Any]:
    return score_levels.member_rates(ms)


def build_record(row, truth, state, members: Sequence, prior, placebo_members: Optional[Sequence] = None,
                 b4: Optional[Mapping[str, Mapping[str, Optional[float]]]] = None, *,
                 allowed: Optional[Iterable[str]] = None,
                 sens: Optional[Mapping[str, Mapping[str, Any]]] = None) -> Dict[str, Any]:
    """Score one row for one model: its members, and every comparator but B4 (passed in).

    `allowed` limits the labels B3 and B3L may use (the detector vocabulary, in that secondary line).
    `sens` maps a sensitivity name (B3_seen, ...) to the keyword arguments of baselines.b3_member."""
    sl, bl = score_levels, baselines
    rec: Dict[str, Any] = {
        "row_id": row.row_id, "cluster": row.cluster, "scene": row.scene, "seed": row.seed, "arm": row.arm,
        "stage": row.stage, "round": row.round, "is_gemini_row": row.is_gemini_row,
        "possible": {lv: bool(sl.possible(lv, truth, state)) for lv in LEVELS},
        "n_unobserved": len(state.unobserved),
        "model": {}, "comparators": {"B3": {}, "B3L": {}, "B5": {}, "D": {}, "B1": {}, "B2": {}, "B4": {}},
    }
    comp = rec["comparators"]
    for name in (sens or {}):
        comp[name] = {}
    for m in members:
        k = str(m.member)
        ms = sl.score_member(m, truth, state, row.observed)
        rec["model"][k] = {**_rates(ms), "counts": {
            "l1_hits": ms.l1_hits, "l1_n": ms.l1_n, "l2_hits": ms.l2_hits, "l2_n": ms.l2_n,
            "l3_hits": ms.l3_hits, "l3_n": ms.l3_n}, "extra": dict(ms.extra)}
        comp["B3"][k] = _rates(sl.score_member(bl.b3_member(prior, row.observed, m, allowed), truth, state, row.observed))
        comp["B3L"][k] = _rates(sl.score_member(bl.b3l_member(prior, row.observed, m, allowed), truth, state, row.observed))
        comp["B5"][k] = {"L3": bl.b5_l3(m, truth, state, seed=bl.stable_seed(row.row_id, m.member, "B5"))}
        comp["D"][k] = {"L3": bl.d_l3(m, truth, state, seed=bl.stable_seed(row.row_id, m.member, "D"))}
        for name, kw in (sens or {}).items():
            comp[name][k] = _rates(sl.score_member(bl.b3_member(prior, row.observed, m, allowed, **kw), truth, state, row.observed))
    for pm in placebo_members or ():
        pms = sl.score_member(pm, truth, state, row.observed)
        comp["B1"][str(pm.member)] = {**_rates(pms), "extra": dict(pms.extra)}
    comp["B2"]["0"] = _rates(sl.score_member(bl.b2_member(row.observed), truth, state, row.observed))
    for k, v in (b4 or {}).items():
        comp["B4"][str(k)] = dict(v)
    return rec


# ---------------------------------------------------------------------------- secondary views (§11)

def _identity(m):
    return m


def _detector_member(vocab):
    """The member restricted to detector-vocabulary classes: L2 claims and L3 object items (rooms are not
    detector words, so the line has no room items and no L1)."""
    def xf(m):
        return dataclasses.replace(
            m, l2_claims=frozenset(c for c in m.l2_claims if c in vocab), l1_claims=frozenset(),
            l3_items=tuple(it for it in m.l3_items if it.kind == "object" and it.label in vocab))
    return xf


def view_specs(ctx) -> Dict[str, Dict[str, Any]]:
    """The secondary readouts that re-score a row under another rule. Each: the levels it reports, the truth
    and the stage state it uses, a transform of every member, the labels B3 may use, and the prior."""
    vocab = frozenset(score_levels.labels.detector_vocab())

    def loose(row):
        st = ctx.states[row.row_id]
        return dataclasses.replace(st, open_types=st.open_types_loose, open_classes=st.open_classes_loose)

    def partly(row):
        st = ctx.states[row.row_id]
        return dataclasses.replace(st, unobserved=st.partly_seen)

    return {
        "loose": {"levels": ("L1", "L2"), "truth": lambda r: ctx.truths[r.scene], "state": loose,
                  "xform": _identity, "allowed": None, "prior": ctx.prior},
        "l3_partly_seen": {"levels": ("L3",), "truth": lambda r: ctx.truths[r.scene], "state": partly,
                           "xform": _identity, "allowed": None, "prior": ctx.prior},
        "detector_vocab": {"levels": ("L2", "L3"), "truth": lambda r: ctx.truths[r.scene],
                           "state": lambda r: ctx.states[r.row_id], "xform": _detector_member(vocab),
                           "allowed": vocab, "prior": ctx.prior},
        "synonym_primary_only": {"levels": ("L2", "L3"), "truth": lambda r: ctx.truths_primary[r.scene],
                                 "state": lambda r: ctx.states_primary[r.row_id], "xform": _identity,
                                 "allowed": None, "prior": ctx.prior_primary},
    }


def sensitivity_kwargs(ctx, row) -> Dict[str, Dict[str, Any]]:
    """B3_seen: counts are the truly seen regions and mapped objects of §5.4. B3_size: the prior's houses are
    those in the same third by number of regions. B3_seen_size: both."""
    truth, state = ctx.truths[row.scene], ctx.states[row.row_id]
    room_m, class_n = baselines.seen_counts(truth, state)
    houses = ctx.prior.size_third(len(truth.regions))
    return {"B3_seen": {"room_counts": room_m, "class_counts": class_n},
            "B3_size": {"houses": houses},
            "B3_seen_size": {"room_counts": room_m, "class_counts": class_n, "houses": houses}}


def _meta(rec: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: rec[k] for k in META_KEYS}


def secondary_records(ctx, name: str, members_by_row: Mapping[str, Sequence], placebo_by_row: Mapping[str, Sequence],
                      specs: Optional[Mapping[str, Mapping[str, Any]]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """For each secondary view, one record per row (the shape `analyse` takes)."""
    specs = specs or view_specs(ctx)
    out: Dict[str, List[Dict[str, Any]]] = {}
    for vname, spec in specs.items():
        xf = spec["xform"]
        mrow = {rid: [xf(m) for m in ms] for rid, ms in members_by_row.items()}
        recs = []
        for r in ctx.rows:
            truth, state = spec["truth"](r), spec["state"](r)
            pm = [xf(m) for m in placebo_by_row[r.row_id]]
            b4 = {} if name == "placebo" else baselines.b4_scores(r, ctx.rows, mrow, truth, state)
            rec = build_record(r, truth, state, mrow.get(r.row_id, ()), spec["prior"], pm, b4, allowed=spec["allowed"])
            recs.append({**_meta(rec), "possible": rec["possible"], "model": rec["model"],
                         "comparators": rec["comparators"]})
        out[vname] = recs
    return out


EXTRA_LEVEL = {"l1_matched": "L1", "l3_multi": "L3", "l3_multi_unobs": "L3", "l3_rooms": "L3", "l3_objects": "L3",
               "l4_0p5m": "L2", "l4_1p0m": "L2", "l4_2p0m": "L2", "l4_3p0m": "L2"}


def extras_summary(recs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """The readouts that come from `extra` of each member score: L1 with one claim per region, the share of
    items that reach two or more regions (all / unobserved), L3 for rooms and objects apart, and L4 at
    0.5, 1, 2 and 3 m. Each: the model's cluster means, the placebo's (B1) and their difference with the
    sign-flip interval. The rows are those where a hit is possible at the level the readout belongs to."""
    out: Dict[str, Any] = {}
    for key, lv in EXTRA_LEVEL.items():
        mine, theirs, diffs = [], [], []
        for r in recs:
            if not r["possible"][lv]:
                continue
            a = _mean(m["extra"].get(key) for m in r["model"].values())
            b = _mean(m.get("extra", {}).get(key) for m in r["comparators"]["B1"].values())
            if a is not None:
                mine.append((r["cluster"], a))
            if b is not None:
                theirs.append((r["cluster"], b))
            if a is not None and b is not None:
                diffs.append((r["cluster"], a - b))
        entry = _test_entry(_cluster_values(diffs), len(diffs))
        entry["model_clusters"] = _cluster_values(mine)
        entry["placebo_clusters"] = _cluster_values(theirs)
        out[key] = entry
    return out


# ------------------------------------------------------------------------------------ context

class Context:
    """Everything a run needs that does not depend on the model."""


def observed_path(row, runs_root: Optional[Path] = None) -> Path:
    """The row's track-0 observed YAML, habitat_scene_graph_original_graph0.yaml: the file
    live_policy's no_llm_completions loaded as `observed` (the path _preprocess_dsg returns)."""
    run, stage, _rnd = extract_preds._frame_index(str(extract_preds.FRAME_PATH))[row.row_id]
    return Path(runs_root or extract_preds.RUNS_ROOT) / run / "stages" / str(stage) / "habitat_scene_graph_original_graph0.yaml"


def build_context(frame: Path, runs_root: Path, truth_dir: Optional[Path] = None,
                  rounds_for_rows: Optional[Sequence[int]] = None) -> Context:
    ep, rt, bl = extract_preds, region_truth, baselines
    ctx = Context()
    ctx.frame, ctx.runs_root = Path(frame), Path(runs_root)
    t0 = time.perf_counter()
    index = ep.parse_frame(ctx.frame)
    ep._frame_index.cache_clear()
    ctx.run_of_row = {rid: run for rid, run, _st, _rd in index}
    ctx.rows = [ep.load_row(rid, ctx.runs_root, ctx.frame) for rid, _r, _s, _d in index]
    td = {} if truth_dir is None else {"truth_dir": Path(truth_dir)}
    scenes = sorted({r.scene for r in ctx.rows})
    ctx.truths = {s: rt.load_scene_truth(s, **td) for s in scenes}
    ctx.truths_primary = {s: rt.load_scene_truth(s, include_extended=False, **td) for s in scenes}
    ctx.states = {r.row_id: rt.stage_state(ctx.truths[r.scene], r) for r in ctx.rows}
    ctx.states_primary = {r.row_id: rt.stage_state(ctx.truths_primary[r.scene], r) for r in ctx.rows}
    ctx.prior = bl.Prior()
    ctx.prior_primary = bl.Prior(include_extended=False)
    ctx.observed_graphs = {}
    ctx.timing = {"truth_and_states_s": time.perf_counter() - t0}
    return ctx


def placebo_inputs(ctx) -> Tuple[Dict[str, List[Any]], Dict[str, Dict[int, dict]]]:
    """B1: the placebo's four members per row, and the graphs they were read from."""
    ep, bl = extract_preds, baselines

    def raw(row):
        import yaml
        with open(observed_path(row, ctx.runs_root)) as f:
            return yaml.safe_load(f) or {"nodes": [], "edges": []}

    members, docs = {}, {}
    for r in ctx.rows:
        graphs = bl.placebo_graphs(r, raw)
        docs[r.row_id] = {k: g for k, g in enumerate(graphs)}
        members[r.row_id] = [ep.member_from_doc(g, r.observed, k) for k, g in enumerate(graphs)]
    return members, docs


def model_inputs(ctx, name: str, claude_root: Optional[Path], placebo: Tuple[Dict, Dict]):
    """(members by row, completion docs by row, live docs by row or None, Claude member status by row)."""
    ep = extract_preds
    if name == "placebo":
        return dict(placebo[0]), dict(placebo[1]), None, {}
    members: Dict[str, List[Any]] = {}
    docs: Dict[str, Dict[int, dict]] = {}
    live: Dict[str, Dict[int, dict]] = {}
    status: Dict[str, Dict[int, str]] = {}
    for r in ctx.rows:
        mem, dd = [], {}
        for m, path in ep.member_files(r, name, ctx.runs_root, ep.GEMINI_ROOT, claude_root, ctx.frame):
            try:
                doc = ep.load_doc(path)
                mem.append(ep.member_from_doc(doc, r.observed, m))
                dd[m] = doc
            except (ValueError, OSError, KeyError, TypeError, ep.yaml.YAMLError):
                ep.SKIPPED["member_unreadable"] += 1
        members[r.row_id], docs[r.row_id] = mem, dd
        if name == "deepseek":
            run, stage, _ = ep._frame_index(str(ctx.frame))[r.row_id]
            live[r.row_id] = {k: ep.load_doc(p) for k, p in ep.raw_member_files(run, stage, ctx.runs_root).items()}
        if is_claude(name):
            status[r.row_id] = ep.claude_member_status(claude_root, name, r.row_id)
    return members, docs, (live if name == "deepseek" else None), status


def score_model(ctx, name: str, members_by_row, docs_by_row, live_by_row, placebo_members, with_validity: bool = True):
    """Primary records, with sensitivity forms of B3 and the validity layer, for one model. The secondary
    views are returned apart."""
    val = validity
    recs = []
    errors: List[float] = []
    left_out = 0
    for r in ctx.rows:
        truth, state = ctx.truths[r.scene], ctx.states[r.row_id]
        members = members_by_row.get(r.row_id, ())
        b4 = {} if name == "placebo" else baselines.b4_scores(r, ctx.rows, members_by_row, truth, state)
        rec = build_record(r, truth, state, members, ctx.prior, placebo_members[r.row_id], b4,
                           sens=sensitivity_kwargs(ctx, r))
        if name == "placebo":
            rec["comparators"]["B1"] = {}          # the model is the placebo: B1 would be itself
        for m in members:
            d, n = score_levels.placement_errors(m, truth, state)
            errors.extend(d)
            left_out += n
        if with_validity and docs_by_row.get(r.row_id):
            import_path = observed_path(r, ctx.runs_root)
            obs_norm = val._asp()[0](import_path, observed=True)
            table = val.guess_table(r, obs_norm, docs_by_row[r.row_id],
                                          live_by_row.get(r.row_id) if live_by_row else None)
            rec["validity"] = val.row_record(table, truth, state)
        recs.append(rec)
    return recs, errors, left_out


def analyse_views(per_view: Mapping[str, Sequence[Mapping[str, Any]]], model: str, specs, use_rounds=None):
    out = {}
    for vname, recs in per_view.items():
        sub = [r for r in recs if use_rounds is None or r["round"] in use_rounds]
        out[vname] = analyse(sub, model, levels=specs[vname]["levels"])
    return out


# -------------------------------------------------------------------------------- the whole run

def finished_rounds(rows: Sequence, members_by_model: Mapping[str, Mapping[str, Sequence]]) -> List[int]:
    """§10: the rounds in which every model holds at least one member on every row of the round."""
    rounds = sorted({r.round for r in rows})
    return [rd for rd in rounds
            if all(members_by_model[m].get(r.row_id) for m in members_by_model for r in rows if r.round == rd)]


def run(models: Sequence[str], frame: Path, rounds: Optional[Sequence[int]] = None, *,
        runs_root: Optional[Path] = None, claude_root: Optional[Path] = None, truth_dir: Optional[Path] = None,
        with_validity: bool = True, with_room_test: bool = True, room_test_runs: str = "counted",
        log: Callable[[str], None] = lambda s: None) -> Dict[str, Any]:
    """Load the frame, the truth and every model's members, then score. Called only after the guards.
    Returns everything, in memory: the caller decides what to write (a real run writes it; a dry run
    writes counts only)."""
    ep = extract_preds
    runs_root = Path(runs_root or ep.RUNS_ROOT)
    t_all = time.perf_counter()
    ctx = build_context(frame, runs_root, truth_dir)
    log(f"truth and states: {ctx.timing['truth_and_states_s']:.1f}s")
    t = time.perf_counter()
    placebo = placebo_inputs(ctx)
    ctx.timing["placebo_s"] = time.perf_counter() - t
    inputs = {}
    for m in models:
        t = time.perf_counter()
        inputs[m] = model_inputs(ctx, m, claude_root, placebo)
        ctx.timing[f"load_{m}_s"] = time.perf_counter() - t
        log(f"loaded {m}")
    out = run_core(ctx, models, inputs, placebo, rounds, with_validity, with_room_test, log, room_test_runs)
    ctx.timing["total_s"] = time.perf_counter() - t_all
    return out


def run_core(ctx, models: Sequence[str], inputs: Mapping[str, Tuple], placebo: Tuple, rounds: Optional[Sequence[int]] = None,
             with_validity: bool = True, with_room_test: bool = True,
             log: Callable[[str], None] = lambda s: None, room_test_runs: str = "counted") -> Dict[str, Any]:
    """Score every model on the context's rows. `inputs[model]` is (members by row, completion docs by row,
    live docs by row or None, Claude member status by row); `placebo` is (members, docs) of the placebo."""
    out: Dict[str, Any] = {"ctx": ctx, "models": {}, "timing": ctx.timing, "members": {m: inputs[m][0] for m in models}}
    claude = [m for m in models if is_claude(m)]
    done = finished_rounds(ctx.rows, {m: inputs[m][0] for m in claude}) if claude else []
    use = set(rounds) if rounds is not None else (set(done) if claude else None)
    out.update(finished_rounds=done, rounds_used=sorted(use) if use is not None else None)
    specs = view_specs(ctx)
    family_results: Dict[str, Any] = {}
    placebo_recs = None
    for m in models:
        t = time.perf_counter()
        members, docs, live, status = inputs[m]
        recs, errors, left_out = score_model(ctx, m, members, docs, live, placebo[0], with_validity)
        if m == "placebo":
            placebo_recs = recs
        views = secondary_records(ctx, m, members, placebo[0], specs)
        sub = [r for r in recs if use is None or r["round"] in use]
        entry = {"role": "confirmatory" if is_claude(m) else "exploratory", "records": recs,
                 "analysis_all_rows": analyse(recs, m), "analysis": analyse(sub, m),
                 "secondary": analyse_views(views, m, specs, use), "extras": extras_summary(sub),
                 "error_sample": errors, "error_sample_left_out": left_out, "status": status,
                 "views": views}
        if with_validity:
            entry["validity"] = validity.summarise(sub)
        if is_claude(m):
            family_results[m] = entry["analysis"]
        else:
            entry["exploratory_family"] = family({m: entry["analysis"]}, [])
        out["models"][m] = entry
        ctx.timing[f"score_{m}_s"] = time.perf_counter() - t
        log(f"scored {m}")
    if placebo_recs is None:
        placebo_recs, _e, _l = score_model(ctx, "placebo", placebo[0], placebo[1], None, placebo[0], False)
    out["placebo_records"] = placebo_recs
    out["mdd"] = mdd_table(placebo_recs)
    out["family"] = family(family_results, claude) if family_results else None
    if with_room_test:
        t = time.perf_counter()
        out["room_test"] = run_room_test(ctx, models, inputs, log, room_test_runs)
        ctx.timing["room_test_s"] = time.perf_counter() - t
    return out


def run_room_test(ctx, models: Sequence[str], inputs, log, which: str = "counted") -> Dict[str, Any]:
    """§11, the paper's room test: every counted live run, and the 4-member replays of each model."""
    rtm, ep = room_test, extract_preds
    states_by_run: Dict[str, Any] = {}

    def states(run):
        if run not in states_by_run:
            scene = ep.run_info(run)[0]
            if scene not in ctx.truths:
                ctx.truths[scene] = region_truth.load_scene_truth(scene)
            states_by_run[run] = rtm.run_states(run, ctx.truths[scene], ctx.runs_root)
        return states_by_run[run]

    live_results = []
    for run in rtm.live_runs(ctx.runs_root, which=which):
        scene = ep.run_info(run)[0]
        if scene not in ctx.truths:
            ctx.truths[scene] = region_truth.load_scene_truth(scene)
        live_results.append(rtm.live_run_result(run, ctx.truths[scene], ctx.runs_root, states(run)))
        log(f"room test: {run}")
    replay = {}
    for m in models:
        members = inputs[m][0]
        runs_needed = {ctx.run_of_row[r.row_id] for r in ctx.rows if members.get(r.row_id)}
        for run in runs_needed:
            states(run)
        replay[m] = rtm.replay_counts(ctx.rows, members, ctx.truths, states_by_run, ctx.run_of_row)
    return {"live": {"runs": live_results, "by_arm": rtm.by_arm(live_results)}, "replay": replay}


# ----------------------------------------------------------------------------------------- dry run

def _spread(values: Sequence[float]) -> Dict[str, Any]:
    vals = sorted(values)
    if not vals:
        return {"min": None, "median": None, "max": None, "total": 0, "n": 0}
    return {"min": vals[0], "median": statistics.median(vals), "max": vals[-1], "total": sum(vals), "n": len(vals)}


def dry_summary(result: Mapping[str, Any], models: Sequence[str]) -> Dict[str, Any]:
    """What a dry run may write: counts, shapes and timing. No hit, no rate, no difference, no p-value, no
    interval, no verdict, no error distance. Every number here is an integer count, a count's min / median /
    max, a boolean, or a time in seconds; test_dry_output_holds_only_counts checks it."""
    ctx = result["ctx"]
    rows = ctx.rows
    states = [ctx.states[r.row_id] for r in rows]
    out: Dict[str, Any] = {"mode": "dry", "frame_rows": len(rows),
                           "rows_by_round": {str(rd): sum(1 for r in rows if r.round == rd) for rd in sorted({r.round for r in rows})},
                           "clusters": len({r.cluster for r in rows}), "scenes": sorted(ctx.truths)}
    out["truth"] = {s: {"regions": len(t.regions), "regions_with_footprint_cells": len(t.regions),
                        "reference_objects": sum(len(g.ref_objects) for g in t.regions.values()),
                        "markers": sum(len(g.markers) for g in t.regions.values())} for s, t in sorted(ctx.truths.items())}
    out["prior"] = {"houses": ctx.prior.n_houses,
                    "houses_in_size_third": {s: len(ctx.prior.size_third(len(t.regions))) for s, t in sorted(ctx.truths.items())}}
    out["regions_per_state"] = {
        "seen": _spread([len(s.seen) for s in states]), "partly_seen": _spread([len(s.partly_seen) for s in states]),
        "unobserved": _spread([len(s.unobserved) for s in states]), "unseen": _spread([len(s.unseen) for s in states]),
        "open_types": _spread([len(s.open_types) for s in states]), "open_classes": _spread([len(s.open_classes) for s in states])}
    out["rows_left_out"] = {lv: sum(1 for r in rows if not score_levels.possible(lv, ctx.truths[r.scene], ctx.states[r.row_id]))
                            for lv in LEVELS}
    out["models"] = {}
    for m in models:
        e = result["models"][m]
        recs = e["records"]
        mem_counts = [len(r["model"]) for r in recs]
        counts_of = lambda key: [v["counts"][key] for r in recs for v in r["model"].values()]   # noqa: E731
        info: Dict[str, Any] = {
            "role": e["role"], "rows": len(recs), "rows_with_members": sum(1 for c in mem_counts if c),
            "members_total": sum(mem_counts), "members_per_row": _spread(mem_counts),
            "rows_with_fewer_than_4_members": sum(1 for c in mem_counts if c < 4),
            "claims_l1_per_member": _spread(counts_of("l1_n")), "claims_l2_per_member": _spread(counts_of("l2_n")),
            "items_l3_per_member": _spread(counts_of("l3_n")),
            "rows_with_no_score_for_the_model": {lv: sum(1 for r in recs if r["possible"][lv] and model_row_score(r, lv) is None)
                                                 for lv in LEVELS}}
        info["comparators_scored"] = {
            c: {lv: sum(1 for r in recs if r["possible"][lv] and row_contrast(r, c, lv) is not None) for lv in ("L1", "L2", "L3")}
            for c in MEMBER_PAIRED + ROW_PAIRED if m != "placebo" or c != "B1"}
        info["comparators_produced_a_score"] = {c: {lv: v > 0 for lv, v in d.items()} for c, d in info["comparators_scored"].items()}
        info["clusters_with_a_contrast"] = {
            lv: {c: e["analysis_all_rows"]["levels"][lv]["comparators"].get(c, {}).get("n_clusters", 0)
                 for c in HYPOTHESIS_COMPARATORS[lv] + REPORTED_COMPARATORS[lv]} for lv in LEVELS}
        info["b4_pairs"] = {lv: len(e["analysis_all_rows"]["levels"][lv]["comparators"]["B4"].get("pairs", {})) for lv in ("L1", "L2")}
        out["models"][m] = info
    # member-level extraction counts come from the loaded members, kept in the result
    for m in models:
        mem = result["members"][m]
        allm = [x for ms in mem.values() for x in ms]
        info = out["models"][m]
        info["new_objects"] = sum(len(x.new_objects) for x in allm)
        info["new_objects_without_a_class"] = sum(x.n_objects_unlabelled for x in allm)
        info["new_objects_flagged"] = sum(x.n_objects_flagged for x in allm)
        info["new_objects_unflagged"] = sum(x.n_objects_unflagged for x in allm)
        info["new_rooms"] = sum(len(x.new_rooms) for x in allm)
        info["new_rooms_untyped"] = sum(x.n_rooms_untyped for x in allm)
        info["new_rooms_dining"] = sum(x.n_rooms_dining for x in allm)
        e = result["models"][m]
        info["error_sample"] = {"n_distances": len(e["error_sample"]), "guesses_left_out": e["error_sample_left_out"]}
        if "validity" in e:
            info["validity"] = validity.dry_counts(e["records"])
        if e["status"]:
            cnt: Dict[str, int] = {}
            for st in e["status"].values():
                for v in st.values():
                    cnt[v] = cnt.get(v, 0) + 1
            info["claude_members_by_status"] = cnt
    if result.get("room_test"):
        out["room_test"] = room_test.dry_counts(result["room_test"]["live"]["by_arm"], result["room_test"]["replay"])
    out["mdd_table_ran"] = {lv: result["mdd"][lv]["n_clusters"] for lv in LEVELS}
    out["family_ran"] = result["family"] is not None
    out["skipped_counters"] = dict(extract_preds.SKIPPED)
    out["timing"] = {k: round(v, 2) for k, v in result["timing"].items()}
    return out


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


def verify_prereg_file(md_path: Path = None, hash_path: Path = None) -> str:
    """The pre-registration text itself must still hash to the registered value (it is frozen)."""
    md_path = Path(md_path or PREREG_MD_PATH)
    hash_path = Path(hash_path or PREREG_HASH_PATH)
    if not md_path.is_file():
        raise Refused(f"refused: {md_path} does not exist")
    actual = hashlib.sha256(md_path.read_bytes()).hexdigest()
    if actual != _first_field(hash_path):
        raise Refused(f"refused: {md_path.name} hashes to {actual}, not the registered value; it was edited")
    return actual


def read_frame(path: Path = FRAME_PATH) -> List[Tuple[str, int]]:
    out = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            parts = line.split()
            out.append((parts[0], int(parts[2])))
    return out


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


def _write(path: Path, obj: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(_jsonable(obj), indent=1, sort_keys=True))


def _sha(path: Path) -> Optional[str]:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def write_real(result: Mapping[str, Any], out_dir: Path, run_info: Mapping[str, Any]) -> List[str]:
    """The real run's files (see README.md). Returns their names."""
    out_dir = Path(out_dir)
    written = []

    def put(name, obj):
        _write(out_dir / name, obj)
        written.append(name)

    for m, e in result["models"].items():
        put(f"error_sample_{m}.json", [float(d) for d in e["error_sample"]])   # PREREGISTRATION_M2.md §4 F3-m
        put(f"records_{m}.json", {"records": e["records"], "secondary_records": e["views"]})
    summary = {"run_info": run_info, "finished_rounds": result["finished_rounds"], "rounds_used": result["rounds_used"],
               "family": result["family"], "mdd_table": result["mdd"], "room_test": result.get("room_test"),
               "models": {m: {k: v for k, v in e.items() if k not in ("records", "views", "error_sample")}
                          | {"error_sample_n": len(e["error_sample"])} for m, e in result["models"].items()}}
    put("results.json", summary)
    put("mdd_table.json", result["mdd"])
    if result.get("room_test"):
        put("room_test.json", result["room_test"])
    put("validity.json", {m: e.get("validity") for m, e in result["models"].items()})
    return written


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--models", required=True, help="comma list of: " + ",".join(ALL_MODELS))
    ap.add_argument("--out", required=True, help="folder for the output files")
    ap.add_argument("--dry", action="store_true", help="compute everything, write only counts, shapes and timing")
    ap.add_argument("--frame", default=str(FRAME_PATH))
    ap.add_argument("--runs-root", default=None, help="the saved runs (default: the laptop copy)")
    ap.add_argument("--claude-root", default=None, help="<root>/<model>/<row_id>/member_<k>/parsed_graph.yaml")
    ap.add_argument("--truth-dir", default=None)
    ap.add_argument("--rounds", default="auto", help="'auto' (rounds the Claude models finished) or e.g. 1,2")
    ap.add_argument("--prereg-sha256", default=None, help="must equal the first field of PREREGISTRATION_SEMANTIC.sha256")
    ap.add_argument("--no-room-test", action="store_true")
    ap.add_argument("--room-test-runs", choices=("counted", "all"), default="counted",
                    help="live runs for the paper's room test: those the run table counts, or also those it excludes")
    ap.add_argument("--no-validity", action="store_true")
    args = ap.parse_args(argv)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    bad = [m for m in models if m not in ALL_MODELS]
    if bad:
        raise Refused(f"refused: unknown model {bad}; expected {ALL_MODELS}")
    check_guards(models, args.prereg_sha256)          # before any model output is touched
    prereg_file_sha = verify_prereg_file()
    if any(is_claude(m) for m in models) and not args.claude_root:
        raise Refused("refused: --claude-root is required for a Claude model")
    rounds = None if args.rounds == "auto" else [int(x) for x in args.rounds.split(",")]
    out_dir = Path(args.out)
    result = run(models, Path(args.frame), rounds, runs_root=args.runs_root, claude_root=args.claude_root,
                 truth_dir=args.truth_dir, with_validity=not args.no_validity, with_room_test=not args.no_room_test, room_test_runs=args.room_test_runs,
                 log=lambda s: print(s, file=sys.stderr))
    if args.dry:
        # members are needed for extraction counts; keep them out of the saved scores
        dry = dry_summary(result, models)
        dry["prereg_sha256"] = args.prereg_sha256.strip().lower()
        _write(out_dir / "dry_run.json", dry)
        print(json.dumps(_jsonable(dry), indent=1, sort_keys=True))
        return 0
    run_info = {"models": models, "prereg_sha256": args.prereg_sha256.strip().lower(), "prereg_file_sha256": prereg_file_sha,
                "freeze_present": Path(FREEZE_PATH).is_file(), "freeze_sha256": _sha(FREEZE_PATH),
                "frame_sha256": _sha(args.frame), "label_table_sha256": _sha(HERE / "canon_labels.json"),
                "placebo_calibration_sha256": _sha(HERE.parent / "placebo_calibration.json"),
                "rounds_argument": args.rounds, "python": platform.python_version(),
                "skipped_counters": dict(extract_preds.SKIPPED), "timing_s": result["timing"]}
    files = write_real(result, out_dir, run_info)
    print("wrote", ", ".join(files), "to", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
