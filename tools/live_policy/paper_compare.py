"""Score runs on the paper's scale (PREREGISTRATION_PAPER.md sections 1 and 4).

F1 follows the author's f1_score_plot.py, copied rather than imported:
- objects are nodes with node_type 'object' whose name is not 'door';
- each predicted object, in file order, takes the nearest unmatched reference
  object with the same name, and counts as a match if the distance is below
  0.5 (strict);
- precision, recall and F1 are computed per graph; the stage value is the mean
  over the graph0 and graph1 YAMLs that exist.
tools/evaluator (graph_io + matching, used by live_score.py as af_f1) has the
same matching loop. It is not reused because its loader drops 'door' in any
letter case, which the author's does not, and it keys nodes by id, which would
merge duplicate ids. Both differences are idle on the campaign data (checked),
and the tests compare the two on random graphs.

Time axis: total_navigation_time_seconds of each stage's navigation_stats.json.
A stage with no such file, or with no graph YAML, is skipped (as the author
does), and so is a stage whose stats lack the path length or the time.

Readout at time t: the stage value at the last stage whose time is at most t.
A run whose last scored stage ends before t has no value at t (null, never
held). A run whose first stage starts after t is also null. The running
maximum over stages up to t (the author's plot rule) is reported beside it.
Times compare with a small tolerance (--time-tol) because budgets come from
rounded figures.

The budget B per scene defaults to the end of the frontier-made reference run.
Readouts sit at 10%, 50% and 100% of B, and of 0.8 B and 1.2 B.

GED comes from --ged-json files that tools/live_policy/paper_ged.py writes on the host
with the author's own ged_score_plot.CustomGED (gmatch4py). Without them every "ged"
field is null.

Usage (--out-dir is required, so a rerun never overwrites a frozen results folder):
    python paper_compare.py --out-dir /tmp/pc       # default run list
    python paper_compare.py --out-dir /tmp/pc --no-default-runs \\
        --add-run frontier_end=00853=/path/to/runs/e7_00853_s42_frontier_end \\
        --apr 00853=/path/to/apr_00853_a --budget 00853=700
"""
from __future__ import annotations

import argparse
import ast
import csv
import glob
import json
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
DEFAULT_ROOT = Path("/Users/sher/cvp_live_campaign_copy")
DEFAULT_PAPER_HTML = PROJECT / ".firecrawl" / "arxiv-2510.05430-html.md"
# Holds the final stage of each frontier-made reference run with its
# navigation_stats.json, which the off-host copy lacks.
DEFAULT_FALLBACK = PROJECT / "tyrone_mirror" / "runs"

THRESHOLD = 0.5
TIME_TOL = 1e-3
GRAPHS = (0, 1)
FRACTIONS = (("10", 0.1), ("50", 0.5), ("100", 1.0))
VARIANTS = (("B", 1.0), ("0.8B", 0.8), ("1.2B", 1.2))
PRIMARY = "B"
COUNTED_ARMS = ("official", "placebo", "filter_only", "oracle_visible")
ARM_ORDER = ("official", "filter_only", "placebo", "oracle_visible", "frontier_60m",
             "frontier_end_ref", "frontier_end")
REF_ORDER = ("hm3d", "apr", "frontier_made")

# Pre-registered fallback: end of the frontier-made reference run (seconds).
DEFAULT_BUDGET = {"00853": 632.1256, "00871": 809.0840}
REF_RUNS = {"00853": ("scene00853_frontier_reference", 33),
            "00871": ("scene00871_frontier_reference", 54)}
# Same files live_score.py reads (REFS_HM3D); never the _extended files.
HM3D_FILES = {"00853": "00853_hm3d_reference.yaml", "00871": "00871_hm3d_reference.yaml"}

# Paper Fig. 4 (left): F1 x 100 and GED at 10%, 50%, 100% of the time budget.
PAPER = {
    "00853": {"Frontier": {"f1": (18.6, 46.5, 58.8), "ged": (279.0, 243.4, 177.0)},
              "SSMI": {"f1": (28.5, 49.5, 61.1), "ged": (280.3, 218.0, 189.0)},
              "Semantic (Ours)": {"f1": (34.4, 60.8, 66.7), "ged": (249.5, 147.0, 147.0)}},
    "00871": {"Frontier": {"f1": (29.2, 55.7, 65.3), "ged": (292.1, 233.0, 203.5)},
              "SSMI": {"f1": (33.4, 59.1, 61.7), "ged": (277.3, 212.4, 204.5)},
              "Semantic (Ours)": {"f1": (30.5, 62.4, 68.0), "ged": (279.0, 204.5, 194.5)}},
    "00069": {"Frontier": {"f1": (23.8, 40.6, 59.7), "ged": (253.0, 213.0, 149.0)},
              "SSMI": {"f1": (25.9, 50.0, 63.1), "ged": (269.2, 194.0, 158.0)},
              "Semantic (Ours)": {"f1": (25.8, 60.1, 62.2), "ged": (266.3, 148.0, 148.0)}},
    "00573": {"Frontier": {"f1": (19.9, 46.1, 63.0), "ged": (231.4, 193.0, 185.0)},
              "SSMI": {"f1": (12.2, 52.1, 56.8), "ged": (261.0, 187.5, 187.5)},
              "Semantic (Ours)": {"f1": (19.2, 59.0, 68.7), "ged": (252.6, 170.5, 163.5)}},
}
PAPER_LABELS = {"Frontier": "Frontier", "SSMI": "SSMI", "Semantic (Ours)": "Ours(ASP)"}

_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


@dataclass
class RunSpec:
    name: str
    arm: str
    scene: str
    path: Path
    seed: int | None = None


# --------------------------------------------------------------------------
# The author's F1 rule
# --------------------------------------------------------------------------

def _literal(expr):
    return ast.literal_eval(expr) if isinstance(expr, str) else expr


def parse_objects(path) -> list:
    """Object nodes of one graph YAML, in file order, as (name, position)."""
    with open(path, "r") as f:
        graph = yaml.load(f, Loader=_LOADER) or {}
    objects = []
    for node in graph.get("nodes", []) or []:
        if node.get("node_type") == "object" and node.get("name") != "door":
            objects.append((node.get("name"), np.array(_literal(node["position"]), dtype=float)))
    return objects


def f1_score(gt_objects, pred_objects, threshold: float = THRESHOLD):
    """Return (f1, precision, recall). Mirrors calculate_f1_score in f1_score_plot.py."""
    if not gt_objects or not pred_objects:
        return 0.0, 0.0, 0.0
    available = list(range(len(gt_objects)))
    true_positives = 0
    for name, position in pred_objects:
        best_idx = -1
        min_dist = float("inf")
        for gt_idx in available:
            gt_name, gt_position = gt_objects[gt_idx]
            if name == gt_name:
                dist = float(np.linalg.norm(position - gt_position))
                if dist < min_dist:
                    min_dist = dist
                    best_idx = gt_idx
        if min_dist < threshold:
            true_positives += 1
            available.remove(best_idx)
    false_positives = len(pred_objects) - true_positives
    false_negatives = len(gt_objects) - true_positives
    precision = true_positives / (true_positives + false_positives)
    recall = true_positives / (true_positives + false_negatives)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
    return f1, precision, recall


# (run name, stage) -> {reference name: GED}, filled from --ged-json files.
GED_LOOKUP: dict = {}


def load_ged_json(path) -> int:
    """Read one paper_ged.py output into GED_LOOKUP. Later files override earlier ones."""
    data = json.loads(Path(path).read_text())
    n = 0
    for run in data["runs"]:
        name = Path(run["run_dir"]).name
        for row in run["stages"]:
            values = {k[len("ged_"):]: v for k, v in row.items() if k.startswith("ged_")}
            GED_LOOKUP.setdefault((name, int(row["stage"])), {}).update(values)
            n += 1
    return n


def ged_stage_value(pred_yamls, ref_yaml, ref_name=None):
    """The author-method GED of PREREGISTRATION_PAPER.md section 1 for one stage.

    paper_ged.py already averaged it over graph0 and graph1. The stage is found
    from the first graph path: <run>/stages/<k>/habitat_scene_graph_original_graph*.yaml.
    """
    if not pred_yamls or ref_name is None:
        return None
    first = Path(pred_yamls[0])
    try:
        key = (first.parents[2].name, int(first.parent.name))
    except (IndexError, ValueError):
        return None
    return GED_LOOKUP.get(key, {}).get(ref_name)


# --------------------------------------------------------------------------
# Reading stages
# --------------------------------------------------------------------------

def _stage_dirs(run_dir: Path, fallback_roots) -> list:
    found = set()
    for base in [run_dir] + [r / run_dir.name for r in fallback_roots]:
        sd = base / "stages"
        if sd.is_dir():
            found.update(int(e.name) for e in sd.iterdir() if e.name.isdigit() and e.is_dir())
    return sorted(found)


def _stage_file(run_dir: Path, fallback_roots, stage: int, name: str):
    """Return (path, source) with source 'run' or the fallback root, or (None, None)."""
    primary = run_dir / "stages" / str(stage) / name
    if primary.exists():
        return primary, "run"
    for root in fallback_roots:
        alt = root / run_dir.name / "stages" / str(stage) / name
        if alt.exists():
            return alt, str(root)
    return None, None


def load_stages(run_dir: Path, fallback_roots=()):
    """Return (stages, skipped, missing).

    stages: scorable stages in stage order, each with time_s, path_m and the
    graph paths that exist. skipped: stages the author's rules drop, with the
    reason. missing: every stage file absent from the run dir, and whether a
    fallback root supplied it.
    """
    stages, skipped, missing = [], [], []
    for stage in _stage_dirs(run_dir, fallback_roots):
        nav, nav_src = _stage_file(run_dir, fallback_roots, stage, "navigation_stats.json")
        graphs = {}
        for gi in GRAPHS:
            gp, gsrc = _stage_file(run_dir, fallback_roots, stage,
                                   f"habitat_scene_graph_original_graph{gi}.yaml")
            if gp is not None:
                graphs[gi] = (gp, gsrc)
        for fname, found in [("navigation_stats.json", nav)] + [
                (f"habitat_scene_graph_original_graph{gi}.yaml", graphs.get(gi, (None,))[0])
                for gi in GRAPHS]:
            in_run = (run_dir / "stages" / str(stage) / fname).exists()
            if not in_run:
                missing.append({"stage": stage, "file": fname, "filled_from_fallback": found is not None})
        if nav is None:
            skipped.append({"stage": stage, "reason": "no_navigation_stats"})
            continue
        if not graphs:
            skipped.append({"stage": stage, "reason": "no_graph_yaml"})
            continue
        try:
            with open(nav, "r") as f:
                stats = json.load(f)
        except (OSError, ValueError):
            skipped.append({"stage": stage, "reason": "bad_navigation_stats"})
            continue
        path_m = stats.get("total_path_length_meters")
        time_s = stats.get("total_navigation_time_seconds")
        if path_m is None:
            skipped.append({"stage": stage, "reason": "no_path_length"})
            continue
        if time_s is None:
            skipped.append({"stage": stage, "reason": "no_navigation_time"})
            continue
        stages.append({"stage": stage, "time_s": float(time_s), "path_m": float(path_m),
                       "graphs": {gi: gp for gi, (gp, _) in graphs.items()},
                       "sources": sorted({src for _, src in graphs.values()} | {nav_src})})
    return stages, skipped, missing


def stage_scores(stage, refs_for_scene: dict, cache: dict) -> dict:
    """Per reference: mean precision, recall and F1 over the graphs that exist."""
    parsed = []
    for gi in sorted(stage["graphs"]):
        gp = stage["graphs"][gi]
        if gp not in cache:
            cache[gp] = parse_objects(gp)
        parsed.append(cache[gp])
    out = {}
    for ref_name, ref in refs_for_scene.items():
        triples = [f1_score(ref["objects"], objs) for objs in parsed]
        out[ref_name] = {
            "f1": sum(t[0] for t in triples) / len(triples),
            "precision": sum(t[1] for t in triples) / len(triples),
            "recall": sum(t[2] for t in triples) / len(triples),
            "ged": ged_stage_value(list(stage["graphs"].values()), ref["path"], ref_name),
        }
    return out


# --------------------------------------------------------------------------
# Readouts
# --------------------------------------------------------------------------

def pick_stages(stages: list, t: float, tol: float = TIME_TOL):
    """Return (eligible stages up to t, null reason). The last eligible one is the readout."""
    if not stages:
        return None, "no_scored_stages"
    if max(s["time_s"] for s in stages) + tol < t:
        return None, "run_ended_before_t"
    eligible = [s for s in stages if s["time_s"] <= t + tol]
    if not eligible:
        return None, "no_stage_at_or_before_t"
    return eligible, None


def readout(stages: list, ref_name: str, t: float, tol: float = TIME_TOL) -> dict:
    eligible, reason = pick_stages(stages, t, tol)
    entry = {"t_s": t, "stage": None, "stage_time_s": None, "f1": None, "f1_runmax": None,
             "precision": None, "recall": None, "ged": None, "null_reason": reason}
    if eligible is None:
        return entry
    last = eligible[-1]
    entry.update({
        "stage": last["stage"], "stage_time_s": last["time_s"],
        "f1": last["scores"][ref_name]["f1"],
        "f1_runmax": max(s["scores"][ref_name]["f1"] for s in eligible),
        "precision": last["scores"][ref_name]["precision"],
        "recall": last["scores"][ref_name]["recall"],
        "ged": last["scores"][ref_name]["ged"],
    })
    return entry


def build_readouts(stages: list, refs_for_scene: dict, budget: float, tol: float) -> dict:
    out = {}
    for ref_name in refs_for_scene:
        out[ref_name] = {}
        for vname, vmult in VARIANTS:
            out[ref_name][vname] = {
                flabel: readout(stages, ref_name, budget * vmult * frac, tol)
                for flabel, frac in FRACTIONS}
    return out


def score_run(spec: RunSpec, refs: dict, budgets: dict, fallback_roots, tol: float = TIME_TOL) -> dict:
    refs_for_scene = {name: by_scene[spec.scene] for name, by_scene in refs.items() if spec.scene in by_scene}
    record = {"run": spec.name, "arm": spec.arm, "scene": spec.scene, "seed": spec.seed,
              "path": str(spec.path)}
    if not (spec.path / "stages").is_dir() and not any((r / spec.path.name / "stages").is_dir() for r in fallback_roots):
        record["error"] = "no stages directory"
        return record
    stages, skipped, missing = load_stages(spec.path, fallback_roots)
    cache = {}
    for s in stages:
        s["scores"] = stage_scores(s, refs_for_scene, cache)
    last = stages[-1] if stages else None
    record.update({
        "n_stages_scored": len(stages),
        "skipped_stages": skipped,
        "missing_files": missing,
        "time_monotone": all(a["time_s"] <= b["time_s"] for a, b in zip(stages, stages[1:])),
        "final_stage": last["stage"] if last else None,
        "final_path_m": last["path_m"] if last else None,
        "final_time_s": last["time_s"] if last else None,
        "sec_per_m": (last["time_s"] / last["path_m"]) if last and last["path_m"] > 0 else None,
        "stages": [{"stage": s["stage"], "time_s": s["time_s"], "path_m": s["path_m"],
                    "n_graphs": len(s["graphs"]), "sources": s["sources"],
                    "scores": {r: {k: v for k, v in sc.items() if k != "ged"}
                               for r, sc in s["scores"].items()}} for s in stages],
        "readouts": build_readouts(stages, refs_for_scene, budgets[spec.scene], tol),
    })
    return record


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------

def paper_method(arm: str):
    if arm.startswith("frontier"):
        return "Frontier"
    if arm in ("official", "filter_only"):
        return "Semantic (Ours)"
    return None


def summarise(values: list) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"mean": None, "min": None, "max": None, "n": 0}
    return {"mean": statistics.mean(vals), "min": min(vals), "max": max(vals), "n": len(vals)}


def _x100(entries: list, key: str) -> list:
    return [None if e[key] is None else 100.0 * e[key] for e in entries]


def aggregate(records: list) -> list:
    """Cells over (scene, arm, reference, variant, fraction); F1 values are x 100."""
    groups = {}
    for rec in records:
        for ref_name, by_variant in rec.get("readouts", {}).items():
            for vname, by_frac in by_variant.items():
                for flabel, entry in by_frac.items():
                    groups.setdefault((rec["scene"], rec["arm"], ref_name, vname, flabel), []).append(entry)
    cells = []
    frac_index = {label: i for i, (label, _) in enumerate(FRACTIONS)}
    for (scene, arm, ref_name, vname, flabel), entries in sorted(groups.items()):
        method = paper_method(arm)
        paper = PAPER.get(scene, {}).get(method) if method else None
        i = frac_index[flabel]
        cells.append({
            "scene": scene, "arm": arm, "reference": ref_name, "variant": vname, "fraction": flabel,
            "n_runs": len(entries),
            "stage_value_x100": summarise(_x100(entries, "f1")),
            "running_max_x100": summarise(_x100(entries, "f1_runmax")),
            "ged": summarise([e["ged"] for e in entries]),
            "paper_method": method,
            "paper_f1_x100": paper["f1"][i] if paper else None,
            "paper_ged": paper["ged"][i] if paper else None,
        })
    return cells


def seconds_per_metre(records: list) -> list:
    groups = {}
    for rec in records:
        groups.setdefault((rec["scene"], rec["arm"]), []).append(rec)
    out = []
    for (scene, arm), recs in sorted(groups.items()):
        out.append({"scene": scene, "arm": arm, "n_runs": len(recs),
                    "sec_per_m": summarise([r.get("sec_per_m") for r in recs]),
                    "final_time_s": summarise([r.get("final_time_s") for r in recs]),
                    "final_path_m": summarise([r.get("final_path_m") for r in recs])})
    return out


# --------------------------------------------------------------------------
# Paper table check
# --------------------------------------------------------------------------

def parse_paper_fig4(text: str) -> dict:
    """Read Fig. 4 (left) from the flattened arXiv HTML text.

    The HTML joins the cells with no separator, but every number has one
    decimal, so each number matches \\d+\\.\\d. Each row holds 12 numbers: for
    the two scenes named by the header above it, F1 and GED at 10%, 50%, 100%.
    """
    labels = ("Frontier", "SSMI", "Semantic (Ours)")
    start = text.index("Scene: ", text.index("GED"))
    block = text[start:].split("\n", 1)[0]  # the table is one line; the next line is another table
    out = {}
    for header in re.finditer(r"Scene: (\d+)Scene: (\d+)", block):
        left, right = (s.zfill(5) for s in header.groups())
        rest = block[header.end():]
        nxt = re.search(r"Scene: \d+Scene: \d+", rest)
        rest = rest[:nxt.start()] if nxt else rest
        parts = re.split(r"(Frontier|SSMI|Semantic \(Ours\))", rest)
        for label, body in zip(parts[1::2], parts[2::2]):
            nums = [float(x) for x in re.findall(r"\d+\.\d", body)]
            if len(nums) != 12 or label not in labels:
                continue
            for scene, chunk in ((left, nums[:6]), (right, nums[6:])):
                out.setdefault(scene, {})[label] = {
                    "f1": (chunk[0], chunk[2], chunk[4]), "ged": (chunk[1], chunk[3], chunk[5])}
    return out


def check_paper_table(html_path) -> dict:
    path = Path(html_path)
    if not path.exists():
        return {"checked": False, "reason": f"{path} not found", "mismatches": []}
    parsed = parse_paper_fig4(path.read_text())
    mismatches = []
    for scene in sorted(set(PAPER) | set(parsed)):
        for label in sorted(set(PAPER.get(scene, {})) | set(parsed.get(scene, {}))):
            if PAPER.get(scene, {}).get(label) != parsed.get(scene, {}).get(label):
                mismatches.append({"scene": scene, "method": label,
                                   "embedded": PAPER.get(scene, {}).get(label),
                                   "html": parsed.get(scene, {}).get(label)})
    return {"checked": True, "mismatches": mismatches}


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------

def default_runs(root: Path, run_table: Path) -> list:
    runs, seen = [], set()
    with open(run_table, newline="") as f:
        for row in csv.DictReader(f):
            name = row["run"]
            if row["status"].strip() != "counted" or row["arm"] not in COUNTED_ARMS or name in seen:
                continue
            seen.add(name)
            runs.append(RunSpec(name, row["arm"], row["scene"], root / "runs" / "live_campaign" / name,
                                int(row["seed"]) if row.get("seed") else None))
    for d in sorted(glob.glob(str(root / "runs" / "frontier_seeds" / "e4_*_frontier_60m"))):
        m = re.match(r"e4_(\d{5})_s(\d+)_frontier_60m$", Path(d).name)
        if m:
            runs.append(RunSpec(Path(d).name, "frontier_60m", m.group(1), Path(d), int(m.group(2))))
    for scene, (dirname, _) in REF_RUNS.items():
        runs.append(RunSpec(dirname, "frontier_end_ref", scene, root / "runs" / dirname))
    return runs


def load_reference(path) -> dict:
    return {"path": str(path), "objects": parse_objects(path)}


def resolve_reference_yaml(path: Path) -> Path:
    """A graph YAML as given, or the graph0 of the last stage of a run dir."""
    path = Path(path)
    if path.is_file():
        return path
    stages = path / "stages" if (path / "stages").is_dir() else path
    nums = sorted((int(e.name) for e in stages.iterdir() if e.name.isdigit()), reverse=True)
    for n in nums:
        cand = stages / str(n) / "habitat_scene_graph_original_graph0.yaml"
        if cand.exists():
            return cand
    raise FileNotFoundError(f"no graph0 YAML under {path}")


def build_references(root: Path, apr: dict) -> dict:
    refs = {"hm3d": {}, "frontier_made": {}, "apr": {}}
    for scene, fname in HM3D_FILES.items():
        p = root / "runs" / "live_campaign" / "hm3d_refs_work" / fname
        if p.exists():
            refs["hm3d"][scene] = load_reference(p)
    for scene, (dirname, stage) in REF_RUNS.items():
        p = root / "runs" / dirname / "stages" / str(stage) / "habitat_scene_graph_original_graph0.yaml"
        if p.exists():
            refs["frontier_made"][scene] = load_reference(p)
    for scene, p in apr.items():
        refs["apr"][scene] = load_reference(resolve_reference_yaml(p))
    return {name: by_scene for name, by_scene in refs.items() if by_scene}


def _pairs(items, label) -> dict:
    out = {}
    for item in items or []:
        if "=" not in item:
            sys.exit(f"{label}: expected SCENE=VALUE, got {item!r}")
        scene, value = item.split("=", 1)
        out[scene] = value
    return out


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------

def _fmt(s: dict, n_runs: int) -> str:
    if not s or s["n"] == 0:
        return f"null (0/{n_runs})"
    n = f"n={s['n']}" if s["n"] == n_runs else f"n={s['n']}/{n_runs}"
    return f"{s['mean']:.1f} [{s['min']:.1f}-{s['max']:.1f}] {n}"


def _arm_key(arm):
    return (ARM_ORDER.index(arm) if arm in ARM_ORDER else len(ARM_ORDER), arm)


def _span(rows: list, arms) -> str | None:
    sel = [r["final_time_s"] for r in rows if r["arm"] in arms and r["final_time_s"]["n"]]
    if not sel:
        return None
    return f"{min(x['min'] for x in sel):.0f}-{max(x['max'] for x in sel):.0f} s"


def build_markdown(result: dict) -> str:
    cells = result["cells"]
    meta = result["meta"]
    lines = ["# Scores on the paper's scale", "",
             "F1 x 100, stage value at the last stage with navigation time at most t. "
             "Each cell reads `mean [min-max] n`; n counts runs with a value at t. "
             "The paper column is Fig. 4 (left) of arXiv 2510.05430v2. "
             "Budget B: " + ", ".join(f"{s} = {b:.4f} s ({meta.get('budget_sources', {}).get(s, 'default')})"
                                      for s, b in sorted(meta["budgets"].items())) + ".", ""]
    for ref_name in [r for r in REF_ORDER if r in meta["references"]]:
        info = meta["references"][ref_name]
        lines += [f"## Reference: {ref_name}", ""]
        if info.get("biased_toward_frontier"):
            lines += ["This reference comes from the frontier explorer, so it favours frontier arms. "
                      "The frontier_end_ref run scored against its own final map is self-referential.", ""]
        lines += ["| Scene | Arm | Paper method | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |",
                  "|---|---|---|---|---|---|---|---|---|"]
        sel = [c for c in cells if c["reference"] == ref_name and c["variant"] == PRIMARY]
        for scene, arm in sorted({(c["scene"], c["arm"]) for c in sel}, key=lambda k: (k[0], _arm_key(k[1]))):
            row = {c["fraction"]: c for c in sel if c["scene"] == scene and c["arm"] == arm}
            method = paper_method(arm)
            parts = [scene, arm, PAPER_LABELS.get(method, "none") if method else "none"]
            for flabel, _ in FRACTIONS:
                c = row[flabel]
                parts.append(_fmt(c["stage_value_x100"], c["n_runs"]))
                parts.append("-" if c["paper_f1_x100"] is None else f"{c['paper_f1_x100']:.1f}")
            lines.append("| " + " | ".join(parts) + " |")
        lines += ["", "Sensitivity, means only (F1 x 100), at 10/50/100% of 0.8 B and of 1.2 B; `-` means no run has a value.", "",
                  "| Scene | Arm | 0.8B 10% | 0.8B 50% | 0.8B 100% | 1.2B 10% | 1.2B 50% | 1.2B 100% |",
                  "|---|---|---|---|---|---|---|---|"]
        sens = [c for c in cells if c["reference"] == ref_name and c["variant"] != PRIMARY]
        for scene, arm in sorted({(c["scene"], c["arm"]) for c in sens}, key=lambda k: (k[0], _arm_key(k[1]))):
            parts = [scene, arm]
            for vname in ("0.8B", "1.2B"):
                for flabel, _ in FRACTIONS:
                    c = next(c for c in sens if (c["scene"], c["arm"], c["variant"], c["fraction"]) == (scene, arm, vname, flabel))
                    m = c["stage_value_x100"]["mean"]
                    parts.append("-" if m is None else f"{m:.1f} (n={c['stage_value_x100']['n']})")
            lines.append("| " + " | ".join(parts) + " |")
        lines.append("")
    if any(c["ged"]["n"] for c in cells):
        lines += ["## GED (the author's own code)", "",
                  "gmatch4py GraphEditDistance(1, 1, 1, 1) with the author's costs, mean over graph0 and graph1, "
                  "stage value at t. Lower is better. `mean [min-max] n`.", ""]
        for ref_name in [r for r in REF_ORDER if r in meta["references"]]:
            sel = [c for c in cells if c["reference"] == ref_name and c["variant"] == PRIMARY]
            if not any(c["ged"]["n"] for c in sel):
                continue
            lines += [f"### Reference: {ref_name}", "",
                      "| Scene | Arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |",
                      "|---|---|---|---|---|---|---|---|"]
            for scene, arm in sorted({(c["scene"], c["arm"]) for c in sel}, key=lambda k: (k[0], _arm_key(k[1]))):
                row = {c["fraction"]: c for c in sel if c["scene"] == scene and c["arm"] == arm}
                parts = [scene, arm]
                for flabel, _ in FRACTIONS:
                    g = row[flabel]["ged"]
                    parts.append("null" if not g["n"] else
                                 (f"{g['mean']:.0f}" if g["n"] == 1 else f"{g['mean']:.0f} [{g['min']:.0f}-{g['max']:.0f}] n={g['n']}"))
                    pg = row[flabel]["paper_ged"]
                    parts.append("-" if pg is None else f"{pg:.1f}")
                lines.append("| " + " | ".join(parts) + " |")
            lines.append("")
    lines += ["## Seconds per metre", "",
              "Final navigation time over final path length, from each run's last scored stage.", "",
              "| Scene | Arm | Runs | s/m mean [min-max] | Final time s (mean) | Final path m (mean) |",
              "|---|---|---|---|---|---|"]
    for r in sorted(result["seconds_per_metre"], key=lambda r: (r["scene"], _arm_key(r["arm"]))):
        s = r["sec_per_m"]
        if s["n"] == 0:
            lines.append(f"| {r['scene']} | {r['arm']} | {r['n_runs']} | null | null | null |")
            continue
        lines.append(f"| {r['scene']} | {r['arm']} | {r['n_runs']} | {s['mean']:.2f} [{s['min']:.2f}-{s['max']:.2f}] "
                     f"| {r['final_time_s']['mean']:.1f} | {r['final_path_m']['mean']:.1f} |")
    asp = _span(result["seconds_per_metre"], COUNTED_ARMS)
    frontier = _span(result["seconds_per_metre"], ("frontier_60m",))
    lines += ["", "## Not comparable", "",
              "- The references differ. The paper scores against a hand-driven full-scene map. "
              "We use the HM3D human-label map, the frontier-made map (biased toward frontier), "
              "and a coverage-tour map when one exists.",
              "- ASP runs stop at 60 m of path" + (f", which took {asp} here" if asp else "")
              + ". A run has no value at a t past its last stage, so its 100% readout is null, "
              "and a 50% readout is null when the run ended sooner.",
              "- The e4 frontier runs stop at 60 m too" + (f" ({frontier})" if frontier else "")
              + ", so their 100% readout is null as well. Only the frontier-to-end runs reach B.",
              "- Navigation time counts moving time only, so it depends on seconds per metre, which differs by arm.",
              "- Scenes 00069 and 00573 have no run here; their paper cells stay in the JSON only.",
              ("- GED comes from the author's own code on the host; see the GED section."
               if any(c["ged"]["n"] for c in cells) else "- GED is pending; every GED field is null.")]
    gaps = result["meta"].get("reference_run_gaps", [])
    if gaps:
        lines += ["", "## Missing stage files", ""]
        lines += [f"- {g}" for g in gaps]
    return "\n".join(lines) + "\n"


def reference_run_gaps(records: list) -> list:
    out = []
    for rec in records:
        if rec["arm"] != "frontier_end_ref":
            continue
        for m in rec.get("missing_files", []):
            fill = "filled from the fallback root" if m["filled_from_fallback"] else "not filled"
            out.append(f"{rec['run']} stage {m['stage']}: {m['file']} absent from the run dir ({fill}).")
        n = rec.get("n_stages_scored", 0)
        out.append(f"{rec['run']}: {n} stage(s) scored. Only the final stage exists in the off-host copy, "
                   "so the readouts before B are null.")
    return out


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="off-host copy of the campaign")
    ap.add_argument("--run-table", type=Path, default=HERE / "results_2026-10-31" / "run_table.csv")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--budget", action="append", metavar="SCENE=SECONDS",
                    help="override the budget B of a scene (repeatable)")
    ap.add_argument("--add-run", action="append", metavar="ARM=SCENE=PATH",
                    help="score one more run dir under an arm label (repeatable)")
    ap.add_argument("--no-default-runs", action="store_true", help="score only the --add-run runs")
    ap.add_argument("--apr", action="append", metavar="SCENE=PATH",
                    help="coverage-tour reference: a graph0 YAML or a tour run dir (repeatable)")
    ap.add_argument("--fallback-root", action="append", type=Path,
                    help="where to look for stage files missing from a run dir, as <root>/<run name>/stages/<n>/ "
                         f"(repeatable; default {DEFAULT_FALLBACK})")
    ap.add_argument("--no-fallback", action="store_true", help="read the run dirs only")
    ap.add_argument("--time-tol", type=float, default=TIME_TOL, help="seconds of slack when comparing times to t")
    ap.add_argument("--paper-html", type=Path, default=DEFAULT_PAPER_HTML)
    ap.add_argument("--ged-json", action="append", type=Path,
                    help="paper_ged.py output with the author's GED per stage (repeatable; later files win)")
    args = ap.parse_args(argv)
    GED_LOOKUP.clear()
    ged_rows = {str(p): load_ged_json(p) for p in (args.ged_json or [])}

    fallback = [] if args.no_fallback else (args.fallback_root or [DEFAULT_FALLBACK])
    fallback = [p for p in fallback if p.is_dir()]
    budgets = dict(DEFAULT_BUDGET)
    passed = {s: float(v) for s, v in _pairs(args.budget, "--budget").items()}
    budgets.update(passed)
    budget_sources = {s: ("--budget" if s in passed else
                          "default: end of the frontier-made reference run (section 4 fallback)")
                      for s in budgets}

    specs = [] if args.no_default_runs else default_runs(args.root, args.run_table)
    for item in args.add_run or []:
        parts = item.split("=", 2)
        if len(parts) != 3:
            sys.exit(f"--add-run: expected ARM=SCENE=PATH, got {item!r}")
        arm, scene, path = parts
        specs.append(RunSpec(Path(path).name, arm, scene, Path(path)))
    if not specs:
        sys.exit("no runs to score")
    no_budget = sorted({s.scene for s in specs} - set(budgets))
    if no_budget:
        sys.exit(f"no budget for scene(s) {no_budget}; pass --budget SCENE=SECONDS")

    refs = build_references(args.root, _pairs(args.apr, "--apr"))
    records = []
    for spec in specs:
        rec = score_run(spec, refs, budgets, fallback, args.time_tol)
        records.append(rec)
        print(f"{spec.name}: {rec.get('n_stages_scored', 0)} stages"
              + (f" ({rec['error']})" if "error" in rec else ""), file=sys.stderr)
    scored = [r for r in records if "error" not in r]

    meta = {
        "argv": sys.argv[1:] if argv is None else list(argv),
        "budgets": budgets,
        "budget_note": "a default B is the end of the frontier-made reference run (PREREGISTRATION_PAPER.md "
                       "section 4 fallback); a B passed with --budget comes from the caller (see budget_sources)",
        "budget_sources": budget_sources,
        "fractions": [f for f, _ in FRACTIONS], "variants": dict(VARIANTS), "primary_variant": PRIMARY,
        "time_tol_s": args.time_tol, "threshold_m": THRESHOLD,
        "fallback_roots": [str(p) for p in fallback],
        "references": {name: {"scenes": {s: {"path": r["path"], "n_objects": len(r["objects"])}
                                         for s, r in by_scene.items()},
                              **({"biased_toward_frontier": True} if name == "frontier_made" else {})}
                       for name, by_scene in refs.items()},
        "paper_fig4_left": PAPER,
        "paper_html_check": check_paper_table(args.paper_html),
        "reference_run_gaps": reference_run_gaps(records),
        "f1_scale_note": "per-run f1 is in [0, 1]; cell fields ending x100 are F1 x 100",
        "ged_sources": ged_rows,
        "ged_method": "author ged_score_plot.CustomGED(1,1,1,1) via gmatch4py, computed on the host by paper_ged.py" if ged_rows else None,
    }
    result = {"meta": meta, "runs": records, "cells": aggregate(scored),
              "seconds_per_metre": seconds_per_metre(scored)}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "paper_compare.json").write_text(json.dumps(result, indent=1) + "\n")
    (args.out_dir / "paper_compare.md").write_text(build_markdown(result))
    print(f"wrote {args.out_dir / 'paper_compare.json'} and paper_compare.md", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
