"""The paper's room test, with a chance rate (PREREGISTRATION_SEMANTIC.md §11).

On a live run: a region not seen at stage 0 counts as **predicted before found** if, at some stage before it is
seen (§5.4), at least 2 of the 8 members put a new room within 2.5 m of the region's `centroid_xy`. It is scored
twice: with the room's type required to match the region's types (§5.2; a region with no marker type never
matches), and without. Reported per live arm, with the placebo arm as the chance rate and the paper's 9 of 28
beside it.

On the 4-member replays (a model's members on the frame's rows, one stage each) the same count is given at 1 of 4
and 2 of 4: a region not seen at stage 0 of the row's run counts if, at some replay row whose stage lies before
the region is first seen in that run, at least t of the model's members put a new room within 2.5 m.

Choices, noted in README.md:
  * "seen at stage k" is `stage_state(...).seen` of the track-0 map and the path to stage k, as everywhere (§3);
  * a new room is a room node more than 0.5 m from every room of the member's own track's observed graph (§7);
  * live members are the files on disk, which for a filter_only run are the members the planner read;
  * a stage with fewer than 8 members is counted with the members it has, and also reported on its own: the
    result is given for all stages and for stages that hold all 8 members;
  * a region seen at stage 0 is left out; a region first seen at stage k can only be predicted at stages < k.
"""
from __future__ import annotations

import csv
import importlib
import importlib.util
import math
import re
import sys
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
extract_preds = _Lazy("extract_preds")
region_truth = _Lazy("region_truth")

ROOM_RADIUS_M = 2.5
LIVE_MEMBERS = 8
LIVE_THRESHOLD = 2
PAPER_PREDICTED, PAPER_OF = 9, 28
RUN_TABLE = Path(__file__).resolve().parent.parent / "results_2026-10-31" / "run_table.csv"
INF = 10 ** 9


# ------------------------------------------------------------------------------------ the runs

def live_runs(runs_root: Path, run_table: Optional[Path] = RUN_TABLE, which: str = "counted") -> List[str]:
    """The live runs to test: those the run table marks `counted`, for the four live arms (`which="all"`
    also takes the runs it marks excluded, whose members are as valid). Without the table, every run
    folder of a live arm whose name carries no FAILED, ABORTED or EXCLUDED."""
    ep = extract_preds
    runs_root = Path(runs_root)
    names: List[str] = []
    if run_table is not None and Path(run_table).is_file():
        with open(run_table, newline="") as f:
            for r in csv.DictReader(f):
                ok = r.get("status") == "counted" or (which == "all" and str(r.get("status", "")).startswith("excluded"))
                if ok and r.get("arm") in ep.LIVE_ARMS:
                    names.append(r["run"])
    else:
        for d in sorted(runs_root.iterdir()) if runs_root.is_dir() else []:
            if d.is_dir() and ep._LIVE_RUN_RE.match(d.name) and not re.search(r"FAILED|ABORTED|EXCLUDED", d.name):
                names.append(d.name)
    return [n for n in names if (runs_root / n / "stages").is_dir()]


def run_states(run: str, truth, runs_root: Path) -> Dict[int, "model.StageState"]:
    """stage_state for every stage of a run that holds an observed graph (track 0)."""
    ep = extract_preds
    return {k: region_truth.stage_state(truth, ep.load_stage_row(run, k, runs_root)) for k in ep.stage_numbers(run, runs_root)}


def first_seen(states: Mapping[int, "model.StageState"], region_id: int) -> int:
    """The first stage at which the region is seen, or INF."""
    return min((k for k, s in states.items() if region_id in s.seen), default=INF)


def regions_unseen_at_start(states: Mapping[int, "model.StageState"]) -> List[int]:
    """Regions not seen at stage 0 (the earliest stage the run holds)."""
    if not states:
        return []
    s0 = states[min(states)]
    return sorted(set(r for r in s0.seen | s0.partly_seen | s0.unobserved) - set(s0.seen))


# ------------------------------------------------------------------------------- the test itself

def _room_near(rooms: Sequence["model.Node"], region, require_type: bool) -> bool:
    cx, cy = region.centroid_xy
    if not (math.isfinite(cx) and math.isfinite(cy)):
        return False
    for n in rooms:
        if math.hypot(n.xy[0] - cx, n.xy[1] - cy) <= ROOM_RADIUS_M:
            if not require_type or (n.room_type is not None and n.room_type in region.types):
                return True
    return False


def n_members_predicting(members_rooms: Mapping[int, Sequence["model.Node"]], region, require_type: bool) -> int:
    """How many members put a new room within 2.5 m of the region's centroid."""
    return sum(1 for rooms in members_rooms.values() if _room_near(rooms, region, require_type))


def predicted_before_found(truth, states: Mapping[int, "model.StageState"],
                           rooms_by_stage: Mapping[int, Mapping[int, Sequence["model.Node"]]],
                           threshold: int, require_type: bool,
                           stages: Optional[Iterable[int]] = None) -> Dict[int, bool]:
    """For each region not seen at stage 0: was it predicted before it was found? `rooms_by_stage[k][m]` are
    member m's new rooms at stage k. `stages` limits the stages looked at (default: all that hold members)."""
    unseen0 = regions_unseen_at_start(states)
    use = sorted(rooms_by_stage) if stages is None else sorted(set(stages) & set(rooms_by_stage))
    out: Dict[int, bool] = {}
    for rid in unseen0:
        fs = first_seen(states, rid)
        region = truth.regions[rid]
        out[rid] = any(k < fs and n_members_predicting(rooms_by_stage[k], region, require_type) >= threshold for k in use)
    return out


def live_new_rooms(run: str, stage: int, runs_root: Path) -> Dict[int, List["model.Node"]]:
    """Member m's new rooms at a live stage, against the observed graph of m's own track."""
    ep = extract_preds
    files = ep.live_member_files(run, stage, runs_root)
    if not files:
        return {}
    observed = {}
    for t in (0, 1):
        f = Path(runs_root) / run / "stages" / str(stage) / f"habitat_scene_graph_original_graph{t}.yaml"
        if not f.is_file():            # e.g. stage 0 of some runs holds no graph for track 1: use track 0's
            ep.SKIPPED["observed_graph_missing_track_%d" % t] += 1
            f = Path(runs_root) / run / "stages" / str(stage) / "habitat_scene_graph_original_graph0.yaml"
        observed[t] = ep.read_graph(f)
    out: Dict[int, List["model.Node"]] = {}
    for k, path in files.items():
        try:
            nodes, _, _ = ep.parse_nodes(path)
        except (ValueError, OSError):
            ep.SKIPPED["member_unreadable"] += 1
            continue
        out[k] = list(ep.guesses_of(nodes, observed[k // 4])[0])
    return out


def live_run_result(run: str, truth, runs_root: Path, states: Optional[Mapping[int, "model.StageState"]] = None) -> Dict[str, Any]:
    """The paper's test on one live run, scored with and without the type match, over all stages and over
    the stages that hold all 8 members."""
    states = states if states is not None else run_states(run, truth, runs_root)
    scene, seed, arm = extract_preds.run_info(run)
    rooms_by_stage = {k: live_new_rooms(run, k, runs_root) for k in sorted(states)}
    rooms_by_stage = {k: v for k, v in rooms_by_stage.items() if v}
    full8 = [k for k, v in rooms_by_stage.items() if len(v) == LIVE_MEMBERS]
    unseen0 = regions_unseen_at_start(states)
    out: Dict[str, Any] = {"run": run, "scene": scene, "seed": seed, "arm": arm, "n_stages": len(states),
                           "n_stages_with_members": len(rooms_by_stage), "n_stages_with_8_members": len(full8),
                           "n_regions_unseen_at_stage0": len(unseen0), "regions_unseen_at_stage0": unseen0}
    for label, stages in (("all_stages", None), ("stages_with_8_members", full8)):
        for typed in (False, True):
            got = predicted_before_found(truth, states, rooms_by_stage, LIVE_THRESHOLD, typed, stages)
            out[f"predicted_{label}_{'typed' if typed else 'untyped'}"] = sorted(r for r, v in got.items() if v)
    return out


def by_arm(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Counts per live arm: regions not seen at stage 0 and regions predicted before found, summed over runs;
    the placebo arm is the chance rate; the paper's 9 of 28 is given beside."""
    out: Dict[str, Any] = {"paper": {"predicted": PAPER_PREDICTED, "of": PAPER_OF}, "arms": {}}
    for r in results:
        a = out["arms"].setdefault(r["arm"], {"runs": 0, "of": 0, "stages": 0, "stages_with_8_members": 0})
        a["runs"] += 1
        a["of"] += r["n_regions_unseen_at_stage0"]
        a["stages"] += r["n_stages_with_members"]
        a["stages_with_8_members"] += r["n_stages_with_8_members"]
        for k, v in r.items():
            if k.startswith("predicted_"):
                a[k] = a.get(k, 0) + len(v)
    for a in out["arms"].values():
        for k in [k for k in a if k.startswith("predicted_")]:
            a["rate" + k[len("predicted"):]] = (a[k] / a["of"]) if a["of"] else None
    return out


# ------------------------------------------------------------------------------ 4-member replays

def replay_counts(rows: Sequence["model.Row"], members_by_row: Mapping[str, Sequence["model.Member"]],
                  truths: Mapping[str, Any], states_by_run: Mapping[str, Mapping[int, "model.StageState"]],
                  run_of_row: Mapping[str, str], thresholds: Sequence[int] = (1, 2)) -> Dict[str, Any]:
    """The same count on the 4-member replays. For each run that holds replay rows with members, regions not
    seen at stage 0 and, for each threshold t and with or without the type match, the regions put by at least
    t members at some replay row before they are first seen in that run."""
    by_run: Dict[str, List["model.Row"]] = {}
    for r in rows:
        if members_by_row.get(r.row_id):
            by_run.setdefault(run_of_row[r.row_id], []).append(r)
    out: Dict[str, Any] = {"runs": {}, "totals": {}}
    for run, rs in sorted(by_run.items()):
        states = states_by_run[run]
        truth = truths[rs[0].scene]
        rooms_by_stage = {r.stage: {m.member: m.new_rooms for m in members_by_row[r.row_id]} for r in rs}
        unseen0 = regions_unseen_at_start(states)
        ent: Dict[str, Any] = {"n_rows": len(rs), "stages": sorted(rooms_by_stage), "n_regions_unseen_at_stage0": len(unseen0)}
        for t in thresholds:
            for typed in (False, True):
                got = predicted_before_found(truth, states, rooms_by_stage, t, typed)
                ent[f"predicted_{t}of4_{'typed' if typed else 'untyped'}"] = sorted(r for r, v in got.items() if v)
        out["runs"][run] = ent
    tot: Dict[str, int] = {"runs": 0, "of": 0}
    for ent in out["runs"].values():
        tot["runs"] += 1
        tot["of"] += ent["n_regions_unseen_at_stage0"]
        for k, v in ent.items():
            if k.startswith("predicted_"):
                tot[k] = tot.get(k, 0) + len(v)
    out["totals"] = tot
    return out


def dry_counts(live: Mapping[str, Any], replay: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """Counts of runs, stages and regions only: no predicted count."""
    out: Dict[str, Any] = {"live_arms": {}, "replay": {}}
    for arm, a in live["arms"].items():
        out["live_arms"][arm] = {k: a[k] for k in ("runs", "of", "stages", "stages_with_8_members")}
    for model_name, rep in replay.items():
        out["replay"][model_name] = {"runs": rep["totals"]["runs"], "of": rep["totals"]["of"],
                                     "rows": sum(e["n_rows"] for e in rep["runs"].values())}
    return out
