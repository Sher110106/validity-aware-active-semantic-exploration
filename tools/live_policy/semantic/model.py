"""Shared data shapes for the semantic test (PREREGISTRATION_SEMANTIC.md).

Every module in this folder passes these objects and nothing else, so that the truth,
extraction, comparator and scoring code can be written and tested apart. Section numbers
refer to the pre-registration. All coordinates are in the pipeline frame: x and y are
horizontal, z is up, and every distance used by the rules is horizontal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

Point = Tuple[float, float]  # (x, y), metres

ROOM_TYPES: Tuple[str, ...] = ("bathroom", "bedroom", "kitchen", "laundry", "living")  # scored at L1
REPORTED_ROOM_TYPES: Tuple[str, ...] = ROOM_TYPES + ("dining",)  # dining is reported, never scored

REACH_M = 0.5        # §5.1: a point reaches a region within this distance of its footprint
MAPPED_M = 0.5       # §5.4: an observed same-class node within this distance maps a reference object
NEW_NODE_M = 0.5     # §7: a new object (room) lies farther than this from every observed object (room) node
NEW_OBJECT_M = NEW_NODE_M
CELL_M = 0.05        # footprint grid


# ---------------------------------------------------------------------------- truth (§5)

@dataclass(frozen=True)
class RefObject:
    """One annotated object used as truth (§5.3)."""
    object_id: int
    region_id: int
    raw_name: str            # the HM3D name
    answers_to: FrozenSet[str]   # §5.3: the non-structure classes it answers to (its own canonical
                                 # class and the detector's label for its name); never empty
    xy: Point                # midpoint of world_min / world_max
    canon: Optional[str] = None  # canonical class of the raw name alone (for reports)
    marker_of: FrozenSet[str] = frozenset()  # room types this object's raw name marks (§5.2)


@dataclass(frozen=True)
class Marker:
    """One annotated object whose raw name marks a room type (§5.2). A marker with no
    geometry, or one that answers only to structure classes, can never be mapped (§5.4)."""
    object_id: int
    region_id: int
    raw_name: str
    types: FrozenSet[str]
    answers_to: FrozenSet[str]   # non-structure classes it answers to; may be empty
    xy: Optional[Point]          # None if the object has no geometry


@dataclass(frozen=True)
class Region:
    region_id: int
    types: FrozenSet[str]                 # subset of REPORTED_ROOM_TYPES; empty means "other"
    centroid_xy: Point                    # `centroid_xy` of <scene>_regions.json (§11, room test)
    ref_objects: Tuple[RefObject, ...]
    markers: Tuple[Marker, ...]


class SceneTruth:
    """Truth for one scene. Built by region_truth.load_scene_truth(scene).

    Attributes
        scene: "00853" or "00871"
        regions: Dict[int, Region]
    Methods (all horizontal, pipeline frame)
        inside(p) -> FrozenSet[int]      region ids whose footprint (the `any` mask) holds p
        inside_floor(p) -> FrozenSet[int]  region ids whose floor mask holds p; a region with no
                                         floor uses its `any` mask (§5.4, the path rule only)
        reaches(p) -> FrozenSet[int]     region ids p is inside or within REACH_M of
        distance(p, region_id) -> float  0.0 if inside, else metres to the nearest footprint cell
    """
    scene: str
    regions: Dict[int, Region]

    def inside(self, p: Point) -> FrozenSet[int]:  # pragma: no cover - interface
        raise NotImplementedError

    def inside_floor(self, p: Point) -> FrozenSet[int]:  # pragma: no cover - interface
        raise NotImplementedError

    def reaches(self, p: Point) -> FrozenSet[int]:  # pragma: no cover - interface
        raise NotImplementedError

    def distance(self, p: Point, region_id: int) -> float:  # pragma: no cover - interface
        raise NotImplementedError


# ------------------------------------------------------------------- graphs and guesses (§7)

@dataclass(frozen=True)
class Node:
    """A room or object node read from a scene-graph YAML. Other node types are dropped."""
    node_id: int
    kind: str                      # "room" or "object"
    name: str                      # as written in the file
    xy: Point
    z: float
    is_predicted: Optional[bool]   # as written; None if absent. Not used by any rule.
    room_type: Optional[str] = None   # for rooms: the type from §6, or None
    canon: Optional[str] = None       # for objects: canonical class, or None for "other"/structure


@dataclass(frozen=True)
class ObservedGraph:
    """The track-0 observed graph of a row."""
    rooms: Tuple[Node, ...]
    objects: Tuple[Node, ...]
    node_ids: FrozenSet[int]       # ids of ALL nodes in the file, whatever their type (kept for reports; no rule uses ids)


@dataclass(frozen=True)
class Item:
    """One L3 item (§7): a new room with a type or a new object with a canonical class."""
    kind: str        # "room" or "object"
    label: str       # room type, or canonical class
    xy: Point


@dataclass(frozen=True)
class Member:
    """One completion of the observed graph, reduced to its guesses (§7)."""
    member: int                           # 0..3
    new_rooms: Tuple[Node, ...]
    new_objects: Tuple[Node, ...]
    l1_claims: FrozenSet[str]             # distinct scored room types among new rooms
    l2_claims: FrozenSet[str]             # distinct canonical classes among new objects
    l3_items: Tuple[Item, ...]            # rooms with a type and objects with a class, pooled
    n_rooms_untyped: int = 0
    n_objects_unlabelled: int = 0         # "other" or structure class
    n_objects_flagged: int = 0            # new objects carrying is_predicted == True
    n_objects_unflagged: int = 0


@dataclass(frozen=True)
class Row:
    """One row of the sample frame."""
    row_id: str                 # as in sample_frame.txt
    scene: str                  # "00853" or "00871"
    seed: int
    arm: str                    # "official" or "filter_only"
    stage: int
    cluster: str                # f"{scene}_s{seed}_{arm}"; first-attempt runs join the official cluster
    round: int                  # 1..4 (§12)
    is_gemini_row: bool
    observed: ObservedGraph
    path_xy: Tuple[Point, ...]  # the start pose and every path point of stages 1..stage (§5.4)


# ------------------------------------------------------------------ state at a stage (§5.4, §5.5)

@dataclass(frozen=True)
class StageState:
    """What the robot has seen at a row, and what is still open."""
    seen: FrozenSet[int]
    partly_seen: FrozenSet[int]
    unobserved: FrozenSet[int]
    mapped_objects: FrozenSet[int]           # object_ids of mapped reference objects and markers
    open_types: FrozenSet[str]               # §5.5: T is open if some unseen region R of type T has none of
                                             # its T markers mapped, and no observed room node of type T is
                                             # inside R, or reaches R while inside no other region of type T
    open_classes: FrozenSet[str]             # §5.5: classes answered to by an unmapped reference object
                                             # in an unseen region
    open_types_loose: FrozenSet[str]         # §11: an unseen region of the type exists
    open_classes_loose: FrozenSet[str]       # §11: an unseen region holds the class

    @property
    def unseen(self) -> FrozenSet[int]:
        return self.partly_seen | self.unobserved


# ------------------------------------------------------------------------------- scores (§8)

@dataclass
class MemberScore:
    """Hits and counts for one member at the three levels. A level with n == 0 has no score."""
    member: int
    l1_hits: int = 0
    l1_n: int = 0
    l2_hits: int = 0
    l2_n: int = 0
    l3_hits: float = 0.0     # float so that comparator means over draws fit
    l3_n: int = 0
    extra: Dict[str, float] = field(default_factory=dict)   # secondary readouts, by name

    def rate(self, level: str) -> Optional[float]:
        hits, n = {"L1": (self.l1_hits, self.l1_n), "L2": (self.l2_hits, self.l2_n), "L3": (self.l3_hits, self.l3_n)}[level]
        return None if n == 0 else hits / n


# ---------------------------------------------------------------- module contracts (signatures)
#
# labels.py
#   normalise(label: str) -> Optional[str]            canonical class, or None for "other"
#   is_structure(canon: str) -> bool
#   room_type(name: str) -> Optional[str]             one of REPORTED_ROOM_TYPES, or None
#   marker_types(raw_name: str) -> FrozenSet[str]     §5.2, with its exclusions
#   answers_to(raw_name: str) -> FrozenSet[str]       §5.3: non-structure classes an annotated object
#                                                     answers to: normalise(raw_name), and normalise of
#                                                     the detector's label for it in label_mapping.json
#                                                     (synonym_primary or extended_sensitivity_only)
#   detector_vocab() -> FrozenSet[str]                canonical classes in the 52-word vocabulary
#   canonical_classes() -> FrozenSet[str]             all non-structure canonical classes
#
# region_truth.py
#   load_scene_truth(scene: str, truth_dir: Path = ...) -> SceneTruth
#   stage_state(truth: SceneTruth, row: Row) -> StageState
#
# extract_preds.py
#   read_graph(path: Path) -> ObservedGraph
#   read_member(path: Path, observed: ObservedGraph, member: int) -> Member
#   load_row(row_id: str, ...) -> Row
#   members_for(row: Row, model: str, ...) -> List[Member]   model in {"deepseek", "gemini", "claude-opus-5-5", "claude-haiku-5-5"}
#
# baselines.py
#   Prior(summary_path).room_scores(observed) -> Dict[str, float]; .class_scores(observed) -> Dict[str, float]
#   b3_claims(prior, observed, k: int, level: str) -> FrozenSet[str]
#   b3l_items(prior, observed, member: Member) -> Tuple[Item, ...]
#   b1_members(row: Row) -> List[Member]                      four placebo draws
#   b5_score(member, truth, state, draws=1000, seed=...) -> float   mean L3 hits over draws
#   d_score(member, truth, state, draws=200, seed=...) -> Optional[float]
#
# score_levels.py
#   score_member(member: Member, truth: SceneTruth, state: StageState) -> MemberScore
#   l3_hit(item: Item, truth: SceneTruth, state: StageState, holder=None) -> bool
