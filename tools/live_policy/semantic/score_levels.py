"""Level scores L1, L2, L3 of the pre-registered semantic test (PREREGISTRATION_SEMANTIC.md §8, §11).

Every function takes the dataclasses of model.py and nothing else. Truth is a SceneTruth,
the robot's state is a StageState, a guess is a Member.

Sibling modules (model, labels) load through `_sibling`, so the file works both as part of a
package and when a test loads it by path. `labels` is a module attribute so that a test can
swap in a fake.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import AbstractSet, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


def _sibling(name: str):
    pkg = __package__
    if pkg:
        return importlib.import_module(f"{pkg}.{name}")
    key = f"_semantic_sibling_{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, Path(__file__).with_name(f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod  # dataclasses look the module up by name
    spec.loader.exec_module(mod)
    return mod


class _Lazy:
    """Module stand-in that imports on first attribute access (sibling files may not exist yet)."""

    def __init__(self, name: str):
        self._name = name
        self._mod = None

    def __getattr__(self, attr: str):
        if self._mod is None:
            self._mod = _sibling(self._name)
        return getattr(self._mod, attr)


model = _sibling("model")
labels = _Lazy("labels")

LEVELS = ("L1", "L2", "L3")
DET_NOTE = "objects only: rooms are not in the detector vocabulary"
L4_RADII_M = (0.5, 1.0, 2.0, 3.0)


# ------------------------------------------------------------------------------ L3 hit rule

def region_classes(region) -> frozenset:
    """Every class a reference object of the region answers to (§5.3)."""
    out = set()
    for o in region.ref_objects:
        out |= o.answers_to
    return frozenset(out)


def _region_matches(region, item) -> bool:
    if item.kind == "room":
        return item.label in region.types
    return item.label in region_classes(region)


def _item_hit(item, truth, region_ids: AbstractSet[int], holder: Optional[Mapping[int, int]] = None) -> bool:
    """Does the item reach a region of `region_ids` whose content (or its holder's) matches?"""
    for rid in truth.reaches(item.xy):
        if rid not in region_ids:
            continue
        judged = holder[rid] if holder is not None else rid
        if _region_matches(truth.regions[judged], item):
            return True
    return False


def l3_hit(item, truth, state, holder: Optional[Mapping[int, int]] = None) -> bool:
    """§8: the item reaches an unobserved region that is of its type (room) or holds a
    reference object of its class (object). With `holder` (region -> region), region R is
    judged by what holder[R] is and holds (the derangement of §9)."""
    return _item_hit(item, truth, state.unobserved, holder)


# ------------------------------------------------------------------------------- possibility

def possible(level: str, truth, state) -> bool:
    """§8, last sentence: can any hit occur at this level on this row?
    L1: some type is open. L2: some class is open. L3: some region is unobserved."""
    if level == "L1":
        # dining is reported, never scored (§5.2, §7): an open dining room makes no hit possible
        return bool(set(state.open_types) & set(model.ROOM_TYPES))
    if level == "L2":
        return bool(state.open_classes)
    if level == "L3":
        return bool(state.unobserved)
    raise ValueError(f"unknown level {level!r}")


# ------------------------------------------------------------------------- member score

def _put(extra: Dict[str, float], key: str, hits: float, n: int) -> None:
    extra[f"{key}_n"] = float(n)
    if n > 0:
        extra[key] = hits / n


def _open_regions(truth, state, room_type: str, observed=None) -> List[int]:
    """§5.5: unseen regions of the type with none of their markers of the type mapped and, when
    `observed` is given, no observed room node of the type reaching them."""
    covered = set()
    if observed is not None:
        for n in observed.rooms:
            if n.room_type == room_type:
                covered |= set(truth.reaches(n.xy))
    out = []
    for rid in sorted(state.unseen):
        region = truth.regions[rid]
        if room_type not in region.types or rid in covered:
            continue
        if not any(room_type in m.types and m.object_id in state.mapped_objects for m in region.markers):
            out.append(rid)
    return out


def _max_matching(adj: Sequence[Sequence[int]], n_right: int) -> int:
    """Size of a maximum bipartite matching (augmenting paths)."""
    match_right = [-1] * n_right

    def try_left(u: int, seen: List[bool]) -> bool:
        for v in adj[u]:
            if seen[v]:
                continue
            seen[v] = True
            if match_right[v] == -1 or try_left(match_right[v], seen):
                match_right[v] = u
                return True
        return False

    return sum(1 for u in range(len(adj)) if try_left(u, [False] * n_right))


def _l1_matched(member, truth, state, observed=None) -> Tuple[int, int]:
    """§11: each new room with a scored type is a claim; it needs its own open region."""
    scored = set(model.ROOM_TYPES)
    claims = [n.room_type for n in member.new_rooms if n.room_type in scored]
    if not claims:
        return 0, 0
    if state.open_type_regions or not state.open_types:   # §5.5 as stage_state computed it, second rule included
        open_by_type = {t: sorted(state.open_type_regions.get(t, ())) for t in set(claims)}
    else:                            # a state built by hand
        open_by_type = {t: _open_regions(truth, state, t, observed) for t in set(claims)}
    regions = sorted({r for rs in open_by_type.values() for r in rs})
    index = {r: i for i, r in enumerate(regions)}
    adj = [[index[r] for r in open_by_type[t]] for t in claims]
    return _max_matching(adj, len(regions)), len(claims)


def unmapped_unseen_targets(truth, state) -> Dict[str, List[Tuple[float, float]]]:
    """Class -> centres of the reference objects that answer to it, are not mapped, and lie in an unseen
    region (§11 L4; §4 F3-m of PREREGISTRATION_M2.md)."""
    targets: Dict[str, List[Tuple[float, float]]] = {}
    for rid in sorted(state.unseen):
        for o in truth.regions[rid].ref_objects:
            if o.object_id not in state.mapped_objects:
                for c in o.answers_to:
                    targets.setdefault(c, []).append(o.xy)
    return targets


def placement_errors(member, truth, state) -> Tuple[List[float], int]:
    """The error sample of PREREGISTRATION_M2.md §4 F3-m, for one member of one row: for each new object
    with a canonical class (not "other", not a structure class), the horizontal distance in metres from its
    centre to the nearest unmapped reference object that answers to its class in an unseen region. Returns
    (distances, number of such guesses left out because the scene holds no such reference object)."""
    targets = unmapped_unseen_targets(truth, state)
    dists: List[float] = []
    left_out = 0
    for n in member.new_objects:
        if not n.canon:
            continue
        pts = targets.get(n.canon)
        if not pts:
            left_out += 1
            continue
        dists.append(min(((n.xy[0] - x) ** 2 + (n.xy[1] - y) ** 2) ** 0.5 for x, y in pts))
    return dists, left_out


def _l4(member, truth, state) -> Dict[str, float]:
    """§11 L4: share of new objects within 0.5, 1, 2, 3 m of an unmapped reference object that
    answers to the same class, in an unseen region."""
    targets = unmapped_unseen_targets(truth, state)
    objs = [n for n in member.new_objects if n.canon]
    out: Dict[str, float] = {}
    for radius in L4_RADII_M:
        hits = 0
        for n in objs:
            r2 = radius * radius
            if any((n.xy[0] - x) ** 2 + (n.xy[1] - y) ** 2 <= r2 for x, y in targets.get(n.canon, ())):
                hits += 1
        _put(out, "l4_" + str(radius).replace(".", "p") + "m", hits, len(objs))
    return out


def member_rates(ms) -> Dict[str, Optional[float]]:
    """{"L1": share or None, "L2": ..., "L3": ...} of a MemberScore."""
    return {lv: ms.rate(lv) for lv in LEVELS}


def score_member(member, truth, state, observed=None) -> "model.MemberScore":
    """§8 hits and counts at the three levels, plus the §11 readouts that need no other module.
    `observed` (the row's ObservedGraph) is optional: it only serves l1_matched, where an observed
    room node of the type reaching a region closes it (§5.5); without it that clause is skipped.

    `extra` keys (each with a count under key + "_n"; the share is absent when the count is 0):
      l1_loose, l2_loose        a claim needs only an unseen region of the type / holding the class
      l3_partly                 L3 items reaching a partly seen region of their type / class
      l3_rooms, l3_objects      primary L3 rule, for each kind apart (n counts that kind's items)
      l2_det, l3_det            claims / items restricted to the detector vocabulary (L3: objects only)
      l1_matched                one new room (a claim) matched to one open region
      l3_multi, l3_multi_unobs  share of L3 items that reach two or more regions (any region /
                                unobserved regions only; §8)
      l4_0p5m, l4_1p0m, l4_2p0m, l4_3p0m          share of new objects within r metres of an unmapped same-class
                                reference object in an unseen region
    """
    ms = model.MemberScore(member=member.member)
    ms.l1_n = len(member.l1_claims)
    ms.l1_hits = sum(1 for t in member.l1_claims if t in state.open_types)
    ms.l2_n = len(member.l2_claims)
    ms.l2_hits = sum(1 for c in member.l2_claims if c in state.open_classes)
    items = list(member.l3_items)
    ms.l3_n = len(items)
    ms.l3_hits = float(sum(1 for it in items if l3_hit(it, truth, state)))

    ex = ms.extra
    _put(ex, "l1_loose", sum(1 for t in member.l1_claims if t in state.open_types_loose), len(member.l1_claims))
    _put(ex, "l2_loose", sum(1 for c in member.l2_claims if c in state.open_classes_loose), len(member.l2_claims))
    _put(ex, "l3_partly", sum(1 for it in items if _item_hit(it, truth, state.partly_seen)), len(items))
    for kind, key in (("room", "l3_rooms"), ("object", "l3_objects")):
        sub = [it for it in items if it.kind == kind]
        _put(ex, key, sum(1 for it in sub if l3_hit(it, truth, state)), len(sub))
    vocab = labels.detector_vocab()
    det_claims = [c for c in member.l2_claims if c in vocab]
    _put(ex, "l2_det", sum(1 for c in det_claims if c in state.open_classes), len(det_claims))
    det_items = [it for it in items if it.kind == "object" and it.label in vocab]
    _put(ex, "l3_det", sum(1 for it in det_items if l3_hit(it, truth, state)), len(det_items))
    hits, n = _l1_matched(member, truth, state, observed)
    _put(ex, "l1_matched", hits, n)
    unobs = state.unobserved
    _put(ex, "l3_multi", sum(1 for it in items if len(truth.reaches(it.xy)) >= 2), len(items))
    _put(ex, "l3_multi_unobs", sum(1 for it in items if len(set(truth.reaches(it.xy)) & unobs) >= 2), len(items))
    ex.update(_l4(member, truth, state))
    return ms
