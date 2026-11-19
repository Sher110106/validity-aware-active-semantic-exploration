"""Score the Gemini replay with the frozen semantic scorer (PREREGISTRATION_GEMINI.md, sections 4 to 6).

A wrapper outside tools/live_policy/semantic/. It changes no frozen file and no state of a frozen module.
It builds Gemini's members from its saved YAML files with the frozen readers, then calls the frozen
functions: build_context, placebo_inputs, score_model, analyse, family, wrong_house_gate,
secondary_records, extras_summary, validity.summarise, run_room_test, and for 5a the frozen row score,
cluster means, sign-flip test and interval, and Holm.

    .venv_offline/bin/python tools/live_policy/semantic_gemini.py \
        --gemini-root <replay out dir> --claude-root /Users/sher/project/cvp/replay_outputs/m4 \
        --prereg-sha256 <first field of PREREGISTRATION_GEMINI.sha256> --out <new folder>

The registration is always tools/live_policy/PREREGISTRATION_GEMINI.md and the rows file always
tools/live_policy/gemini_replay_rows.txt. It refuses unless `freeze.py check` passes, `--prereg-sha256` equals the
first field of PREREGISTRATION_GEMINI.sha256, the registration file has that hash, and the rows file has the hash
pinned in ROWS_FILE_SHA256. The confirmatory set is the rows of the whole rounds that finished. The finished rows
of a round that did not finish are scored apart, as exploratory, with numbers and no sentence. Rows not done are
listed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import yaml

HERE = Path(__file__).resolve().parent
SEM_DIR = HERE / "semantic"
PREREG_PATH = HERE / "PREREGISTRATION_GEMINI.md"
PREREG_HASH_PATH = HERE / "PREREGISTRATION_GEMINI.sha256"
ROWS_FILE = HERE / "gemini_replay_rows.txt"
ROWS_FILE_SHA256 = "e1d05b9c2345192a9e9337673b89c9a581a40301e7bd1a4f18922cef4abd98df"
MEMBERS_PER_ROW = (4, 2)
FINAL_ENDS = ("ok", "dropped_parse", "dropped_error")
DROPPED_ENDS = ("dropped_parse", "dropped_error")
LEVELS = ("L1", "L2", "L3")
FAMILY_5A = tuple((m, lv) for m in ("claude-opus-5-5", "claude-haiku-5-5") for lv in ("L2", "L3"))
OTHER_MODELS = ("claude-opus-5-5", "claude-haiku-5-5", "deepseek")
MIN_CLUSTERS_5A = 7
MIN_CLUSTERS_5B = 5
DROP_FLAG = 0.25
EXPLORATORY_LABEL = "exploratory: fewer than 7 clusters"


def _load(name: str):
    """Load a frozen module by path, under the key the frozen tests use, so every caller shares one copy."""
    key = f"_semantic_sibling_{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, SEM_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


rs = _load("run_semantic")
stats = rs.stats
ep = rs.extract_preds


class Refused(SystemExit):
    """The wrapper refuses to run."""


# ---------------------------------------------------------------------------------------- guards

def freeze_problems() -> List[str]:
    """The frozen check, as the frozen command line runs it for a Claude model. Empty means it holds."""
    return list(rs._sibling("freeze").check(rs.FREEZE_PATH, rs.FREEZE_SEMANTIC_DIR, rs.FREEZE_REPO))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _first_field(path: Path) -> str:
    p = Path(path)
    if not p.is_file():
        raise Refused(f"refused: {p} does not exist")
    text = p.read_text().strip()
    if not text:
        raise Refused(f"refused: {p} is empty")
    return text.split()[0].lower()


def check_guards(prereg_sha256: Optional[str]) -> str:
    """As the frozen command line does (run_semantic.check_guards): `--prereg-sha256` must equal the first field of
    PREREGISTRATION_GEMINI.sha256, and the registration file must hash to it too. Also: the freeze holds, the frozen
    PREREGISTRATION_SEMANTIC.md still has its hash, and the rows file is the pinned one. Returns the hash."""
    if not prereg_sha256:
        raise Refused("refused: --prereg-sha256 is required before any model output is loaded")
    registered = _first_field(PREREG_HASH_PATH)
    if prereg_sha256.strip().lower() != registered:
        raise Refused("refused: --prereg-sha256 does not equal the registered hash")
    if not Path(PREREG_PATH).is_file():
        raise Refused(f"refused: {PREREG_PATH} does not exist")
    actual = sha256_file(PREREG_PATH)
    if actual != registered:
        raise Refused(f"refused: {Path(PREREG_PATH).name} hashes to {actual}, not the registered value; it was edited")
    problems = freeze_problems()
    if problems:
        raise Refused("refused: the freeze does not hold (freeze.py check): " + "; ".join(problems))
    rs.verify_prereg_file()                      # the frozen PREREGISTRATION_SEMANTIC.md still has its hash
    if not Path(ROWS_FILE).is_file():
        raise Refused(f"refused: {ROWS_FILE} does not exist")
    rows_actual = sha256_file(ROWS_FILE)
    if rows_actual != ROWS_FILE_SHA256:
        raise Refused(f"refused: {Path(ROWS_FILE).name} hashes to {rows_actual}, not the pinned {ROWS_FILE_SHA256}")
    return actual


def forbidden_path(path: Path) -> bool:
    """True for any path under hm3d_refs_work/gemini_static*: the frozen gemini_dir would read it as round 4."""
    for p in (Path(path), Path(path).resolve()):
        parts = p.parts
        if any(parts[i] == "hm3d_refs_work" and parts[i + 1].startswith("gemini_static") for i in range(len(parts) - 1)):
            return True
    return False


def check_paths(gemini_root: Path, out: Path) -> None:
    for what, p in (("--gemini-root", gemini_root), ("--out", out)):
        if forbidden_path(p):
            raise Refused(f"refused: {what} {p} lies under hm3d_refs_work/gemini_static*, which the frozen reader takes for round 4")


# ----------------------------------------------------------------------------------- the replay

def read_rows(path: Path) -> List[str]:
    """Row ids in running order; blank lines and lines that start with # are skipped (as gemini_replay does)."""
    rows = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            rows.append(line.split()[0])
    return rows


def load_replay(gemini_root: Path, rows: Sequence[str], frame_rows: Sequence[Sequence[Any]]) -> Dict[str, Any]:
    """Read every row.json. A row is finished when row.json says done and every member ended ok or dropped.
    A round is finished when every row of it in the frame is finished. Returns the model name (all finished rows
    must agree), per-row info, the finished rounds, and the confirmatory and exploratory row ids."""
    round_of = {rid: rnd for rid, _run, _st, rnd in frame_rows}
    unknown = [r for r in rows if r not in round_of]
    if unknown:
        raise Refused(f"refused: rows file names rows that the frame does not hold: {unknown}")
    if len(set(rows)) != len(rows):
        raise Refused("refused: rows file repeats a row")
    r4 = [r for r in rows if round_of[r] == 4]
    if r4:
        raise Refused(f"refused: rows file holds round 4 rows, which the replay does not run: {r4}")
    root = Path(gemini_root)
    info: Dict[str, Dict[str, Any]] = {}
    models = set()
    sizes: Dict[str, int] = {}
    for rid in rows:
        entry: Dict[str, Any] = {"finished": False, "reason": None, "ends": {}, "round": round_of[rid]}
        info[rid] = entry
        p = root / rid / "row.json"
        if not p.is_file():
            entry["reason"] = "no row.json"
            continue
        try:
            doc = json.loads(p.read_text())
        except ValueError:
            entry["reason"] = "row.json unreadable"
            continue
        if not isinstance(doc, dict) or doc.get("row") != rid:
            raise Refused(f"refused: {p} does not name row {rid}")
        listed = doc.get("members") or []
        numbers = [m.get("member") if isinstance(m, dict) else None for m in listed]
        entry["ends"] = {int(m["member"]): m.get("end") for m in listed
                         if isinstance(m, dict) and isinstance(m.get("member"), int)}
        if not doc.get("done"):
            entry["reason"] = "not done (a member was cut short)"
            continue
        n = len(numbers)
        if n not in MEMBERS_PER_ROW or numbers != list(range(n)):
            raise Refused(f"refused: done row {rid} lists members {numbers}; expected 0 to n-1 with n in {MEMBERS_PER_ROW}")
        sizes[rid] = n
        if any(e not in FINAL_ENDS for e in entry["ends"].values()):
            entry["reason"] = "done but a member has an end that is neither ok nor dropped"
        else:
            entry["finished"] = True
            models.add(doc.get("model"))
    if len(set(sizes.values())) > 1:
        bad = {r: n for r, n in sizes.items() if n != next(iter(sizes.values()))}
        raise Refused(f"refused: done rows list different numbers of members; first row has {next(iter(sizes.values()))}, "
                      f"but {bad}")
    if not models:
        raise Refused("refused: no row is finished, so there is no Gemini output to score")
    if len(models) != 1:
        raise Refused(f"refused: finished rows name more than one model: {sorted(map(str, models))}")
    model = models.pop()
    if not isinstance(model, str) or not model.startswith("gemini-") or model in rs.ALL_MODELS:
        raise Refused(f"refused: row.json model {model!r} is not a gemini-* model name")
    in_play = sorted({round_of[r] for r in rows})
    not_done: Dict[str, str] = {}
    finished_rounds: List[int] = []
    for rnd in in_play:
        frame_ids = [rid for rid, _r, _s, rd in frame_rows if rd == rnd]
        for rid in frame_ids:
            if rid not in info:
                not_done[rid] = "not in the rows file"
            elif not info[rid]["finished"]:
                not_done[rid] = info[rid]["reason"]
        if all(rid in info and info[rid]["finished"] for rid in frame_ids):
            finished_rounds.append(rnd)
    confirmatory = [r for r in rows if info[r]["finished"] and info[r]["round"] in finished_rounds]
    exploratory = [r for r in rows if info[r]["finished"] and info[r]["round"] not in finished_rounds]
    return {"model": model, "rows": info, "rounds_in_play": in_play, "finished_rounds": finished_rounds,
            "members_per_row": next(iter(sizes.values())) if sizes else None,
            "confirmatory": confirmatory, "exploratory": exploratory, "not_done": not_done}


def build_members(ctx, replay: Mapping[str, Any], gemini_root: Path):
    """The frozen Claude path (`model_inputs`) reads a member with `load_doc` and `member_from_doc`; so does this.
    Only members whose end is ok are read; a dropped member is counted by `member_counts` and never scored.
    Returns (members by row, docs by row, ok members that could not be read, by row)."""
    members: Dict[str, List[Any]] = {}
    docs: Dict[str, Dict[int, dict]] = {}
    unreadable: Dict[str, List[int]] = {}
    for r in ctx.rows:
        mem, dd = [], {}
        info = replay["rows"].get(r.row_id)
        if info and info["finished"]:
            for k, end in sorted(info["ends"].items()):
                if end != "ok":
                    continue
                try:
                    doc = ep.load_doc(Path(gemini_root) / r.row_id / f"gemini_new_graph_{k}.yaml")
                    mem.append(ep.member_from_doc(doc, r.observed, k))
                    dd[k] = doc
                except (ValueError, OSError, KeyError, TypeError, yaml.YAMLError):
                    unreadable.setdefault(r.row_id, []).append(k)
        members[r.row_id], docs[r.row_id] = mem, dd
    return members, docs, unreadable


def member_counts(replay: Mapping[str, Any], row_ids: Sequence[str], unreadable: Mapping[str, Sequence[int]],
                  flag: bool = False) -> Dict[str, Any]:
    """Members of the given rows. A member marked ok whose file cannot be read has no score, so it is a drop: it
    counts in `dropped` and in the drop rate, and `ok_but_unreadable` keeps its own count beside them. `ok` is the
    members read and scored, so ok + dropped = members. `flag` adds the 25% flag (given on the total only)."""
    ends = [e for rid in row_ids for e in replay["rows"][rid]["ends"].values()]
    n = len(ends)
    bad = sum(len(unreadable.get(rid, ())) for rid in row_ids)
    dropped = sum(1 for e in ends if e in DROPPED_ENDS) + bad
    rate = dropped / n if n else None
    out = {"rows": len(row_ids), "members": n, "ok": ends.count("ok") - bad, "dropped_parse": ends.count("dropped_parse"),
           "dropped_error": ends.count("dropped_error"), "ok_but_unreadable": bad, "dropped": dropped, "drop_rate": rate}
    if flag:
        out["drop_rate_above_25_percent"] = bool(rate is not None and rate > DROP_FLAG)
    return out


# ----------------------------------------------------------------------- contrasts (section 5a)


def contrast_entry(rows: Sequence[Mapping[str, Any]], level: str, side, test: bool = True) -> Dict[str, Any]:
    """Cluster by cluster contrast of a model with another side, on the rows where both have a score.
    `side(record)` returns (difference, the other side's row score) or None. The cluster value is the mean over its
    rows; p is the frozen exact one-sided (model above) sign-flip test, the interval the frozen two-sided 95%."""
    diffs, mine, theirs = [], [], []
    for rec in rows:
        if not rec["possible"][level]:
            continue
        got = side(rec)
        if got is None:
            continue
        d, other = got
        diffs.append((rec["cluster"], d))
        mine.append((rec["cluster"], rs.model_row_score(rec, level)))
        theirs.append((rec["cluster"], other))
    cl = rs._cluster_values(diffs)
    d = [cl[c] for c in sorted(cl)]
    entry: Dict[str, Any] = {"n_clusters": len(d), "n_rows": len(diffs), "clusters": dict(sorted(cl.items())),
                             "mean_diff": sum(d) / len(d) if d else None, "p": None, "ci": None,
                             "model_clusters": dict(sorted(rs._cluster_values(mine).items())),
                             "other_clusters": dict(sorted(rs._cluster_values(theirs).items()))}
    entry["model_mean"] = rs._mean(entry["model_clusters"].values())
    entry["other_mean"] = rs._mean(entry["other_clusters"].values())
    if d and test:
        entry["p"] = stats.sign_flip_test(d, "greater").p
        entry["ci"] = tuple(stats.sign_flip_ci(d, 0.95, "two-sided"))
    return entry


def side_vs_model(other_by_row: Mapping[str, Mapping[str, Any]], level: str):
    """Gemini row score minus another model's row score (frozen `model_row_score`), same row."""
    def side(rec):
        o = other_by_row.get(rec["row_id"])
        if o is None:
            return None
        a, b = rs.model_row_score(rec, level), rs.model_row_score(o, level)
        return None if a is None or b is None else (a - b, b)
    return side


def side_vs_comparator(name: str, level: str):
    """Gemini minus a comparator of the frozen record (frozen `row_contrast`), same row."""
    def side(rec):
        d = rs.row_contrast(rec, name, level)
        if d is None:
            return None
        return d, rs._mean(rs._scores(rec["comparators"].get(name, {}), level).values())
    return side


def five_a(rows: Sequence[Mapping[str, Any]], others: Mapping[str, Sequence[Mapping[str, Any]]],
           confirmatory: bool = True) -> Dict[str, Any]:
    """Gemini against each other model and against B1, at L1, L2, L3. The family is {Opus, Haiku} x {L2, L3}:
    Holm over four. With fewer than 7 clusters in any of the four, it is exploratory and no hypothesis is called.
    L1 is reported and not tested. Outside the family (DeepSeek, B1) there is no Holm and no call.
    With confirmatory False (the exploratory set) nothing is called and Holm is not applied."""
    tables: Dict[str, Dict[str, Any]] = {}
    for name in OTHER_MODELS:
        by_row = {r["row_id"]: r for r in others.get(name, ())}
        tables[name] = {lv: contrast_entry(rows, lv, side_vs_model(by_row, lv), test=lv != "L1") for lv in LEVELS}
    tables["B1"] = {lv: contrast_entry(rows, lv, side_vs_comparator("B1", lv), test=lv != "L1") for lv in LEVELS}
    raw, missing = {}, []
    for m, lv in FAMILY_5A:
        p = tables[m][lv]["p"]
        if p is None:
            missing.append(f"{m}|{lv}")
            p = 1.0
        raw[f"{m}|{lv}"] = p
    adj = stats.holm(raw)
    n_min = min(tables[m][lv]["n_clusters"] for m, lv in FAMILY_5A)
    exploratory = (not confirmatory) or n_min < MIN_CLUSTERS_5A
    family: Dict[str, Any] = {}
    for m, lv in FAMILY_5A:
        key = f"{m}|{lv}"
        e = tables[m][lv]
        family[key] = {"model": m, "level": lv, "n_clusters": e["n_clusters"], "p": e["p"], "p_holm": adj[key],
                       "mean_diff": e["mean_diff"], "ci": e["ci"],
                       "found": None if exploratory else bool(adj[key] < rs.ALPHA)}
    label = None
    if not confirmatory:
        label = "exploratory: rows of a round that did not finish"
    elif n_min < MIN_CLUSTERS_5A:
        label = EXPLORATORY_LABEL
    return {"title": "Gemini in the author's loop against Claude in our port", "alpha": rs.ALPHA, "m_hypotheses": 4,
            "n_clusters_min_family": n_min, "exploratory": exploratory, "label": label,
            "missing_p": missing, "family": family, "tables": tables}


# ----------------------------------------------------------------------- the registered rule (5b)

def five_b(rows: Sequence[Mapping[str, Any]], model: str, confirmatory: bool = True) -> Dict[str, Any]:
    """Section 10 for Gemini, one level at a time, from the frozen `analyse` and `family`. Each level is its own
    hypothesis at alpha 0.05, with no Holm (a family of one). L3 is the confirmatory hypothesis; L1 and L2 are
    exploratory. With confirmatory False (the exploratory set) all three are exploratory. No thesis line."""
    full = rs.analyse(rows, model)
    out: Dict[str, Any] = {"levels": {}, "wrong_house_gate": {}}
    for lv in LEVELS:
        analysis = {"model": model, "levels": {lv: full["levels"][lv]}}
        fam = rs.family({model: analysis}, [])
        h = dict(fam["hypotheses"][f"{model}|{lv}"])
        comps = rs.HYPOTHESIS_COMPARATORS[lv] + rs.REPORTED_COMPARATORS[lv]
        own = {c: contrast_entry(rows, lv, side_vs_comparator(c, lv), test=False) for c in comps}
        for c in comps:                      # the same rows and the same arithmetic as the frozen `analyse`
            a, b = own[c]["mean_diff"], full["levels"][lv]["comparators"][c]["mean_diff"]
            if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-12):
                raise RuntimeError(f"{lv} {c}: own contrast {a} differs from the frozen analyse {b}")
        n_hyp = min([full["levels"][lv]["comparators"][c]["n_clusters"] for c in rs.HYPOTHESIS_COMPARATORS[lv]] or [0])
        h.update({"confirmatory": confirmatory and lv == "L3", "n_clusters": n_hyp,
                  "reaches_supported": n_hyp >= MIN_CLUSTERS_5B,
                  "model_cluster_scores": full["levels"][lv]["model_cluster_scores"],
                  "model_own_score": rs._mean(full["levels"][lv]["model_cluster_scores"].values()),
                  "comparators": {c: {**{k: full["levels"][lv]["comparators"][c][k] for k in ("n_clusters", "n_rows", "mean_diff", "p", "ci")},
                                      "model_mean": own[c]["model_mean"], "comparator_own_score": own[c]["other_mean"]}
                                  for c in comps}})
        out["levels"][lv] = h
        out["wrong_house_gate"].update({k.split("|")[1]: v for k, v in fam["wrong_house_gate"].items()})
    out["analysis"] = full
    return out


# -------------------------------------------------------------------------------------- wording

def display_name(model: str) -> str:
    return "Gemini " + " ".join(p.capitalize() for p in model.split("-")[1:])


def _pts(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{100 * x:+.1f}"


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _interval(ci) -> str:
    if ci is None:
        return "no interval"
    lo, hi = ci
    return f"95% interval [{_pts(lo) if math.isfinite(lo) else '-inf'}, {_pts(hi) if math.isfinite(hi) else '+inf'}] points"


def _short(model: str) -> str:
    return {"claude-opus-5-5": "Opus", "claude-haiku-5-5": "Haiku"}.get(model, model)


def wording(model: str, a5: Mapping[str, Any], b5: Mapping[str, Any]) -> List[str]:
    """The lines section 6 assigns to the outcome. For a fallback model every line names it and says it is not the paper's."""
    name = display_name(model)
    paper = model == "gemini-2.5-pro"
    note = "" if paper else f" {name} is not the paper's model."
    lines: List[str] = []
    fam = a5["family"]
    found = [v["found"] for v in fam.values()]
    if a5["exploratory"]:
        lines.append(f"5a is {a5['label'] or 'exploratory'}: no hypothesis is called. The four lines as they fall.{note}")
    elif all(found):
        who = "the paper's model" if paper else name
        lines.append(f"The Claude result does not carry over to {who}: on the same inputs {name} names more of what is "
                     f"there and puts more of it in fitting regions.{note}")
    elif not any(found):
        lines.append(f"On the same inputs {name}, in the author's loop, was not detectably above Claude.{note}")
    else:
        lines.append(f"5a, some hypotheses found and some not: the four lines as they fall.{note}")
    for key, v in fam.items():
        verb = "not called (exploratory)" if v["found"] is None else ("above" if v["found"] else "not detectably above")
        lines.append(f"{name} minus {_short(v['model'])} at {v['level']}: {_pts(v['mean_diff'])} points, {_interval(v['ci'])}, "
                     f"Holm p {v['p_holm']:.4f}, {v['n_clusters']} clusters; {verb}.{note}")
    l3 = b5["levels"]["L3"]
    ci = b5["analysis"]["levels"]["L3"]["comparators"]["D"]["ci"]
    tag = "" if l3["confirmatory"] else " (exploratory)"
    if l3["verdict"] == "Supported":
        lines.append(f"{name} puts its guesses in fitting regions more often than the controls{tag}.{note}")
    elif l3["verdict"] == "Rejected":
        lines.append(f"{name} did not beat a trade of region contents by the 3-point margin{tag}.{note}")
    else:
        lines.append(f"5b at L3{tag}: Inconclusive, {name} minus D {_pts(l3['comparators']['D']['mean_diff'])} points, {_interval(ci)}.{note}")
    lines.append(f"Saved inputs from two homes; no robot acted on these guesses; the comparators at L1 and L2 sit at the ceiling.{note}")
    return lines


# --------------------------------------------------------------------------------------- the run

def room_count_labels(replay_counts: Mapping[str, Any], n_members: int) -> List[Dict[str, Any]]:
    """The frozen replay count names its keys `predicted_<t>of4_...`; that "of4" is fixed text in the frozen code.
    Here each count is labelled with the members a row of this replay really has."""
    tot = replay_counts["totals"]
    return [{"label": f"{t} of {n_members} members, {kind}", "threshold": t, "typed": kind == "typed",
             "regions_predicted": tot.get(f"predicted_{t}of4_{kind}", 0), "regions_unseen_at_stage0": tot["of"]}
            for t in (1, 2) for kind in ("untyped", "typed")]


def set_report(label: str, row_ids: Sequence[str], confirmatory: bool, model: str, recs_by_id, others_by_id, views,
               specs, ctx, members, n_members: int, log) -> Dict[str, Any]:
    ids = set(row_ids)
    rows = [recs_by_id[r.row_id] for r in ctx.rows if r.row_id in ids]
    others = {m: [by[r["row_id"]] for r in rows if r["row_id"] in by] for m, by in others_by_id.items()}
    scored = [r for r in rows if r["model"]]
    out: Dict[str, Any] = {"label": label, "confirmatory": confirmatory, "rows": list(row_ids), "rows_with_a_score": len(scored),
                           "clusters": len({r["cluster"] for r in rows}), "clusters_with_a_score": len({r["cluster"] for r in scored})}
    out["5a"] = five_a(rows, others, confirmatory)
    out["5b"] = five_b(rows, model, confirmatory)
    sub_views = {v: [r for r in recs if r["row_id"] in ids] for v, recs in views.items()}
    sec = {v: rs.analyse(recs, model, levels=specs[v]["levels"]) for v, recs in sub_views.items()}
    out["5c"] = {"wrong_house_gate": out["5b"]["wrong_house_gate"], "secondary": sec, "extras": rs.extras_summary(rows),
                 "validity": rs.validity.summarise(rows) if any(r.get("validity") for r in rows) else None}
    if row_ids:
        sub_members = {rid: (ms if rid in ids else []) for rid, ms in members.items()}
        replay_counts = rs.run_room_test(ctx, [model], {model: (sub_members, {}, None, {})}, log)["replay"][model]
        out["5c"]["room_test_replay"] = replay_counts
        out["5c"]["room_count"] = room_count_labels(replay_counts, n_members)
    # Section 6 words the confirmatory result only. The exploratory set gets numbers and no sentence.
    if not confirmatory:
        out["wording"] = None
    elif not row_ids:
        out["wording"] = ["No round finished, so there is no confirmatory result and no sentence of section 6 applies."]
    else:
        out["wording"] = wording(model, out["5a"], out["5b"])
    return out


def run_analysis(gemini_root: Path, claude_root: Path, runs_root: Optional[Path] = None,
                 log=lambda s: None) -> Dict[str, Any]:
    """Everything, in memory. The guards are the caller's (main). The rows file (ROWS_FILE), the frame and the
    truth are the frozen ones. Reads only; changes no frozen module."""
    rows = read_rows(ROWS_FILE)
    replay = load_replay(gemini_root, rows, ep.parse_frame(rs.FRAME_PATH))
    model = replay["model"]
    n_members = replay["members_per_row"]
    ctx = rs.build_context(rs.FRAME_PATH, Path(runs_root or ep.RUNS_ROOT))
    placebo = rs.placebo_inputs(ctx)
    members, docs, unreadable = build_members(ctx, replay, gemini_root)
    log(f"read {sum(len(v) for v in members.values())} members of {model}")
    recs, errors, left_out = rs.score_model(ctx, model, members, docs, None, placebo[0], True)
    specs = rs.view_specs(ctx)
    views = rs.secondary_records(ctx, model, members, placebo[0], specs)
    others_by_id: Dict[str, Dict[str, Any]] = {}
    for name in OTHER_MODELS:
        if name != "deepseek" and not (Path(claude_root) / name).is_dir():
            raise Refused(f"refused: {Path(claude_root) / name} does not exist")
        inp = rs.model_inputs(ctx, name, Path(claude_root), placebo)
        orecs, _e, _l = rs.score_model(ctx, name, inp[0], inp[1], inp[2], placebo[0], False)
        others_by_id[name] = {r["row_id"]: r for r in orecs}
        log(f"scored {name}")
    recs_by_id = {r["row_id"]: r for r in recs}
    result: Dict[str, Any] = {"model": model, "replay": replay, "records": recs, "secondary_records": views,
                              "unreadable": unreadable, "skipped_counters": dict(ep.SKIPPED), "ctx": ctx}
    finished = replay["confirmatory"] + replay["exploratory"]
    result["analysis_set"] = {
        "rounds_in_play": replay["rounds_in_play"], "finished_rounds": replay["finished_rounds"],
        "members_per_row": n_members,
        "all_rows_run": member_counts(replay, finished, unreadable, flag=True),     # the 25% flag is on this total
        "confirmatory": member_counts(replay, replay["confirmatory"], unreadable),
        "exploratory": member_counts(replay, replay["exploratory"], unreadable),
        "not_done": replay["not_done"]}
    result["confirmatory"] = set_report("confirmatory", replay["confirmatory"], True, model, recs_by_id, others_by_id,
                                        views, specs, ctx, members, n_members, log)
    result["exploratory"] = set_report("exploratory", replay["exploratory"], False, model, recs_by_id, others_by_id,
                                       views, specs, ctx, members, n_members, log) if replay["exploratory"] else None
    return result


# -------------------------------------------------------------------------------------- writing

def _table_own_scores(rep: Mapping[str, Any]) -> List[str]:
    b5 = rep["5b"]
    lines = ["| level | Gemini | B3 | B1 | B5 | D | B3L |", "|---|---|---|---|---|---|---|"]
    for lv in LEVELS:
        h = b5["levels"][lv]
        cells = [_pct(h["model_own_score"])]
        for c in ("B3", "B1", "B5", "D", "B3L"):
            e = h["comparators"].get(c)
            cells.append(_pct(e["comparator_own_score"]) if e else "-")
        lines.append(f"| {lv} | " + " | ".join(cells) + " |")
    return lines


def _count_line(c: Mapping[str, Any]) -> str:
    rate = "n/a" if c["drop_rate"] is None else f"{100 * c['drop_rate']:.1f}%"
    flag = " (ABOVE 25%: flagged)" if c.get("drop_rate_above_25_percent") else ""
    return (f"{c['rows']} rows; {c['members']} members: {c['ok']} ok, {c['dropped']} dropped "
            f"({c['dropped_parse']} parse, {c['dropped_error']} error, {c['ok_but_unreadable']} ok but unreadable); "
            f"drop rate {rate}{flag}")


def render_md(res: Mapping[str, Any], run_info: Mapping[str, Any]) -> str:
    model, name = res["model"], display_name(res["model"])
    s = res["analysis_set"]
    L = [f"# Gemini replay: results ({name})", "",
         f"Model `{model}`. Frozen scorer; `freeze.py check` passed. Pre-registration sha256 `{run_info['prereg_sha256']}`.", "",
         "## Analysis set", "",
         f"- Rounds in play: {s['rounds_in_play']}; finished: {s['finished_rounds']}. Members per row: {s['members_per_row']}.",
         f"- All rows run (confirmatory and exploratory together; the 25% flag is on this total): {_count_line(s['all_rows_run'])}.",
         f"- Confirmatory (whole rounds finished): {_count_line(s['confirmatory'])}; "
         f"{res['confirmatory']['clusters']} clusters, {res['confirmatory']['rows_with_a_score']} rows with a score.",
         f"- Exploratory (finished rows of unfinished rounds): {_count_line(s['exploratory'])}.",
         f"- Rows not done ({len(s['not_done'])}): " + ("; ".join(f"{r} ({why})" for r, why in s["not_done"].items()) or "none") + ".", ""]
    for key in ("confirmatory", "exploratory"):
        rep = res[key]
        if rep is None:
            continue
        head = "Confirmatory set" if key == "confirmatory" else "Exploratory set (rows of unfinished rounds)"
        L += [f"## {head}", "", "### Own scores (mean over clusters, rows with a score; comparators on the rows shared with Gemini)", ""]
        L += _table_own_scores(rep)
        a = rep["5a"]
        L += ["", f"### 5a. {a['title']}", ""]
        if a["label"]:
            L += [f"**{a['label']}.** Fewest clusters among the four: {a['n_clusters_min_family']}.", ""]
        L += ["| contrast | level | clusters | Gemini | other | diff (pts) | p (one-sided) | Holm p | 95% interval | found |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for m in OTHER_MODELS + ("B1",):
            for lv in LEVELS:
                e = a["tables"][m][lv]
                f = a["family"].get(f"{m}|{lv}")
                p = "-" if e["p"] is None else f"{e['p']:.4f}"
                ph = "-" if f is None else f"{f['p_holm']:.4f}"
                found = "-" if f is None or f["found"] is None else ("yes" if f["found"] else "no")
                tag = "" if f else (" (outside family)" if lv != "L1" else " (reported, not tested)")
                if f is None and lv == "L1" and m in ("claude-opus-5-5", "claude-haiku-5-5"):
                    tag = " (reported, not tested)"
                L.append(f"| Gemini minus {_short(m)}{tag} | {lv} | {e['n_clusters']} | {_pct(e['model_mean'])} | {_pct(e['other_mean'])} "
                         f"| {_pts(e['mean_diff'])} | {p} | {ph} | {_interval(e['ci'])} | {found} |")
        b = rep["5b"]
        L += ["", "### 5b. The registered rule (section 10), one level at a time, no Holm; L3 is the confirmatory hypothesis", "",
              "| level | status | clusters | p (largest over comparators) | named | upper bound vs named (pts) | margin | verdict |",
              "|---|---|---|---|---|---|---|---|"]
        for lv in LEVELS:
            h = b["levels"][lv]
            up = h["ci_upper_named"]
            L.append(f"| {lv} | {'confirmatory' if h['confirmatory'] else 'exploratory'} | {h['n_clusters']} | {h['p']:.4f} | {h['named']} "
                     f"| {_pts(up)} | {_pts(h['delta'])[1:]} | {h['verdict']}{'' if h['reaches_supported'] else ' (fewer than 5 clusters: cannot be Supported)'} |")
        L += ["", "Ceiling: B3 scores about 100% at L1 and about 93% at L2, so Supported there is out of reach for most models. "
              "L3 has no such ceiling. No thesis line.", ""]
        L += ["### 5c. Reported, no verdict", ""]
        for lv, g in b["wrong_house_gate"].items():
            L.append(f"- Wrong-house gate {lv}: pairs {g['n_pairs']}, p {'-' if g['p'] is None else format(g['p'], '.4f')}, "
                     f"{'pass' if g['pass'] else 'no pass'}.")
        for c in rep["5c"].get("room_count", ()):
            L.append(f"- Paper's room count on these replays, {c['label']}: {c['regions_predicted']} of "
                     f"{c['regions_unseen_at_stage0']} regions unseen at stage 0.")
        L.append("- Secondary lines, extras and validity: `results.json`.")
        if rep["wording"]:
            L += ["", "### Wording", ""] + [f"- {w}" for w in rep["wording"]]
        else:
            L += ["", "No sentence of section 6 is written for the exploratory set."]
        L.append("")
    return "\n".join(L)


def write_outputs(res: Mapping[str, Any], out: Path, run_info: Mapping[str, Any]) -> List[str]:
    out = Path(out)
    model = res["model"]
    rs._write(out / f"records_{model}.json", {"records": res["records"], "secondary_records": res["secondary_records"]})
    summary = {"run_info": run_info, "model": model, "analysis_set": res["analysis_set"],
               "rows": {rid: {k: v for k, v in info.items() if k != "finished"} | {"finished": info["finished"]}
                        for rid, info in res["replay"]["rows"].items()},
               "unreadable": res["unreadable"], "confirmatory": res["confirmatory"], "exploratory": res["exploratory"]}
    rs._write(out / "results.json", summary)
    (out / "RESULTS_GEMINI.md").write_text(render_md(res, run_info))
    return [f"records_{model}.json", "results.json", "RESULTS_GEMINI.md"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False)
    ap.add_argument("--gemini-root", required=True, help="<root>/<row_id>/row.json and gemini_new_graph_<k>.yaml")
    ap.add_argument("--claude-root", required=True, help="<root>/<model>/effort_medium/<row_id>/member_<k>/")
    ap.add_argument("--prereg-sha256", required=True,
                    help="must equal the first field of PREREGISTRATION_GEMINI.sha256")
    ap.add_argument("--out", required=True, help="a new folder; not under hm3d_refs_work/gemini_static*")
    ap.add_argument("--runs-root", default=None, help="the saved runs (default: the laptop copy)")
    ap.add_argument("--overwrite", action="store_true", help="allow --out to hold a results.json already")
    a = ap.parse_args(argv)
    out = Path(a.out)
    check_paths(Path(a.gemini_root), out)
    prereg_sha = check_guards(a.prereg_sha256)           # before any model output is touched
    if (out / "results.json").exists() and not a.overwrite:
        raise Refused(f"refused: {out / 'results.json'} exists; name a new --out or pass --overwrite")
    res = run_analysis(Path(a.gemini_root), Path(a.claude_root), a.runs_root, log=lambda s: print(s, file=sys.stderr))
    run_info = {"model": res["model"],
                "argv": list(argv) if argv is not None else sys.argv[1:],
                "arguments": {"gemini_root": str(a.gemini_root), "claude_root": str(a.claude_root),
                              "prereg_sha256": a.prereg_sha256, "out": str(a.out),
                              "runs_root": str(a.runs_root) if a.runs_root else None, "overwrite": bool(a.overwrite)},
                "paths_used": {"prereg": str(PREREG_PATH), "prereg_hash_file": str(PREREG_HASH_PATH),
                               "rows_file": str(ROWS_FILE), "frame": str(rs.FRAME_PATH), "truth_dir": "frozen default",
                               "runs_root": str(a.runs_root or ep.RUNS_ROOT), "claude_root": str(a.claude_root)},
                "prereg_sha256": prereg_sha, "rows_file_sha256": rs._sha(ROWS_FILE), "rows_file_pinned_sha256": ROWS_FILE_SHA256,
                "freeze_holds": True, "freeze_sha256": rs._sha(rs.FREEZE_PATH),
                "frozen_prereg_sha256": rs.verify_prereg_file(), "frame_sha256": rs._sha(rs.FRAME_PATH),
                "semantic_gemini_sha256": sha256_file(Path(__file__)), "python": platform.python_version(),
                "skipped_counters": res["skipped_counters"]}
    files = write_outputs(res, out, run_info)
    print("wrote", ", ".join(files), "to", out)
    for line in res["confirmatory"]["wording"]:      # the confirmatory set only
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
