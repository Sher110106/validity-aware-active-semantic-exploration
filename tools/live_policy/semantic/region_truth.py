"""Truth of each scene, and what the robot has seen at a stage (PREREGISTRATION_SEMANTIC.md §5).

    load_scene_truth(scene, truth_dir=TRUTH_DIR) -> SceneTruth     §5.1 to §5.3
    stage_state(truth, row)                       -> StageState    §5.4, §5.5, and the loose sets of §11

Distance rule (used by `distance` and `reaches`). A footprint is a set of 0.05 m grid cells; cell
(ix, iy) is the square [ox + ix*cs, ox + (ix+1)*cs) x [oy + iy*cs, oy + (iy+1)*cs). A point is inside
a region if its cell is set in the region's `any` mask. Otherwise its distance to the region is the
exact Euclidean distance from the point to the nearest point of any set cell's square. A point
outside the grid is inside nothing and its distance is computed the same way. The error against the
rule is zero, so it is inside the half-cell bound the brief allows. A KD-tree over the set cells'
centres finds the candidates; a distance transform cannot hold that bound (its error is up to
one cell diagonal / 2 = 0.035 m, more than half a cell).

Sibling modules load by file path: `tools/live_policy` has no `__init__.py` and also holds a
`live_policy.py`, so a package import is not safe. The label layer is the module attribute
`labels`; tests may swap it.
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent


def _sibling(name: str):
    """Load a module of this folder. Returns None if the file does not exist yet."""
    key = f"semantic_{name}"
    if key in sys.modules:
        return sys.modules[key]
    path = HERE / f"{name}.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(key, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod  # dataclasses look the module up by name
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(key, None)  # never leave a half-built module behind
        raise
    return mod


def _optional_sibling(name: str):
    """Like _sibling, but a module that fails to load (for example, its table file is missing) gives None."""
    try:
        return _sibling(name)
    except Exception as exc:  # noqa: BLE001 - reported by _need_labels
        _LOAD_ERRORS[name] = exc
        return None


_LOAD_ERRORS: Dict[str, Exception] = {}
model = _sibling("model")
labels = _optional_sibling("labels")  # swap in tests: region_truth.labels = FakeLabels

Point = Tuple[float, float]
TRUTH_DIR = HERE / "truth"

REACH_EPS = 1e-9


def _need_labels():
    if labels is None:
        why = _LOAD_ERRORS.get("labels")
        raise ImportError(f"semantic/labels.py is missing or failed to load ({why!r}) and region_truth.labels was not set")
    return labels


def _canon_of(raw_name: str) -> Optional[str]:
    """Canonical class of the raw name alone, or None if "other" or a structure class (§6)."""
    lab = _need_labels()
    c = lab.normalise(raw_name)
    if c is None or lab.is_structure(c):
        return None
    return c


def _answers_to(raw_name: str, include_extended: bool = True) -> FrozenSet[str]:
    """§5.3: the non-structure classes an annotated object answers to (labels.answers_to; structure
    classes are dropped again here, so a label layer that forgets cannot let one through).
    include_extended=False is the §11 sensitivity rule (synonym_primary alone)."""
    lab = _need_labels()
    got = lab.answers_to(raw_name) if include_extended else lab.answers_to(raw_name, include_extended=False)
    return frozenset(c for c in got if c is not None and not lab.is_structure(c))


def _centre(obj: dict) -> Optional[Point]:
    """Midpoint of world_min and world_max, or None if the object has no geometry."""
    if not obj.get("n_tri"):
        return None
    lo, hi = obj.get("world_min"), obj.get("world_max")
    if lo is None or hi is None or len(lo) < 2 or len(hi) < 2:
        return None
    return (0.5 * (float(lo[0]) + float(hi[0])), 0.5 * (float(lo[1]) + float(hi[1])))


class GridSceneTruth(model.SceneTruth):
    """SceneTruth on the footprint grid. Build it with load_scene_truth."""

    def __init__(self, scene: str, regions: Dict[int, "model.Region"], origin_xy, cell_size: float,
                 region_ids, any_masks: np.ndarray, skipped_objects: int = 0,
                 floor_masks: Optional[np.ndarray] = None):
        self.scene = scene
        self.regions = regions
        self.skipped_objects = skipped_objects      # annotated objects whose region is not in the grid
        self._ox, self._oy = float(origin_xy[0]), float(origin_xy[1])
        self._cs = float(cell_size)
        self._ids = np.asarray(region_ids, dtype=int)
        self._masks = np.asarray(any_masks, dtype=bool)         # [region, iy, ix]
        # path rule of §5.4: the floor mask; a region with no floor cell uses its `any` mask
        fl = self._masks.copy() if floor_masks is None else np.asarray(floor_masks, dtype=bool).copy()
        self.regions_without_floor = []
        for i, rid in enumerate(self._ids):
            if not fl[i].any():
                fl[i] = self._masks[i]
                self.regions_without_floor.append(int(rid))
        self._floor = fl
        self._ny, self._nx = self._masks.shape[1], self._masks.shape[2]
        self._index = {int(r): i for i, r in enumerate(self._ids)}
        self._trees: Dict[int, Optional[cKDTree]] = {}
        self._bbox: Dict[int, Optional[Tuple[float, float, float, float]]] = {}
        self._cells: Dict[int, np.ndarray] = {}
        h = 0.5 * self._cs
        for rid, i in self._index.items():
            iy, ix = np.nonzero(self._masks[i])
            if len(ix) == 0:
                self._trees[rid], self._bbox[rid] = None, None
                continue
            cx = self._ox + (ix + 0.5) * self._cs
            cy = self._oy + (iy + 0.5) * self._cs
            pts = np.column_stack([cx, cy])
            self._cells[rid] = pts
            self._trees[rid] = cKDTree(pts)
            self._bbox[rid] = (cx.min() - h, cy.min() - h, cx.max() + h, cy.max() + h)

    # ------------------------------------------------------------------ geometry
    def _cell(self, p: Point) -> Optional[Tuple[int, int]]:
        x, y = float(p[0]), float(p[1])
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError(f"non-finite point {p!r}")
        ix = math.floor((x - self._ox) / self._cs)
        iy = math.floor((y - self._oy) / self._cs)
        if 0 <= ix < self._nx and 0 <= iy < self._ny:
            return ix, iy
        return None

    def inside(self, p: Point) -> FrozenSet[int]:
        c = self._cell(p)
        if c is None:
            return frozenset()
        ix, iy = c
        return frozenset(int(r) for r in self._ids[self._masks[:, iy, ix]])

    def inside_floor(self, p: Point) -> FrozenSet[int]:
        """Regions whose floor mask holds p (the `any` mask for a region with no floor). §5.4, paths only."""
        c = self._cell(p)
        if c is None:
            return frozenset()
        ix, iy = c
        return frozenset(int(r) for r in self._ids[self._floor[:, iy, ix]])

    def _square_distance(self, p: Point, rid: int) -> float:
        tree = self._trees.get(rid)
        if tree is None:
            return math.inf
        x, y = float(p[0]), float(p[1])
        h = 0.5 * self._cs
        dc, _ = tree.query([x, y])
        # a square at centre-distance c lies at least c - h*sqrt(2) away; the nearest centre's square
        # lies at most dc away, so only centres within dc + h*sqrt(2) can hold the nearest square
        idx = tree.query_ball_point([x, y], dc + h * math.sqrt(2.0) + 1e-9)
        pts = self._cells[rid][idx]
        dx = np.maximum(np.abs(pts[:, 0] - x) - h, 0.0)
        dy = np.maximum(np.abs(pts[:, 1] - y) - h, 0.0)
        return float(np.sqrt(dx * dx + dy * dy).min())

    def distance(self, p: Point, region_id: int) -> float:
        if region_id not in self._index:
            raise KeyError(f"unknown region {region_id}")
        if region_id in self.inside(p):
            return 0.0
        return self._square_distance(p, region_id)

    def reaches(self, p: Point) -> FrozenSet[int]:
        out = set(self.inside(p))
        x, y = float(p[0]), float(p[1])
        r = model.REACH_M + REACH_EPS
        for rid, box in self._bbox.items():
            if rid in out or box is None:
                continue
            if x < box[0] - r or x > box[2] + r or y < box[1] - r or y > box[3] + r:
                continue
            if self._square_distance(p, rid) <= r:
                out.add(rid)
        return frozenset(out)


def load_scene_truth(scene: str, truth_dir: Path = TRUTH_DIR, include_extended: bool = True) -> "GridSceneTruth":
    """Read `<scene>_region_footprints.npz`, `<scene>_semantic_geometry.json`, `<scene>_regions.json`.
    include_extended=False builds "answers to" from `synonym_primary` alone (§11 sensitivity)."""
    truth_dir = Path(truth_dir)
    lab = _need_labels()
    z = np.load(truth_dir / f"{scene}_region_footprints.npz", allow_pickle=False)
    cs = float(z["cell_size"])
    region_ids = [int(r) for r in z["region_ids"]]
    any_masks = z["any_masks"]
    origin = z["origin_xy"]
    geom = json.loads((truth_dir / f"{scene}_semantic_geometry.json").read_text())
    regions_json = json.loads((truth_dir / f"{scene}_regions.json").read_text())
    json_centroid = {int(r["region_id"]): r.get("centroid_xy") for r in regions_json.get("regions", [])}

    markers: Dict[int, List] = {r: [] for r in region_ids}
    refs: Dict[int, List] = {r: [] for r in region_ids}
    skipped = 0
    for obj in sorted(geom["objects"].values(), key=lambda o: int(o["id"])):
        rid = obj.get("region")
        if rid is None or int(rid) not in markers:
            skipped += 1
            continue
        rid = int(rid)
        oid = int(obj["id"])
        name = str(obj["name"])
        xy = _centre(obj)
        answers = _answers_to(name, include_extended)
        mt = frozenset(lab.marker_types(name))
        if mt:
            markers[rid].append(model.Marker(object_id=oid, region_id=rid, raw_name=name, types=mt,
                                             answers_to=answers, xy=xy))
        if xy is not None and answers:
            refs[rid].append(model.RefObject(object_id=oid, region_id=rid, raw_name=name, answers_to=answers,
                                             xy=xy, canon=_canon_of(name), marker_of=mt))

    regions: Dict[int, "model.Region"] = {}
    for i, rid in enumerate(region_ids):
        c = json_centroid.get(rid)       # §11: the `centroid_xy` field of <scene>_regions.json
        if c is not None and len(c) >= 2:
            cen = (float(c[0]), float(c[1]))
        else:                            # field absent: the footprint centroid (not seen in either scene)
            iy, ix = np.nonzero(any_masks[i])
            cen = ((float(origin[0] + (ix.mean() + 0.5) * cs), float(origin[1] + (iy.mean() + 0.5) * cs))
                   if len(ix) else (math.nan, math.nan))
        types = frozenset(t for m in markers[rid] for t in m.types)
        regions[rid] = model.Region(region_id=rid, types=types, centroid_xy=cen,
                                    ref_objects=tuple(refs[rid]), markers=tuple(markers[rid]))
    return GridSceneTruth(scene, regions, origin, cs, region_ids, any_masks, skipped_objects=skipped,
                          floor_masks=z["floor_masks"])


# ------------------------------------------------------------------------------ stage state

def stage_state(truth: "SceneTruth", row: "model.Row") -> "model.StageState":
    """§5.4 and §5.5 for one row, and the loose sets of §11.

    Mapped: an observed OBJECT node (the graph holds object nodes only) whose canonical class is in the
    reference object's (or marker's) `answers_to` lies within 0.5 m of its centre. A marker with no
    geometry or an empty `answers_to` is never mapped.
    Seen: a path point in the region's floor mask (`inside_floor`), or an observed room node's centre
    inside its `any` mask, or at least 2 reference objects mapped.
    Open type T: some unseen region R of type T has none of its T markers mapped, and no observed room
    node of type T is inside R or reaches R while inside no other region of type T. Open class c: an unseen region holds an unmapped reference object with
    c in its `answers_to`.
    """
    obs = row.observed
    tmp: Dict[str, List[Point]] = {}
    for n in obs.objects:
        if n.kind == "object" and n.canon is not None:
            tmp.setdefault(n.canon, []).append(n.xy)
    by_canon: Dict[str, np.ndarray] = {c: np.asarray(pts, dtype=float) for c, pts in tmp.items()}

    def mapped(answers: FrozenSet[str], xy: Optional[Point]) -> bool:
        if xy is None or not answers:
            return False
        for c in answers:
            arr = by_canon.get(c)
            if arr is not None and bool((np.hypot(arr[:, 0] - xy[0], arr[:, 1] - xy[1]) <= model.MAPPED_M).any()):
                return True
        return False

    path_floor = set()
    for p in row.path_xy:
        path_floor |= truth.inside_floor(p)
    room_inside = set()
    room_reach = set()
    # room type -> regions that an observed room node of that type closes (§5.5): the node is inside the
    # region, or reaches it while inside no OTHER region of that type (seen or not; `any` mask)
    closed_by_room: Dict[str, set] = {}
    for n in obs.rooms:
        ins = truth.inside(n.xy)
        r = truth.reaches(n.xy)
        room_inside |= ins
        room_reach |= r
        t = n.room_type
        if t is None:
            continue
        for rid in r:
            if t not in truth.regions[rid].types:
                continue
            if rid in ins or not any(o != rid and t in truth.regions[o].types for o in ins):
                closed_by_room.setdefault(t, set()).add(rid)

    mapped_ids = set()
    mapped_markers = set()
    n_ref_mapped: Dict[int, int] = {}
    for rid, reg in truth.regions.items():
        k = 0
        for o in reg.ref_objects:
            if mapped(o.answers_to, o.xy):
                mapped_ids.add(o.object_id)
                k += 1
        n_ref_mapped[rid] = k
        for m in reg.markers:
            if mapped(m.answers_to, m.xy):
                mapped_ids.add(m.object_id)
                mapped_markers.add(m.object_id)

    seen, partly, unobs = set(), set(), set()
    for rid in truth.regions:
        if rid in path_floor or rid in room_inside or n_ref_mapped[rid] >= 2:
            seen.add(rid)
        elif n_ref_mapped[rid] >= 1 or rid in room_reach:
            partly.add(rid)
        else:
            unobs.add(rid)

    open_types, open_types_loose = set(), set()
    open_classes, open_classes_loose = set(), set()
    open_type_regions: Dict[str, set] = {}
    for rid in partly | unobs:
        reg = truth.regions[rid]
        open_types_loose |= set(reg.types)
        for t in reg.types:
            t_markers = [m for m in reg.markers if t in m.types]
            if not any(m.object_id in mapped_markers for m in t_markers) and rid not in closed_by_room.get(t, ()):
                open_types.add(t)
                open_type_regions.setdefault(t, set()).add(rid)
        for o in reg.ref_objects:
            open_classes_loose |= set(o.answers_to)
            if o.object_id not in mapped_ids:
                open_classes |= set(o.answers_to)

    return model.StageState(
        seen=frozenset(seen), partly_seen=frozenset(partly), unobserved=frozenset(unobs),
        mapped_objects=frozenset(mapped_ids),
        open_types=frozenset(open_types), open_classes=frozenset(open_classes),
        open_types_loose=frozenset(open_types_loose), open_classes_loose=frozenset(open_classes_loose),
        open_type_regions={t: frozenset(r) for t, r in open_type_regions.items()},
    )
