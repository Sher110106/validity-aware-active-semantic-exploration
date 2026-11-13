"""The validity layer of the semantic test (PREREGISTRATION_SEMANTIC.md §11), scored in the same pass.

Views of a member's guesses (a guess is a new object or a new room by §7: by place alone):

    raw          every guess (the confirmatory view)
    V            guesses the E2 filter keeps: `validate_completion(..., ValidationConfig(allow_parsed_mapping=True))`,
                 called as live_policy.track_keep_sets calls it; a guess is kept if its node is in the validated
                 graph (a completion the validator rejects keeps none of its guesses)
    V+vote<t>    V, and the guess has support >= t of the 4 intended members (0.5, 0.75, 1.0). Support is
                 asp_offline.support_policy.support_scores: a node of the same label and parent room within 0.5 m
                 (objects) or 4.0 m (rooms) in the member itself or in another member, divided by 4, never by the
                 number of members that survived. The same rule as support_filtered_graph.
    V+2of8       V, and at least 2 of the 8 members of a live stage hold a node of the same label near the guess
                 (0.5 m objects, 4.0 m rooms, 3-D distance, any track, no parent-room test, because room ids are a
                 separate namespace per track). The paper's rule. Only for a model whose members come from a live
                 stage (DeepSeek).

Two readings, noted in README.md:
  * support is computed on the completions with `is_predicted` set from the node id (a node whose id is not in
    the observed graph is predicted), because Gemini sets the flag false on every new object and support_policy
    would then ignore them. The validator itself is id-based and gets the file as live_policy gives it.
  * a guess that reuses an observed node id is, for the validator and for the vote, an echoed observed node: kept.

Readouts: (1) share removed, by reason; (2) hit rates of kept against removed guesses, interval of the difference;
(3) member support against L3 truth: reliability curve, Brier, ECE, isotonic calibrator fit on one scene and
tested on the other; (4) hits kept against guesses kept in each view.
"""
from __future__ import annotations

import importlib
import importlib.util
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


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


model = _sibling("model")
stats = _sibling("stats")
score_levels = _sibling("score_levels")
extract_preds = _Lazy("extract_preds")

TOOLS_DIR = Path(__file__).resolve().parent.parent.parent
EXPECTED_SIZE = 4                     # §3: where a rule needs the intended count, it is 4
VOTE_LEVELS = (0.5, 0.75, 1.0)
OBJECT_M = 0.5                        # support_policy.support_filtered_graph defaults
ROOM_M = 4.0
VIEWS = ("raw", "V", "V+vote0.5", "V+vote0.75", "V+vote1.0", "V+2of8")
DETECTABLE_BAND = 0.05                # §11 readout 2


def _asp():
    """The validator and the support rule, imported from tools/asp_offline."""
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    from asp_offline.author_io import load_author_graph, normalize_author_graph
    from asp_offline.support_policy import support_scores
    from asp_offline.validator import ValidationConfig, validate_completion
    return load_author_graph, normalize_author_graph, support_scores, ValidationConfig, validate_completion


# ------------------------------------------------------------------------------------ guesses

@dataclass(frozen=True)
class Guess:
    member: int
    node: "model.Node"
    valid: bool                      # kept by the validator (V)
    reason: Optional[str]            # why removed, else None
    support: Optional[float]         # hits / 4; None for a node that reuses an observed id
    n8: Optional[int] = None         # members of the live stage holding a matching node (itself included)

    @property
    def echoed(self) -> bool:
        return self.support is None


def vote_view(t: float) -> str:
    return f"V+vote{t:g}"


def keeps(g: Guess, view: str) -> bool:
    """Does the view keep this guess?"""
    if view == "raw":
        return True
    if not g.valid:
        return False
    if view == "V":
        return True
    if view == "V+2of8":
        return g.n8 is not None and g.n8 >= 2
    if view.startswith("V+vote"):
        t = float(view[len("V+vote"):])
        return g.support is None or g.support >= t - 1e-9
    raise ValueError(f"unknown view {view!r}")


def item_of(node: "model.Node") -> Optional["model.Item"]:
    """The L3 item of a guess (§7, item 51), or None if it makes none."""
    if node.kind == "room":
        return model.Item("room", node.room_type, node.xy) if node.room_type in model.ROOM_TYPES else None
    return model.Item("object", node.canon, node.xy) if node.canon else None


def view_member(member: int, guesses: Iterable[Guess], view: Optional[str] = None,
                removed: bool = False) -> "model.Member":
    """The Member made of the guesses a view keeps (or, with removed=True, of those the validator removed)."""
    if removed:
        pick = [g for g in guesses if not g.valid]
    else:
        pick = [g for g in guesses if keeps(g, view)]
    return extract_preds.member_from_nodes(member, [g.node for g in pick if g.node.kind == "room"],
                                           [g.node for g in pick if g.node.kind == "object"])


# ---------------------------------------------------------------------------- the validator

def _remove_reasons(result) -> Tuple[bool, Dict[str, str], str]:
    """(rejected, reason by node id, reason of a rejection)."""
    reasons: Dict[str, str] = {}
    reject = ""
    for issue in result.issues:
        if issue.severity == "reject":
            reject = reject or str(issue.code)
        elif issue.node_id is not None:
            reasons.setdefault(str(issue.node_id), str(issue.code))
    return bool(result.rejected), reasons, reject


def validate_member(observed_graph: Mapping[str, Any], doc: Mapping[str, Any]) -> Tuple[set, Dict[str, str], str]:
    """Run the E2 filter on one completion, as live_policy.track_keep_sets does. Returns (ids of the
    nodes kept, reason by removed id, reason the completion was rejected or "")."""
    _, normalize, _, ValidationConfig, validate_completion = _asp()
    try:
        completion = normalize(doc)
        result = validate_completion(completion, observed_graph, ValidationConfig(allow_parsed_mapping=True))
    except Exception as exc:  # noqa: BLE001 - a completion the validator cannot read is a rejected one
        return set(), {}, f"validator_error:{type(exc).__name__}"
    rejected, reasons, reject = _remove_reasons(result)
    kept = {str(n["id"]) for n in result.graph["nodes"]}
    return kept, reasons, (reject or "rejected") if rejected else ""


def _id_flagged(doc: Mapping[str, Any], observed_ids: Iterable[str]) -> Dict[str, Any]:
    """A copy of a completion with is_predicted set from the node id (see the module note)."""
    obs = set(observed_ids)
    nodes = []
    for n in doc.get("nodes") or []:
        if isinstance(n, Mapping):
            n = dict(n)
            n["is_predicted"] = str(n.get("id")) not in obs
        nodes.append(n)
    return {**doc, "nodes": nodes}


def support_by_id(docs: Mapping[int, Mapping[str, Any]], observed_ids: Iterable[str]) -> Dict[int, Dict[str, float]]:
    """For each member, the support (hits / 4) of each of its predicted nodes, over the members given."""
    _, normalize, support_scores, _, _ = _asp()
    flagged = {m: normalize(_id_flagged(d, observed_ids)) for m, d in docs.items()}
    ensemble = list(flagged.values())
    out: Dict[int, Dict[str, float]] = {}
    for m, comp in flagged.items():
        out[m] = {str(h.node_id): float(h.support)
                  for h in support_scores(comp, ensemble, expected_size=EXPECTED_SIZE)}
    return out


def count_n8(node: "model.Node", live_nodes: Mapping[int, Sequence["model.Node"]]) -> int:
    """How many of the live stage's members hold a node of this label, kind and 3-D place (§11, the paper's rule)."""
    thr = ROOM_M if node.kind == "room" else OBJECT_M
    n = 0
    for nodes in live_nodes.values():
        for o in nodes:
            if o.kind == node.kind and o.name == node.name and \
                    math.dist((o.xy[0], o.xy[1], o.z), (node.xy[0], node.xy[1], node.z)) <= thr:
                n += 1
                break
    return n


def guess_table(row, observed_graph: Mapping[str, Any], docs: Mapping[int, Mapping[str, Any]],
                live_docs: Optional[Mapping[int, Mapping[str, Any]]] = None) -> Dict[int, List[Guess]]:
    """Every guess of every member of a row, with its validator outcome, its support and, on a live stage,
    its count of the 8. `observed_graph` is load_author_graph(observed file, observed=True)."""
    ep = extract_preds
    observed_ids = {str(i) for i in row.observed.node_ids}
    support = support_by_id(docs, observed_ids) if docs else {}
    live_nodes = None
    if live_docs is not None:
        live_nodes = {k: ep.parse_doc_nodes(d)[0] for k, d in live_docs.items()}
    out: Dict[int, List[Guess]] = {}
    for m, doc in docs.items():
        kept, reasons, reject = validate_member(observed_graph, doc)
        nodes, _, _ = ep.parse_doc_nodes(doc)
        new_rooms, new_objects = ep.guesses_of(nodes, row.observed)
        table = []
        for node in new_rooms + new_objects:
            sid = str(node.node_id)
            valid = sid in kept
            if valid:
                reason = None
            else:
                reason = reasons.get(sid) or (f"rejected:{reject}" if reject else "other")
            sup = support.get(m, {}).get(sid)
            if sid in observed_ids:
                sup = None
            table.append(Guess(m, node, valid, reason, sup,
                               count_n8(node, live_nodes) if live_nodes is not None else None))
        out[m] = table
    return out


# ------------------------------------------------------------------------------- row record

LEVEL_KEYS = ("L2", "L3")


def _rates(ms) -> Dict[str, Any]:
    return {"L2": ms.rate("L2"), "L3": ms.rate("L3"),
            "l2_hits": ms.l2_hits, "l2_n": ms.l2_n, "l3_hits": ms.l3_hits, "l3_n": ms.l3_n}


def row_record(table: Mapping[int, Sequence[Guess]], truth, state, views: Sequence[str] = VIEWS) -> Dict[str, Any]:
    """The validity layer of one row and one model. JSON-safe.

        n_guesses, n_removed      counts over every member's guesses
        reasons                   {reason: n} of the removed guesses
        views[view][member]       L2, L3 shares and counts of the member made of the view's kept guesses,
                                  plus n_kept (guesses the view keeps)
        removed[member]           the same for the guesses the validator removed
        support_items             [[support, hit], ...] over L3 items whose guess has a support (readout 3)
    """
    rec: Dict[str, Any] = {"n_guesses": 0, "n_removed": 0, "reasons": {}, "views": {}, "removed": {}, "support_items": []}
    reasons: Counter = Counter()
    for guesses in table.values():
        rec["n_guesses"] += len(guesses)
        for g in guesses:
            if not g.valid:
                rec["n_removed"] += 1
                reasons[g.reason or "other"] += 1
    rec["reasons"] = dict(reasons)
    for view in views:
        if view == "V+2of8" and not any(g.n8 is not None for gs in table.values() for g in gs):
            continue
        per: Dict[str, Any] = {}
        for m, guesses in table.items():
            mem = view_member(m, guesses, view)
            per[str(m)] = {**_rates(score_levels.score_member(mem, truth, state)),
                           "n_kept": sum(1 for g in guesses if keeps(g, view))}
        rec["views"][view] = per
    for m, guesses in table.items():
        rec["removed"][str(m)] = _rates(score_levels.score_member(view_member(m, guesses, removed=True), truth, state))
        for g in guesses:
            it = item_of(g.node)
            if it is not None and g.support is not None:
                rec["support_items"].append([g.support, 1 if score_levels.l3_hit(it, truth, state) else 0])
    return rec


# ---------------------------------------------------------------------------------- readouts

def _mean(vals: Iterable[Optional[float]]) -> Optional[float]:
    v = [float(x) for x in vals if x is not None]
    return math.fsum(v) / len(v) if v else None


def _cluster_mean(pairs: Sequence[Tuple[str, float]]) -> Dict[str, float]:
    if not pairs:
        return {}
    ids, means = stats.cluster_means([v for _, v in pairs], [c for c, _ in pairs])
    return {c: float(m) for c, m in zip(ids, means)}


def share_removed(recs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Readout 1: the share of guesses the validator removes, and by reason (over the records given;
    each record is {"validity": row_record, ...})."""
    n = sum(r["validity"]["n_guesses"] for r in recs)
    removed = sum(r["validity"]["n_removed"] for r in recs)
    reasons: Counter = Counter()
    for r in recs:
        reasons.update(r["validity"]["reasons"])
    return {"n_guesses": n, "n_removed": removed, "share_removed": (removed / n) if n else None,
            "by_reason": {k: {"n": v, "share_of_guesses": v / n} for k, v in sorted(reasons.items())}}


def kept_vs_removed(recs: Sequence[Mapping[str, Any]], level: str) -> Dict[str, Any]:
    """Readout 2 at one level ("L2" or "L3"): hit rate of the guesses V keeps against those it removes,
    averaged member -> row -> cluster as in §8; the difference per cluster; its 95% two-sided sign-flip
    interval; "no detectable difference" if the interval lies within +-0.05."""
    kept_c, rem_c, diffs = [], [], []
    for r in recs:
        v = r["validity"]
        kept = _mean(m[level] for m in v["views"].get("V", {}).values())
        rem = _mean(m[level] for m in v["removed"].values())
        if kept is not None:
            kept_c.append((r["cluster"], kept))
        if rem is not None:
            rem_c.append((r["cluster"], rem))
        if kept is not None and rem is not None:
            diffs.append((r["cluster"], kept - rem))
    d = _cluster_mean(diffs)
    out: Dict[str, Any] = {"level": level, "n_rows": len(diffs), "n_clusters": len(d),
                           "kept": _cluster_mean(kept_c), "removed": _cluster_mean(rem_c),
                           "mean_diff": None, "ci": None, "verdict": "no interval"}
    if d:
        vals = [d[c] for c in sorted(d)]
        out["mean_diff"] = math.fsum(vals) / len(vals)
        lo, hi = stats.sign_flip_ci(vals, 0.95, "two-sided")
        out["ci"] = (lo, hi)
        out["verdict"] = ("no detectable difference" if (lo >= -DETECTABLE_BAND and hi <= DETECTABLE_BAND)
                          else "interval reaches beyond +-0.05")
    return out


def reliability(items_by_scene: Mapping[str, Sequence[Sequence[float]]]) -> Dict[str, Any]:
    """Readout 3: member support against L3 truth. `items_by_scene[scene]` is a list of [support, hit].
    Returns the reliability curve, Brier score and ECE over all items, and, for each scene, the same two
    numbers of an isotonic calibrator fit on the other scene and tested on this one (with the raw support's
    on the same items beside them)."""
    allp = [p for items in items_by_scene.values() for p, _ in items]
    ally = [y for items in items_by_scene.values() for _, y in items]
    out: Dict[str, Any] = {"n_items": len(allp), "curve": [], "brier": None, "ece": None, "cross_scene": {}}
    if allp:
        out["curve"] = stats.reliability_curve(allp, ally)
        out["brier"] = stats.brier_score(allp, ally)
        out["ece"] = stats.expected_calibration_error(allp, ally)
    scenes = sorted(items_by_scene)
    for test in scenes:
        train = [it for s in scenes if s != test for it in items_by_scene[s]]
        held = list(items_by_scene[test])
        if not train or not held:
            out["cross_scene"][test] = {"n_train": len(train), "n_test": len(held), "brier": None, "ece": None}
            continue
        cal = stats.IsotonicMap([p for p, _ in train], [y for _, y in train])
        pred = [cal(p) for p, _ in held]
        y = [h for _, h in held]
        raw = [p for p, _ in held]
        out["cross_scene"][test] = {
            "n_train": len(train), "n_test": len(held),
            "brier": stats.brier_score(pred, y), "ece": stats.expected_calibration_error(pred, y),
            "brier_raw_support": stats.brier_score(raw, y), "ece_raw_support": stats.expected_calibration_error(raw, y)}
    return out


def kept_vs_guesses(recs: Sequence[Mapping[str, Any]], views: Sequence[str] = VIEWS) -> Dict[str, Any]:
    """Readout 4: for each view, the guesses kept, the L3 items and hits among them, the L2 claims and hits,
    pooled over members, and the cluster mean of the member -> row -> cluster L2 and L3 shares."""
    out: Dict[str, Any] = {}
    for view in views:
        n_kept = l3_n = l2_n = 0
        l3_h = l2_h = 0.0
        rows = {"L2": [], "L3": []}
        for r in recs:
            per = r["validity"]["views"].get(view)
            if per is None:
                continue
            for m in per.values():
                n_kept += m["n_kept"]
                l3_n += m["l3_n"]
                l3_h += m["l3_hits"]
                l2_n += m["l2_n"]
                l2_h += m["l2_hits"]
            for lv in LEVEL_KEYS:
                s = _mean(m[lv] for m in per.values())
                if s is not None:
                    rows[lv].append((r["cluster"], s))
        if n_kept or any(rows.values()):
            out[view] = {"guesses_kept": n_kept, "l3_items": l3_n, "l3_hits": l3_h, "l2_claims": l2_n, "l2_hits": l2_h,
                         "cluster_mean_L2": _cluster_mean(rows["L2"]), "cluster_mean_L3": _cluster_mean(rows["L3"])}
    return out


def summarise(recs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """All four readouts over the records of one model (each record carries "validity", "cluster", "scene")."""
    with_v = [r for r in recs if r.get("validity")]
    by_scene: Dict[str, List[Sequence[float]]] = {}
    for r in with_v:
        by_scene.setdefault(r["scene"], []).extend(r["validity"]["support_items"])
    return {"share_removed": share_removed(with_v),
            "kept_vs_removed": {lv: kept_vs_removed(with_v, lv) for lv in LEVEL_KEYS},
            "reliability": reliability(by_scene),
            "kept_vs_guesses": kept_vs_guesses(with_v)}


# ------------------------------------------------------------------------------------ counts

def dry_counts(recs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Counts only (no share and no hit): guesses, removed, by reason, kept in each view, items with a support."""
    out: Dict[str, Any] = {"guesses": 0, "removed": 0, "removed_by_reason": {}, "kept_by_view": {}, "support_items": 0}
    reasons: Counter = Counter()
    kept: Counter = Counter()
    for r in recs:
        v = r.get("validity")
        if not v:
            continue
        out["guesses"] += v["n_guesses"]
        out["removed"] += v["n_removed"]
        reasons.update(v["reasons"])
        out["support_items"] += len(v["support_items"])
        for view, per in v["views"].items():
            kept[view] += sum(m["n_kept"] for m in per.values())
    out["removed_by_reason"] = dict(sorted(reasons.items()))
    out["kept_by_view"] = dict(kept)
    return out
