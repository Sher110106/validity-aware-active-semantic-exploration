"""Read saved graphs and model completions into guesses (PREREGISTRATION_SEMANTIC.md §3 and §7).

    read_graph(path)                       -> ObservedGraph
    read_member(path, observed, member)    -> Member
    parse_frame(path)                      -> [(row_id, run_basename, stage, round), ...]
    load_row(row_id, runs_root=...)        -> Row
    members_for(row, model, ...)           -> [Member, ...]

What counts as a guess (§7 as the lead changed it; geometry only, ids and `is_predicted` play no part):
  - a NEW OBJECT is an object node of the completion whose centre lies more than 0.5 m (horizontally)
    from EVERY observed object node;
  - a NEW ROOM is a room node of the completion whose centre lies more than 0.5 m from EVERY observed
    room node.
`is_predicted` is only counted (n_objects_flagged / n_objects_unflagged). Both rules use the same
test as the mapping rule of §5.4: a node is "near" when its distance is <= 0.5 m, so "new" means > 0.5 m.

Bad input: a node with no parseable position (or no integer id) is skipped and counted in `SKIPPED`,
never guessed. A member file that does not parse is skipped and counted. `SKIPPED` is a module-level
Counter that adds up across calls; call `SKIPPED.clear()` to reset it. model.py has no field for it.

Sibling modules load by file path (see region_truth.py); `labels` is a module attribute tests may swap.
"""
from __future__ import annotations

import ast
import collections
import functools
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent


def _sibling(name: str):
    key = f"semantic_{name}"
    if key in sys.modules:
        return sys.modules[key]
    path = HERE / f"{name}.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(key, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(key, None)  # never leave a half-built module behind
        raise
    return mod


_LOAD_ERRORS: Dict[str, Exception] = {}


def _optional_sibling(name: str):
    """Like _sibling, but a module that fails to load (for example, its table file is missing) gives None."""
    try:
        return _sibling(name)
    except Exception as exc:  # noqa: BLE001 - reported by _need_labels
        _LOAD_ERRORS[name] = exc
        return None


M = _sibling("model")
labels = _optional_sibling("labels")  # swap in tests: extract_preds.labels = FakeLabels

RUNS_ROOT = Path("/Users/sher/cvp_live_campaign_copy/runs/live_campaign")
GEMINI_ROOT = RUNS_ROOT / "hm3d_refs_work"
FRAME_PATH = HERE / "sample_frame.txt"
N_MEMBERS = 4
MODELS = ("deepseek", "gemini", "claude-opus-5-5", "claude-haiku-5-5")

SKIPPED: "collections.Counter[str]" = collections.Counter()

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _need_labels():
    if labels is None:
        why = _LOAD_ERRORS.get("labels")
        raise ImportError(f"semantic/labels.py is missing or failed to load ({why!r}) and extract_preds.labels was not set")
    return labels


# ---------------------------------------------------------------------------- node parsing

def _parse_vec3(v) -> Optional[Tuple[float, float, float]]:
    """"[1.3, 8.0, 0.5]" or a 3-list to three finite floats; None if it is anything else."""
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            try:
                v = ast.literal_eval(v)
            except (ValueError, SyntaxError):
                return None
    if not isinstance(v, (list, tuple)) or len(v) != 3:
        return None
    out = []
    for c in v:
        if isinstance(c, bool) or not isinstance(c, (int, float)):
            return None
        c = float(c)
        if not math.isfinite(c):
            return None
        out.append(c)
    return (out[0], out[1], out[2])


def _load_yaml(path: Path) -> dict:
    with open(path, "r") as fh:
        doc = yaml.load(fh, Loader=_YAML_LOADER)
    if not isinstance(doc, dict) or not isinstance(doc.get("nodes"), list):
        raise ValueError(f"{path}: not a scene graph (no top-level 'nodes' list)")
    return doc


def _object_canon(name: str) -> Optional[str]:
    lab = _need_labels()
    c = lab.normalise(name)
    if c is None or lab.is_structure(c):
        return None
    return c


def parse_nodes(path: Path) -> Tuple[list, FrozenSet[int], int]:
    """(room and object nodes with a position, ids of ALL nodes, number skipped for bad id/position)."""
    return parse_doc_nodes(_load_yaml(Path(path)))


def _check_doc(doc) -> dict:
    if not isinstance(doc, dict) or not isinstance(doc.get("nodes"), list):
        raise ValueError("not a scene graph (no top-level 'nodes' list)")
    return doc


def parse_doc_nodes(doc: dict) -> Tuple[list, FrozenSet[int], int]:
    """Like parse_nodes, for a graph already loaded as a dict (a file's YAML, or a placebo graph)."""
    lab = _need_labels()
    doc = _check_doc(doc)
    nodes, ids, skipped = [], set(), 0
    for raw in doc["nodes"]:
        if not isinstance(raw, dict):
            skipped += 1
            SKIPPED["node_not_a_mapping"] += 1
            continue
        nid = raw.get("id")
        if isinstance(nid, bool) or not isinstance(nid, int):
            skipped += 1
            SKIPPED["node_bad_id"] += 1
            continue
        ids.add(nid)
        kind = raw.get("node_type")
        if kind not in ("room", "object"):
            continue
        pos = _parse_vec3(raw.get("position"))
        if pos is None:
            skipped += 1
            SKIPPED[f"{kind}_unparseable_position"] += 1
            continue
        name = str(raw.get("name") if raw.get("name") is not None else "")
        flag = raw.get("is_predicted")
        flag = flag if isinstance(flag, bool) else None
        nodes.append(M.Node(
            node_id=nid, kind=kind, name=name, xy=(pos[0], pos[1]), z=pos[2], is_predicted=flag,
            room_type=lab.room_type(name) if kind == "room" else None,
            canon=_object_canon(name) if kind == "object" else None))
    return nodes, frozenset(ids), skipped


def read_graph(path: Path) -> "M.ObservedGraph":
    nodes, ids, _ = parse_nodes(path)
    return M.ObservedGraph(rooms=tuple(n for n in nodes if n.kind == "room"),
                           objects=tuple(n for n in nodes if n.kind == "object"), node_ids=ids)


def _far_from_all(xy, others: np.ndarray, d: float) -> bool:
    """True if xy is more than d from every row of `others` (Nx2)."""
    if len(others) == 0:
        return True
    return not bool((np.hypot(others[:, 0] - xy[0], others[:, 1] - xy[1]) <= d).any())


def member_from_nodes(member: int, new_rooms: Sequence["M.Node"], new_objects: Sequence["M.Node"]) -> "M.Member":
    """Reduce a member's guesses (§7) to claims and items (§7, item 51 of DEVIATIONS_NOVEMBER).

    L1 claims: distinct typed room types, dining left out. L2 claims: distinct canonical classes.
    L3 items: each new room with a type other than dining, and each new object with a class. A new
    room typed dining is left out of the items too (item 51) and counted in `n_rooms_dining`."""
    new_rooms, new_objects = tuple(new_rooms), tuple(new_objects)
    l1 = frozenset(n.room_type for n in new_rooms if n.room_type in M.ROOM_TYPES)
    l2 = frozenset(n.canon for n in new_objects if n.canon is not None)
    items = tuple(M.Item("room", n.room_type, n.xy) for n in new_rooms if n.room_type in M.ROOM_TYPES) + \
        tuple(M.Item("object", n.canon, n.xy) for n in new_objects if n.canon is not None)
    flagged = sum(1 for n in new_objects if n.is_predicted is True)
    return M.Member(
        member=member, new_rooms=new_rooms, new_objects=new_objects,
        l1_claims=l1, l2_claims=l2, l3_items=items,
        n_rooms_untyped=sum(1 for n in new_rooms if n.room_type is None),
        n_objects_unlabelled=sum(1 for n in new_objects if n.canon is None),
        n_objects_flagged=flagged, n_objects_unflagged=len(new_objects) - flagged,
        n_rooms_dining=sum(1 for n in new_rooms if n.room_type == "dining"))


def guesses_of(nodes: Sequence["M.Node"], observed: "M.ObservedGraph") -> Tuple[Tuple["M.Node", ...], Tuple["M.Node", ...]]:
    """§7: (new rooms, new objects) among the nodes of one completion, by place alone."""
    obs_obj = np.asarray([n.xy for n in observed.objects], dtype=float).reshape(-1, 2)
    obs_room = np.asarray([n.xy for n in observed.rooms], dtype=float).reshape(-1, 2)
    return (tuple(n for n in nodes if n.kind == "room" and _far_from_all(n.xy, obs_room, M.NEW_NODE_M)),
            tuple(n for n in nodes if n.kind == "object" and _far_from_all(n.xy, obs_obj, M.NEW_NODE_M)))


def member_from_doc(doc: dict, observed: "M.ObservedGraph", member: int) -> "M.Member":
    nodes, _, _ = parse_doc_nodes(doc)
    return member_from_nodes(member, *guesses_of(nodes, observed))


def read_member(path: Path, observed: "M.ObservedGraph", member: int) -> "M.Member":
    nodes, _, _ = parse_nodes(path)
    return member_from_nodes(member, *guesses_of(nodes, observed))


# ------------------------------------------------------------------------------ the frame

def parse_frame(path: Path = FRAME_PATH) -> List[Tuple[str, str, int, int]]:
    """Lines `<row_id> <run_dir> <stage>`; comment lines `# Round N: ...` set the round."""
    rows, rnd = [], 0
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            m = re.match(r"#\s*Round\s+(\d+)", line)
            if m:
                rnd = int(m.group(1))
            continue
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"bad frame line: {line!r}")
        row_id, run_dir, stage = parts
        if rnd == 0:
            raise ValueError("frame row before any 'Round' comment")
        rows.append((row_id, Path(run_dir).name, int(stage), rnd))
    return rows


_RUN_RE = re.compile(r"^e[12]_(\d{5})_s(\d+)_(official|filter_only)_")
# Every live arm of the saved runs (the paper's room test, §11): official, filter_only, placebo, oracle.
_LIVE_RUN_RE = re.compile(r"^e\d_(\d{5})_s(\d+)_(official|filter_only|placebo|oracle_visible)_")
LIVE_ARMS = ("official", "filter_only", "placebo", "oracle_visible")


@functools.lru_cache(maxsize=None)
def _frame_index(path: str) -> Dict[str, Tuple[str, int, int]]:
    return {rid: (run, stage, rnd) for rid, run, stage, rnd in parse_frame(Path(path))}


def _world_path(stage_dir: Path) -> List[Tuple[float, float]]:
    doc = json.loads((stage_dir / "executed_path.json").read_text())
    pts = []
    for p in doc["world_frame_path"]:
        v = _parse_vec3(p)
        if v is None:
            SKIPPED["path_point_unparseable"] += 1
            continue
        pts.append((v[0], v[1]))
    return pts


def _path_up_to(run_dir: Path, stage: int) -> Tuple[Tuple[float, float], ...]:
    """§5.4: the start pose, then every point of `world_frame_path` of stages 1..stage. Stage 0 has
    no path file: its path is the start pose, the first point of stage 1's file."""
    first = _world_path(run_dir / "stages" / "1")
    if not first:
        raise ValueError(f"{run_dir.name}: stage 1 holds no path point, so there is no start pose")
    path: List[Tuple[float, float]] = [first[0]]
    for k in range(1, stage + 1):
        path.extend(_world_path(run_dir / "stages" / str(k)))
    return tuple(path)


def load_row(row_id: str, runs_root: Path = RUNS_ROOT, frame_path: Path = FRAME_PATH) -> "M.Row":
    index = _frame_index(str(frame_path))
    if row_id not in index:
        raise KeyError(f"row {row_id!r} is not in {frame_path}")
    run, stage, rnd = index[row_id]
    m = _RUN_RE.match(run)
    if not m:
        raise ValueError(f"cannot read scene, seed and arm from run name {run!r}")
    scene, seed, arm = m.group(1), int(m.group(2)), m.group(3)
    run_dir = Path(runs_root) / run
    stage_dir = run_dir / "stages" / str(stage)
    observed = read_graph(stage_dir / "habitat_scene_graph_original_graph0.yaml")
    return M.Row(row_id=row_id, scene=scene, seed=seed, arm=arm, stage=stage,
                 cluster=f"{scene}_s{seed}_{arm}", round=rnd, is_gemini_row=(rnd == 4),
                 observed=observed, path_xy=_path_up_to(run_dir, stage))


def run_info(run: str) -> Tuple[str, int, str]:
    """(scene, seed, arm) of a live run folder name, for every live arm."""
    m = _LIVE_RUN_RE.match(run)
    if not m:
        raise ValueError(f"cannot read scene, seed and arm from run name {run!r}")
    return m.group(1), int(m.group(2)), m.group(3)


def stage_numbers(run: str, runs_root: Path = RUNS_ROOT) -> List[int]:
    """Stage folders of a run that hold an observed graph, ascending."""
    out = []
    root = Path(runs_root) / run / "stages"
    if root.is_dir():
        for d in root.iterdir():
            if d.name.isdigit() and (d / "habitat_scene_graph_original_graph0.yaml").is_file():
                out.append(int(d.name))
    return sorted(out)


def load_stage_row(run: str, stage: int, runs_root: Path = RUNS_ROOT, track: int = 0) -> "M.Row":
    """A Row for any (run, stage) of a live run, not only the frame's. Round 0, never a Gemini row.
    `track` 0 or 1 picks the observed graph of that track (members 0-3 use track 0, 4-7 track 1)."""
    scene, seed, arm = run_info(run)
    run_dir = Path(runs_root) / run
    observed = read_graph(run_dir / "stages" / str(stage) / f"habitat_scene_graph_original_graph{track}.yaml")
    return M.Row(row_id=f"{run}#st{stage:02d}", scene=scene, seed=seed, arm=arm, stage=stage,
                 cluster=f"{scene}_s{seed}_{arm}", round=0, is_gemini_row=False,
                 observed=observed, path_xy=_path_up_to(run_dir, stage))


# ---------------------------------------------------------------------------------- members

def _highest_attempt(raw_dir: Path) -> Optional[Path]:
    best, best_n = None, -1
    if raw_dir.is_dir():
        for d in raw_dir.iterdir():
            m = re.fullmatch(r"attempt_(\d+)", d.name)
            if m and d.is_dir() and int(m.group(1)) > best_n:
                best, best_n = d, int(m.group(1))
    return best


def _read_all(row: "M.Row", files: Sequence[Tuple[int, Path]]) -> List["M.Member"]:
    out = []
    for m, f in files:
        if not f.is_file():
            continue
        try:
            out.append(read_member(f, row.observed, m))
        except (ValueError, OSError, yaml.YAMLError, KeyError, TypeError):
            SKIPPED["member_unreadable"] += 1
    return out


def gemini_dir(row: "M.Row", gemini_root: Path = GEMINI_ROOT, frame_path: Path = FRAME_PATH) -> Optional[Path]:
    """The stage folder holding this row's Gemini members: gemini_static2 if it holds any, else gemini_static."""
    run, stage, _ = _frame_index(str(frame_path))[row.row_id]
    for sub in ("gemini_static2", "gemini_static"):
        d = Path(gemini_root) / sub / run / str(stage)
        if any((d / f"gemini_new_graph_{m}.yaml").is_file() for m in range(N_MEMBERS)):
            return d
    return None


def claude_member_status(claude_root: Path, model: str, row_id: str) -> Dict[int, str]:
    """Per member 0..3: "ok" (parsed_graph.yaml with parse.json {"ok": true}), "dropped" (the folder
    exists but parse.json says ok false, is missing or unreadable, or there is no parsed_graph.yaml:
    counted, not scored), or "absent" (no member folder: never run)."""
    base = Path(claude_root) / model / row_id
    out: Dict[int, str] = {}
    for m in range(N_MEMBERS):
        d = base / f"member_{m}"
        if not d.is_dir():
            out[m] = "absent"
            continue
        ok = False
        try:
            doc = json.loads((d / "parse.json").read_text())
            ok = isinstance(doc, dict) and doc.get("ok") is True
        except (OSError, ValueError):
            ok = False
        out[m] = "ok" if ok and (d / "parsed_graph.yaml").is_file() else "dropped"
    return out


def member_files(row: "M.Row", model: str, runs_root: Path = RUNS_ROOT, gemini_root: Path = GEMINI_ROOT,
                 claude_root: Optional[Path] = None, frame_path: Path = FRAME_PATH) -> List[Tuple[int, Path]]:
    """The completion files of a row's members 0..3 that exist, in member order (a Claude member that
    is dropped has no file here; see claude_member_status). filter_only rows give the raw files (§7)."""
    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}; expected one of {MODELS}")
    if model == "deepseek":
        run, stage, _ = _frame_index(str(frame_path))[row.row_id]
        stage_dir = Path(runs_root) / run / "stages" / str(stage)
        if row.arm == "filter_only":  # raw completions, before the filter (§7)
            att = _highest_attempt(stage_dir / "live_policy_raw")
            if att is None:
                SKIPPED["raw_attempt_missing"] += 1
                return []
            base = att
        else:
            base = stage_dir
        files = [(m, base / f"habitat_scene_graph_new_graph_{m}.yaml") for m in range(N_MEMBERS)]
    elif model == "gemini":
        if not row.is_gemini_row:
            return []
        d = gemini_dir(row, gemini_root, frame_path)
        if d is None:
            return []
        files = [(m, d / f"gemini_new_graph_{m}.yaml") for m in range(N_MEMBERS)]
    else:
        if claude_root is None:
            raise ValueError("claude_root is required for a Claude model")
        status = claude_member_status(claude_root, model, row.row_id)
        base = Path(claude_root) / model / row.row_id
        files = [(m, base / f"member_{m}" / "parsed_graph.yaml") for m in range(N_MEMBERS) if status[m] == "ok"]
    return [(m, f) for m, f in files if f.is_file()]


def members_for(row: "M.Row", model: str, runs_root: Path = RUNS_ROOT, gemini_root: Path = GEMINI_ROOT,
                claude_root: Optional[Path] = None, frame_path: Path = FRAME_PATH) -> List["M.Member"]:
    """Track-0 members 0..3 that exist, in member order. A missing file is a missing member."""
    return _read_all(row, member_files(row, model, runs_root, gemini_root, claude_root, frame_path))


def live_member_files(run: str, stage: int, runs_root: Path = RUNS_ROOT) -> Dict[int, Path]:
    """The members on disk of a live stage, 0..7 (track = id // 4). For a filter_only run these are the
    files the planner read (after the filter); live_policy_raw holds the others (see raw_member_files)."""
    d = Path(runs_root) / run / "stages" / str(stage)
    return {k: d / f"habitat_scene_graph_new_graph_{k}.yaml" for k in range(2 * N_MEMBERS)
            if (d / f"habitat_scene_graph_new_graph_{k}.yaml").is_file()}


def raw_member_files(run: str, stage: int, runs_root: Path = RUNS_ROOT) -> Dict[int, Path]:
    """Members 0..7 as the model produced them: the highest live_policy_raw attempt if the stage has one
    (filter_only), else the stage files."""
    d = Path(runs_root) / run / "stages" / str(stage)
    att = _highest_attempt(d / "live_policy_raw")
    if att is None:
        return live_member_files(run, stage, runs_root)
    return {k: att / f"habitat_scene_graph_new_graph_{k}.yaml" for k in range(2 * N_MEMBERS)
            if (att / f"habitat_scene_graph_new_graph_{k}.yaml").is_file()}


def load_doc(path: Path) -> dict:
    """A completion file as a dict (the YAML top level)."""
    return _load_yaml(Path(path))
