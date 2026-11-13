"""Comparators of the pre-registered semantic test (PREREGISTRATION_SEMANTIC.md §9).

B3 and B3L (the other-house prior), B5 (swap), D (derangement), B1 (placebo), B4 (wrong
house), B2 (copy the map). Every random draw takes an explicit seed built from
(row_id, member, comparator name) by `stable_seed`, a sha256 hash, never Python's hash().

Sibling modules (model, labels, score_levels) load through `_sibling` and sit as module
attributes, so a test can swap in a fake.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np


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
score_levels = _sibling("score_levels")
labels = _Lazy("labels")

SUMMARY_PATH = Path(__file__).resolve().parent / "truth" / "hm3d_semantic_summary.json"
LIVE_POLICY_PATH = Path(__file__).resolve().parent.parent / "live_policy.py"
EXCLUDED_HOUSES = frozenset({"00853", "00871"})  # the two test houses (§9)
N_PLACEBO_MEMBERS = 4
KINDS = ("room", "object")


# ------------------------------------------------------------------------------------ seeds

def stable_seed(row_id: str, member: int, name: str) -> int:
    """A 64-bit seed from (row_id, member, comparator name). Stable across runs and machines."""
    text = f"{row_id}\x1f{int(member)}\x1f{name}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(text).digest()[:8], "big")


# ------------------------------------------------------------------------------- the prior

def _share_above(counts: Sequence[int], m: int) -> float:
    """Share of houses with N > m among those with N >= m; 0 if no house has N >= m."""
    ge = [n for n in counts if n >= m]
    if not ge:
        return 0.0
    return sum(1 for n in ge if n > m) / len(ge)


class Prior:
    """The other-house prior B3 (§9). Houses are counted once by number; 00853 and 00871 are left out.

    N_T counts regions of the type (marker_types over the region's category names). N_c counts the
    house's objects that answer to c: an object adds one to every class in labels.answers_to(name).
    Region ids below 0 (objects with no region) hold no room, so they add no N_T; their objects
    still count in N_c.
    """

    def __init__(self, summary_path=SUMMARY_PATH, include_extended: bool = True):
        self.include_extended = include_extended
        with open(summary_path) as f:
            data = json.load(f)
        seen = set()
        houses = []
        for h in data["houses"]:
            number = str(h["number"])
            if number in seen or number in EXCLUDED_HOUSES:
                continue
            seen.add(number)
            houses.append(h)
        self.n_houses = len(houses)
        ans_cache: Dict[str, FrozenSet[str]] = {}
        mark_cache: Dict[str, FrozenSet[str]] = {}

        def answers(name: str) -> FrozenSet[str]:
            if name not in ans_cache:
                got = labels.answers_to(name) if include_extended else labels.answers_to(name, include_extended=False)
                ans_cache[name] = frozenset(c for c in got if not labels.is_structure(c))
            return ans_cache[name]

        def marks(name: str) -> FrozenSet[str]:
            if name not in mark_cache:
                mark_cache[name] = frozenset(labels.marker_types(name))
            return mark_cache[name]

        self.room_n: Dict[str, List[int]] = {t: [] for t in model.REPORTED_ROOM_TYPES}
        class_n: List[Dict[str, int]] = []
        self.n_regions: List[int] = [sum(1 for rid in h["regions"] if int(rid) >= 0) for h in houses]
        for h in houses:
            n_t = {t: 0 for t in model.REPORTED_ROOM_TYPES}
            n_c: Dict[str, int] = {}
            for rid, cats in h["regions"].items():
                types = set()
                for name, cnt in cats.items():
                    types |= marks(name)
                    for c in answers(name):  # one count per class the object answers to (§5.3)
                        n_c[c] = n_c.get(c, 0) + int(cnt)
                if int(rid) >= 0:
                    for t in types:
                        if t in n_t:
                            n_t[t] += 1
            for t in n_t:
                self.room_n[t].append(n_t[t])
            class_n.append(n_c)
        universe = set(labels.canonical_classes())
        for d in class_n:
            universe |= set(d)
        self.class_n: Dict[str, List[int]] = {c: [d.get(c, 0) for d in class_n] for c in sorted(universe)}
        self.holders: Dict[str, Dict[str, int]] = {
            "room": {t: sum(1 for n in v if n >= 1) for t, v in self.room_n.items()},
            "object": {c: sum(1 for n in v if n >= 1) for c, v in self.class_n.items()},
        }

    # §9 rooms: m_T is presence (0 or 1) of a typed room node in the observed graph.
    # `counts` (type -> m_T) replaces it in the sensitivity form of §9 that knows the truly seen regions;
    # `houses` (indices) limits the houses, for the house-size form.
    def room_scores(self, observed, include_dining: bool = False, counts: Optional[Mapping[str, int]] = None,
                    houses: Optional[Sequence[int]] = None) -> Dict[str, float]:
        present = {n.room_type for n in observed.rooms if n.room_type}
        types = model.REPORTED_ROOM_TYPES if include_dining else model.ROOM_TYPES

        def m_of(t):
            return int(counts.get(t, 0)) if counts is not None else (1 if t in present else 0)

        return {t: _share_above(self._pick(self.room_n[t], houses), m_of(t)) for t in types}

    # §9 objects: n_c is the number of observed object nodes of the class (or `counts`, the number of
    # mapped reference objects of the class, in the sensitivity form).
    def class_scores(self, observed, counts: Optional[Mapping[str, int]] = None,
                     houses: Optional[Sequence[int]] = None) -> Dict[str, float]:
        n = Counter(o.canon for o in observed.objects if o.canon) if counts is None else counts
        return {c: _share_above(self._pick(v, houses), int(n.get(c, 0))) for c, v in self.class_n.items()}

    @staticmethod
    def _pick(values: Sequence[int], houses: Optional[Sequence[int]]) -> Sequence[int]:
        return values if houses is None else [values[i] for i in houses]

    def size_third(self, n_regions: int) -> Tuple[int, ...]:
        """Indices of the houses in the same third, by number of regions, as a house with `n_regions`
        (§9 sensitivity). The cuts are the 1/3 and 2/3 percentiles of the houses' region counts; a
        house falls in third (n > cut1) + (n > cut2)."""
        c1, c2 = (float(x) for x in np.percentile(self.n_regions, [100.0 / 3.0, 200.0 / 3.0]))

        def third(n):
            return int(n > c1) + int(n > c2)

        t = third(n_regions)
        return tuple(i for i, n in enumerate(self.n_regions) if third(n) == t)

    def top_k(self, scores: Mapping[str, float], k: int, kind: str,
              allowed: Optional[Iterable[str]] = None) -> List[str]:
        """The k best labels: score, then houses holding it (N >= 1), then alphabetical. `allowed`
        limits the labels (the detector vocabulary, in the §11 line on it)."""
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}")
        held = self.holders[kind]
        keep = None if allowed is None else set(allowed)
        names = [lab for lab in scores if keep is None or lab in keep]
        order = sorted(names, key=lambda lab: (-scores[lab], -held.get(lab, 0), lab))
        return order[:max(0, int(k))]


def b3_claims(prior: Prior, observed, k: int, level: str, allowed: Optional[Iterable[str]] = None,
              counts: Optional[Mapping[str, int]] = None, houses: Optional[Sequence[int]] = None) -> FrozenSet[str]:
    if level == "L1":
        return frozenset(prior.top_k(prior.room_scores(observed, counts=counts, houses=houses), k, "room"))
    if level == "L2":
        return frozenset(prior.top_k(prior.class_scores(observed, counts=counts, houses=houses), k, "object", allowed))
    raise ValueError("B3 claims exist at L1 and L2 only")


def b3_member(prior: Prior, observed, member, allowed: Optional[Iterable[str]] = None,
              room_counts: Optional[Mapping[str, int]] = None, class_counts: Optional[Mapping[str, int]] = None,
              houses: Optional[Sequence[int]] = None) -> "model.Member":
    """B3: as many claims as the member made at each level; no L3 items. `allowed` limits the L2 labels
    (detector vocabulary); `room_counts`, `class_counts` and `houses` give the sensitivity forms."""
    return model.Member(
        member=member.member, new_rooms=(), new_objects=(),
        l1_claims=frozenset(prior.top_k(prior.room_scores(observed, counts=room_counts, houses=houses),
                                        len(member.l1_claims), "room")),
        l2_claims=frozenset(prior.top_k(prior.class_scores(observed, counts=class_counts, houses=houses),
                                        len(member.l2_claims), "object", allowed)),
        l3_items=(),
    )


def b3l_items(prior: Prior, observed, member, allowed: Optional[Iterable[str]] = None) -> Tuple["model.Item", ...]:
    """B3L: rank the member's distinct labels of each kind by frequency (ties alphabetical);
    the i-th is replaced everywhere by the prior's i-th label of that kind. Centres are kept.
    Rooms are ranked over the five scored types (§9: "at L1 the labels are the five scored room types";
    a dining room is never an item, item 51). Objects over the canonical classes, or over `allowed`.
    An item whose rank exceeds the prior's list is dropped."""
    mapping: Dict[str, Dict[str, str]] = {}
    for kind in KINDS:
        counts = Counter(it.label for it in member.l3_items if it.kind == kind)
        ranked = sorted(counts, key=lambda lab: (-counts[lab], lab))
        if kind == "room":
            scores, keep = prior.room_scores(observed), None
        else:
            scores, keep = prior.class_scores(observed), allowed
        repl = prior.top_k(scores, len(ranked), kind, keep)
        mapping[kind] = {lab: repl[i] for i, lab in enumerate(ranked) if i < len(repl)}
    out = []
    for it in member.l3_items:
        new = mapping[it.kind].get(it.label)
        if new is not None:
            out.append(model.Item(kind=it.kind, label=new, xy=it.xy))
    return tuple(out)


def b3l_member(prior: Prior, observed, member, allowed: Optional[Iterable[str]] = None) -> "model.Member":
    return model.Member(member=member.member, new_rooms=(), new_objects=(),
                        l1_claims=frozenset(), l2_claims=frozenset(),
                        l3_items=b3l_items(prior, observed, member, allowed))


def seen_counts(truth, state) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Counts for the §9 sensitivity form that knows what the robot truly saw (§5.4): (m_T, n_c) with m_T
    the number of seen regions of type T and n_c the number of mapped reference objects that answer to c."""
    room_m: Dict[str, int] = {}
    for rid in state.seen:
        for t in truth.regions[rid].types:
            room_m[t] = room_m.get(t, 0) + 1
    class_n: Dict[str, int] = {}
    for reg in truth.regions.values():
        for o in reg.ref_objects:
            if o.object_id in state.mapped_objects:
                for c in o.answers_to:
                    class_n[c] = class_n.get(c, 0) + 1
    return room_m, class_n


def b2_member(observed, member: int = 0) -> "model.Member":
    """B2 (reported only): claim the types and classes already observed."""
    scored = set(model.ROOM_TYPES)
    return model.Member(
        member=member, new_rooms=(), new_objects=(),
        l1_claims=frozenset(n.room_type for n in observed.rooms if n.room_type in scored),
        l2_claims=frozenset(n.canon for n in observed.objects if n.canon),
        l3_items=(),
    )


# ---------------------------------------------------------------------- B5 and D (L3)

def _reached(items, truth, state) -> List[Tuple[int, ...]]:
    unobs = state.unobserved
    return [tuple(sorted(r for r in truth.reaches(it.xy) if r in unobs)) for it in items]


def _region_content(truth, region_ids: Iterable[int]) -> Dict[int, Tuple[FrozenSet[str], FrozenSet[str]]]:
    out = {}
    for rid in region_ids:
        reg = truth.regions[rid]
        out[rid] = (frozenset(reg.types), score_levels.region_classes(reg))
    return out


def _holds(content: Tuple[FrozenSet[str], FrozenSet[str]], kind: str, label: str) -> bool:
    return label in (content[0] if kind == "room" else content[1])


def b5_l3(member, truth, state, draws: int = 1000, *, seed: int) -> Optional[float]:
    """B5: mean L3 hit share over `draws` seeded permutations of the member's labels among its
    items of the same kind (centres kept). None if the member has no item."""
    items = list(member.l3_items)
    if not items:
        return None
    reached = _reached(items, truth, state)
    content = _region_content(truth, {r for rs in reached for r in rs})
    memo: Dict[Tuple[int, str], bool] = {}

    def hit(i: int, label: str) -> bool:
        key = (i, label)
        if key not in memo:
            memo[key] = any(_holds(content[r], items[i].kind, label) for r in reached[i])
        return memo[key]

    by_kind = {k: [i for i, it in enumerate(items) if it.kind == k] for k in KINDS}
    rng = np.random.default_rng(int(seed))
    total = 0.0
    for _ in range(int(draws)):
        hits = 0
        for kind in KINDS:
            idx = by_kind[kind]
            if not idx:
                continue
            labs = [items[i].label for i in idx]
            perm = rng.permutation(len(labs))
            hits += sum(1 for j, i in enumerate(idx) if hit(i, labs[int(perm[j])]))
        total += hits / len(items)
    return total / int(draws)


def random_derangement(n: int, rng) -> np.ndarray:
    """A uniform random permutation of range(n) with no fixed point (rejection). n >= 2."""
    if n < 2:
        raise ValueError("a derangement needs at least 2 elements")
    ident = np.arange(n)
    while True:
        perm = rng.permutation(n)
        if not np.any(perm == ident):
            return perm


def d_l3(member, truth, state, draws: int = 200, *, seed: int) -> Optional[float]:
    """D: mean L3 hit share over `draws` seeded derangements of the unobserved regions, where an
    item is a hit if it reaches R with sigma(R) of its type / holding its class. None if fewer
    than 2 unobserved regions, or if the member has no item."""
    regions = sorted(state.unobserved)
    items = list(member.l3_items)
    if len(regions) < 2 or not items:
        return None
    reached = _reached(items, truth, state)
    content = _region_content(truth, regions)
    rng = np.random.default_rng(int(seed))
    total = 0.0
    for _ in range(int(draws)):
        perm = random_derangement(len(regions), rng)
        sigma = {regions[i]: regions[int(perm[i])] for i in range(len(regions))}
        hits = sum(1 for it, rs in zip(items, reached) if any(_holds(content[sigma[r]], it.kind, it.label) for r in rs))
        total += hits / len(items)
    return total / int(draws)


# the names of the model.py contract
b5_score = b5_l3
d_score = d_l3


# ------------------------------------------------------------------------------ B1 placebo

def b1_members(row, placebo_fn: Callable, n_members: int = N_PLACEBO_MEMBERS) -> List["model.Member"]:
    """Four placebo draws on the row's observed graph. `placebo_fn(row, k)` returns the Member
    for draw k. The real one is `make_placebo_fn(...)`."""
    return [placebo_fn(row, k) for k in range(n_members)]


def _load_live_policy():
    key = "_semantic_sibling_live_policy"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, LIVE_POLICY_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


def placebo_rng_key(row, k: int) -> List[int]:
    """Seed of the live placebo arm for a first attempt of a plain run, track 0: the numpy seed
    list [run seed, stage number, graph id], where graph id = track * ensemble + member = k.
    (live_policy.no_llm_completions adds [attempt] after a retry and [attempt, rerun] for a rerun
    directory; neither applies to a frame row. numpy seeds [a, b] and [a, b, 0] alike.)"""
    return [int(row.seed), int(row.stage), int(k)]


def reduce_via_extract_preds(extract_preds) -> Callable:
    """Glue: write the placebo's graph dict to a temporary YAML and read it back through
    extract_preds.read_member(path, row.observed, k), the reduction every model's member gets."""
    def reduce(graph, row, k):
        import yaml
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"placebo_{row.row_id}_{k}.yaml"
            with open(path, "w") as f:
                yaml.safe_dump(graph, f)
            return extract_preds.read_member(path, row.observed, k)
    return reduce


def make_placebo_fn(read_observed_raw: Callable, reduce_graph: Callable, calib: Optional[dict] = None) -> Callable:
    """The real `placebo_fn` for b1_members.

    read_observed_raw(row) -> dict: the track-0 observed graph exactly as live_policy loads it,
        yaml.safe_load of habitat_scene_graph_original_graph0.yaml: {"nodes": [...], "edges": [...]}.
    reduce_graph(graph, row, k) -> Member: e.g. reduce_via_extract_preds(extract_preds).
    The call is live_policy.placebo_graph(observed, np.random.default_rng([seed, stage, k]), calib)
    with calib = live_policy.load_calibration() (tools/live_policy/placebo_calibration.json).
    """
    def placebo_fn(row, k):
        lp = _load_live_policy()
        cal = calib if calib is not None else lp.load_calibration()
        graph = lp.placebo_graph(read_observed_raw(row), np.random.default_rng(placebo_rng_key(row, k)), cal)
        return reduce_graph(graph, row, k)
    return placebo_fn


def placebo_graphs(row, read_observed_raw: Callable, calib: Optional[dict] = None,
                   n_members: int = N_PLACEBO_MEMBERS) -> List[dict]:
    """The placebo's four graphs for a row, as live_policy.placebo_graph makes them:
    placebo_graph(observed, np.random.default_rng([seed, stage, k]), load_calibration()), k = 0..3."""
    lp = _load_live_policy()
    cal = calib if calib is not None else lp.load_calibration()
    observed = read_observed_raw(row)
    return [lp.placebo_graph(observed, np.random.default_rng(placebo_rng_key(row, k)), cal) for k in range(n_members)]


# ----------------------------------------------------------------------------- B4 wrong house

def b4_partner(row, rows: Iterable):
    """The row of the other scene with the same seed, arm and stage; None for a Gemini row or when
    the frame holds none. Two candidates is an error."""
    if row.is_gemini_row:
        return None
    found = [r for r in rows if r.scene != row.scene and not r.is_gemini_row
             and r.seed == row.seed and r.arm == row.arm and r.stage == row.stage]
    if len(found) > 1:
        raise ValueError(f"row {row.row_id}: {len(found)} partner rows")
    return found[0] if found else None


def b4_scores(row, rows: Iterable, members_by_row: Mapping[str, Sequence], truth, state) -> Dict[str, Dict[str, Optional[float]]]:
    """B4: the partner row's members (of the same model) scored against THIS row's truth and state.
    Returns {partner member id: {"L1","L2","L3": share or None}}; {} if there is no partner row or
    the model holds no member on it. The row score is the mean over these members."""
    partner = b4_partner(row, rows)
    if partner is None:
        return {}
    out = {}
    for m in members_by_row.get(partner.row_id, ()):
        out[str(m.member)] = score_levels.member_rates(score_levels.score_member(m, truth, state, row.observed))
    return out
