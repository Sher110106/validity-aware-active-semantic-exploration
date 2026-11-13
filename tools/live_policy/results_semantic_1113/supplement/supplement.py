#!/usr/bin/env python3
"""Counts that PREREGISTRATION_SEMANTIC.md asks for and the scorer's result files do not hold.

It imports the frozen scorer's own loading and label functions (read only), so every count uses the
rules of the scoring runs. It reads the inputs the two scoring runs read (see section "How it was run"
of RESULTS.md) and writes `supplement.json` beside this file. It changes no other file.

Run from the repository root:
    .venv_offline/bin/python tools/live_policy/results_semantic_1113/supplement/supplement.py

What it counts, per model (DeepSeek, Gemini, placebo, Claude Opus, Claude Haiku):
  - new objects, and how many carry an "other" label, a structure label, or a class (section 6);
  - new objects with and without the is_predicted flag (section 7);
  - new rooms, untyped new rooms, new rooms typed dining (section 6; deviation 51);
and for the replays of both Claude models, the balance checks of section 12; and, for each frame row,
where the looser truth sets (section 11) differ from the primary ones, and how many members proposed a
new object (or a new room) with that label.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]                       # the repository root (project/)
SEM = ROOT / "tools" / "live_policy" / "semantic"
CVP = ROOT.parent
REPLAY_M4 = CVP / "replay_outputs" / "m4"
OUT = HERE / "supplement.json"
MODELS = ("deepseek", "gemini", "placebo", "claude-opus-5-5", "claude-haiku-5-5")
CLAUDE = ("claude-opus-5-5", "claude-haiku-5-5")


# ------------------------------------------------------------------------------------------ pure counts

def label_kind(name: str, normalise: Callable[[str], Optional[str]], is_structure: Callable[[str], bool]) -> str:
    """'other' (no canonical class), 'structure' (a structure class) or 'class' (a scored class)."""
    c = normalise(name)
    if c is None:
        return "other"
    return "structure" if is_structure(c) else "class"


def label_counts(members: Iterable[Any], normalise, is_structure) -> Dict[str, int]:
    """Counts over the new objects and new rooms of a list of members (section 7 objects)."""
    out = collections.Counter()
    for m in members:
        out["members"] += 1
        for n in m.new_objects:
            out["new_objects"] += 1
            out["objects_" + label_kind(n.name, normalise, is_structure)] += 1
            if n.is_predicted is True:
                out["objects_flagged"] += 1
            else:
                out["objects_unflagged"] += 1
        for n in m.new_rooms:
            out["new_rooms"] += 1
            if n.room_type is None:
                out["rooms_untyped"] += 1
            elif n.room_type == "dining":
                out["rooms_dining"] += 1
    keys = ("members", "new_objects", "objects_other", "objects_structure", "objects_class", "objects_flagged",
            "objects_unflagged", "new_rooms", "rooms_untyped", "rooms_dining")
    return {k: int(out[k]) for k in keys}


def looser_differences(state: Any) -> Dict[str, List[str]]:
    """Labels the looser truth (section 11) holds and the primary truth does not, for one row."""
    return {"types": sorted(set(state.open_types_loose) - set(state.open_types)),
            "classes": sorted(set(state.open_classes_loose) - set(state.open_classes))}


def members_proposing(members: Iterable[Any], types: Sequence[str], classes: Sequence[str]) -> Dict[str, int]:
    """For one row: members with a claim of one of those labels, and new objects of those classes."""
    ts, cs = set(types), set(classes)
    mem = list(members)
    return {
        "members": len(mem),
        "members_with_type_claim": sum(1 for m in mem if ts & set(m.l1_claims)),
        "members_with_class_claim": sum(1 for m in mem if cs & set(m.l2_claims)),
        "new_objects_of_those_classes": sum(1 for m in mem for n in m.new_objects if n.canon in cs),
    }


def matched_equals_plain(records: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    """Members with an L1 claim whose one-claim score (extra.l1_matched) differs from the plain L1 score."""
    n = diff = 0
    for r in records:
        for m in r["model"].values():
            if m["L1"] is None:
                continue
            n += 1
            if m["extra"].get("l1_matched") != m["L1"]:
                diff += 1
    return {"members_with_l1_score": n, "members_where_one_claim_score_differs": diff}


def balance_counts(root: Path, model: str, ledger: Path, statuses: Mapping[str, Mapping[int, str]]) -> Dict[str, Any]:
    """Section 12 balance checks for one replayed model.

    drop rate: members not scored (status other than ok) over members.
    rejected requests: ledger lines whose status is not ok, and member records with an error or a status
    other than ok. The loop sends history append-only and asks the API to fail on any edit of it
    (tools/llm_anthropic/claude_loop.py, "Preserved thinking"), so a rejected edit would show as one of these."""
    members = dropped = 0
    for per_row in statuses.values():
        for st in per_row.values():
            members += 1
            dropped += st != "ok"
    ledger_lines = ledger_bad = 0
    for line in ledger.read_text().splitlines():
        if not line.strip():
            continue
        x = json.loads(line)
        if x["model"] != model:
            continue
        ledger_lines += 1
        ledger_bad += x["status"] != "ok"
    rec_n = rec_err = rec_bad = 0
    for p in sorted((root / model / "effort_medium").glob("*/member_*/record.json")):
        r = json.loads(p.read_text())
        rec_n += 1
        rec_err += r.get("error") is not None
        rec_bad += r.get("status") != "ok"
    return {"members": members, "members_dropped": dropped,
            "ledger_lines": ledger_lines, "ledger_lines_not_ok": ledger_bad,
            "member_records": rec_n, "member_records_with_error": rec_err, "member_records_status_not_ok": rec_bad}


# ------------------------------------------------------------------------------------------ loading the scorer

def load_scorer():
    """The frozen run_semantic module, loaded as the command line loads it. Read only."""
    path = SEM / "run_semantic.py"
    spec = importlib.util.spec_from_file_location("_supplement_run_semantic", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def build(claude_root: Path) -> Dict[str, Any]:
    rs = load_scorer()
    ep = rs.extract_preds
    labels = ep._need_labels()
    frame = Path(rs.FRAME_PATH)
    ctx = rs.build_context(frame, Path(ep.RUNS_ROOT))
    placebo = rs.placebo_inputs(ctx)
    members_by_model: Dict[str, Dict[str, list]] = {}
    status_by_model: Dict[str, Dict[str, Dict[int, str]]] = {}
    for m in MODELS:
        mem, _docs, _live, status = rs.model_inputs(ctx, m, claude_root if rs.is_claude(m) else None, placebo)
        members_by_model[m] = mem
        status_by_model[m] = status
    out: Dict[str, Any] = {
        "what": "counts the pre-registration asks for that the scorer's result files do not hold",
        "scorer": str(SEM.relative_to(ROOT)), "frame_rows": len(ctx.rows),
        "claude_root": "replay_outputs/m4",
    }
    out["labels"] = {m: label_counts([x for ms in members_by_model[m].values() for x in ms],
                                     labels.normalise, labels.is_structure) for m in MODELS}
    looser = []
    for r in ctx.rows:
        d = looser_differences(ctx.states[r.row_id])
        if d["types"] or d["classes"]:
            looser.append({"row_id": r.row_id, "scene": r.scene, "types": d["types"], "classes": d["classes"],
                           "proposed": {m: members_proposing(members_by_model[m].get(r.row_id, ()), d["types"], d["classes"])
                                        for m in MODELS}})
    out["looser"] = {
        "rows_where_truth_sets_differ": len(looser),
        "rows_where_types_differ": sum(1 for x in looser if x["types"]),
        "rows_where_classes_differ": sum(1 for x in looser if x["classes"]),
        "labels_that_differ": sorted({c for x in looser for c in x["classes"]} | {t for x in looser for t in x["types"]}),
        "rows": looser,
        "members_with_a_claim_of_a_differing_label": {
            m: sum(x["proposed"][m]["members_with_class_claim"] + x["proposed"][m]["members_with_type_claim"] for x in looser)
            for m in MODELS},
        "new_objects_of_a_differing_class": {
            m: sum(x["proposed"][m]["new_objects_of_those_classes"] for x in looser) for m in MODELS},
    }
    recs = {}
    for m, path in (("claude-opus-5-5", ROOT / "tools/live_policy/results_semantic_1113/claude/records_claude-opus-5-5.json"),
                    ("claude-haiku-5-5", ROOT / "tools/live_policy/results_semantic_1113/claude/records_claude-haiku-5-5.json"),
                    ("deepseek", ROOT / "tools/live_policy/results_semantic_1113/exploratory/records_deepseek.json")):
        recs[m] = matched_equals_plain(json.loads(path.read_text())["records"])
    out["one_claim_vs_plain_l1"] = recs
    out["balance"] = {m: balance_counts(claude_root, m, claude_root / "usage.jsonl", status_by_model[m]) for m in CLAUDE}
    out["skipped_counters"] = dict(ep.SKIPPED)
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--claude-root", default=str(REPLAY_M4))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    result = build(Path(a.claude_root))
    Path(a.out).write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
