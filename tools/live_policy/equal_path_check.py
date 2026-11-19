#!/usr/bin/env python3
"""Exploratory: the paper-scale F1 read at equal path length, and at other time budgets.

Written on 2026-11-18, extended on 2026-11-19, both after the November results were seen. It is not a
registered readout (PREREGISTRATION_PAPER.md section 4 reads at fractions of one time budget), it enters
no table of paper_compare.md and no slide, and it decides nothing. It reads the per-stage scores that
paper_compare.py already wrote, and scores nothing itself:
    .venv_offline/bin/python tools/live_policy/equal_path_check.py
One run writes two things under results_paper_compare_1113/:

1. equal_path/equal_path.{json,md}. For scenes 00853 and 00871, object F1 x 100 at L metres of path.
   Rule, the path analogue of section 4: a run's value at L is its stage value at the last stage whose
   path length is at most L; a run whose last stage lies short of L has no value at L.
2. budget_sensitivity/budget_sensitivity.{json,md}. F1 x 100 at 10%, 50% and 100% of several budgets B,
   read by paper_compare.readout, the function that reads the registered cells. At the registered B
   the cells must equal the registered cells of paper_compare.json, or the script stops with an error.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paper_compare as pc  # noqa: E402

RESULTS = HERE / "results_paper_compare_1113"
ARMS = ("official", "official_nov", "filter_only", "placebo", "frontier_60m", "frontier_end")  # the 11-18 table
REFS = ("apr", "hm3d", "frontier_made")
LENGTHS = (20, 30, 40, 50, 55, 60, 70, 80, 90, 100)
SCENE_LENGTHS = {"00853": LENGTHS, "00871": LENGTHS + (120, 150, 190)}
SCENE_BUDGETS = {"00853": (500, 550, 600, 632.1751, 650, 700, 750),
                 "00871": (600, 650, 700, 750, 800, 900, 1000, 1100, 1200, 1300.25)}
BANNER = ("**Not a registered readout.** Written on 2026-11-19, after the results were seen. It is on no registered table. "
          "See `DEVIATIONS_NOVEMBER.md`.")
PATH_RULE = "last stage with path <= L; no value past the run's last stage"
BUDGET_RULE = ("stage value at the last stage with navigation time <= t (paper_compare.readout); a run that ended before t "
               "has no value at t; t = 10%, 50%, 100% of B")


# --------------------------------------------------------------------------
# Shared
# --------------------------------------------------------------------------

def scored_runs(pc_json: dict, scene: str, arm: str) -> list:
    return [r for r in pc_json["runs"] if r["scene"] == scene and r["arm"] == arm and "error" not in r]


def scene_arms(pc_json: dict, scene: str) -> list:
    """Every arm with a scored run in the scene, in paper_compare.py's order."""
    return sorted({r["arm"] for r in pc_json["runs"] if r["scene"] == scene and "error" not in r}, key=pc._arm_key)


def cell(vals: list, n_runs: int) -> dict:
    """F1 x 100 over the runs that have a value. Same arithmetic as the registered cells (statistics.mean)."""
    s = pc.summarise([None if v is None else 100.0 * v for v in vals])
    s["n_runs"] = n_runs
    return s


def path_cell(vals: list, n_runs: int) -> dict:
    """The same for the equal-path tables, with the arithmetic of the 2026-11-18 script (100 * sum / n), so no old cell moves.
    It can differ from `cell` in the last bit of a mean."""
    vals = [v for v in vals if v is not None]
    return {"mean": 100 * sum(vals) / len(vals), "min": 100 * min(vals), "max": 100 * max(vals), "n": len(vals), "n_runs": n_runs} if vals \
        else {"mean": None, "min": None, "max": None, "n": 0, "n_runs": n_runs}


def fmt(c: dict) -> str:
    if not c["n"]:
        return "-"
    return f"{c['mean']:.1f} [{c['min']:.1f}-{c['max']:.1f}] n={c['n']}" + ("" if c["n"] == c["n_runs"] else f" of {c['n_runs']}")


def key_of(x: float) -> str:
    return f"{x:.4f}".rstrip("0").rstrip(".")


# --------------------------------------------------------------------------
# 1. Equal path
# --------------------------------------------------------------------------

def value_at(stages: list, length_m: float, reference: str):
    """F1 at the last stage with path <= length_m; None if the run ends short of it or holds no such stage."""
    scored = [s for s in stages if reference in s.get("scores", {})]
    if not scored or max(s["path_m"] for s in scored) < length_m:
        return None
    at = [s for s in scored if s["path_m"] <= length_m]
    return at[-1]["scores"][reference]["f1"] if at else None


def table(pc_json: dict, scene: str, reference: str, arms=ARMS, lengths=LENGTHS) -> dict:
    out = {}
    for arm in arms:
        runs = scored_runs(pc_json, scene, arm)
        out[arm] = {str(length): path_cell([value_at(r["stages"], length, reference) for r in runs], len(runs)) for length in lengths}
    return out


def sec_per_m(pc_json: dict, scene: str) -> dict:
    """Mean navigation seconds per metre of each arm, as paper_compare.json files it under seconds_per_metre."""
    return {r["arm"]: r["sec_per_m"] | {"n_runs": r["n_runs"]} for r in pc_json.get("seconds_per_metre", []) if r["scene"] == scene}


def equal_path_md(tables: dict, scene: str, lengths, spm: dict) -> str:
    L = [f"## Scene {scene}", ""]
    for ref, t in tables.items():
        L += [f"### Reference: {ref}", "", "| Arm | " + " | ".join(f"{x} m" for x in lengths) + " |", "|---|" + "---|" * len(lengths)]
        L += [f"| {arm} | " + " | ".join(fmt(row[str(x)]) for x in lengths) + " |" for arm, row in t.items()]
        L.append("")
    if spm:
        L += ["### Seconds of navigation time per metre", ""]
        for arm in next(iter(tables.values())):
            s = spm.get(arm)
            if s and s["n"]:
                L.append(f"- {arm}: {s['mean']:.2f} s/m [{s['min']:.2f}-{s['max']:.2f}], n={s['n']}")
        L.append("")
    return "\n".join(L)


def equal_path_doc(pc_json: dict) -> tuple:
    scenes, md = {}, ["# F1 at equal path length (exploratory)", "", BANNER, "",
                      "It reads the per-stage scores of `paper_compare.json` at the last stage whose path is at most L metres; "
                      "a run that ends short of L has no value there. Object F1 x 100, mean [min-max] and n (\"n=k of m\" when "
                      "some of the m runs have no value). `-` means no run has a value.", ""]
    for scene, lengths in SCENE_LENGTHS.items():
        arms = scene_arms(pc_json, scene)
        tables = {ref: table(pc_json, scene, ref, arms, lengths) for ref in REFS}
        spm = sec_per_m(pc_json, scene)
        scenes[scene] = {"lengths": list(lengths), "arms": arms, "tables": tables, "sec_per_m": spm}
        md.append(equal_path_md(tables, scene, lengths, spm))
    doc = {"registered": False, "banner": BANNER, "rule": PATH_RULE, "scenes": scenes}
    return doc, "\n".join(md)


# --------------------------------------------------------------------------
# 2. Budget sensitivity
# --------------------------------------------------------------------------

def run_stages(run: dict) -> tuple:
    """A run's stages as paper_compare.readout wants them: it reads `graphs` (complete_end_s counts them) and `ged`,
    and the JSON keeps n_graphs and drops ged."""
    stages = [{**s, "graphs": dict.fromkeys(range(s["n_graphs"])), "scores": {r: {**sc, "ged": None} for r, sc in s["scores"].items()}}
              for s in run["stages"]]
    return stages, (pc.complete_end_s(stages) if run["arm"] == pc.NOV_ARM else None)


def budget_table(pc_json: dict, scene: str, reference: str, arms: list, budgets: dict) -> dict:
    """budgets maps a label to the seconds to read at. Returns {arm: {label: {"10"|"50"|"100": cell}}}."""
    tol = pc_json["meta"]["time_tol_s"]
    out = {}
    for arm in arms:
        runs = [run_stages(r) for r in scored_runs(pc_json, scene, arm)]
        out[arm] = {}
        for label, b in budgets.items():
            out[arm][label] = {fl: cell([pc.readout(st, reference, b * frac, tol, end_s)["f1"] for st, end_s in runs], len(runs))
                               for fl, frac in pc.FRACTIONS}
    return out


def registered_label(pc_json: dict, scene: str) -> str:
    """The label of the listed B that is the registered one (the listed value is rounded)."""
    exact = pc_json["meta"]["budgets"][scene]
    return next(key_of(b) for b in SCENE_BUDGETS[scene] if abs(b - exact) < 0.01)


def read_budgets(pc_json: dict, scene: str) -> dict:
    """label -> seconds. The registered B is read at paper_compare.json's exact value, not at the rounded one in its label."""
    exact = pc_json["meta"]["budgets"][scene]
    return {key_of(b): (exact if abs(b - exact) < 0.01 else float(b)) for b in SCENE_BUDGETS[scene]}


def registered_mismatches(pc_json: dict, scene: str, tables: dict, reg_label: str) -> list:
    """Compare our cells at the registered B with the `cells` of paper_compare.json (variant B). Returns the differences."""
    reg = {(c["arm"], c["reference"], c["fraction"]): c for c in pc_json["cells"] if c["scene"] == scene and c["variant"] == pc.PRIMARY}
    diffs, seen = [], 0
    for ref, t in tables.items():
        for arm, by_b in t.items():
            for fl, mine in by_b[reg_label].items():
                c = reg.get((arm, ref, fl))
                seen += 1
                theirs = None if c is None else {**c["stage_value_x100"], "n_runs": c["n_runs"]}
                if theirs != mine:
                    diffs.append(f"{scene} {arm} {ref} {fl}%: here {mine}, registered {theirs}")
    if seen != len(reg):
        diffs.append(f"{scene}: {seen} cells here, {len(reg)} registered")
    return diffs


def budget_doc(pc_json: dict) -> tuple:
    scenes, md = {}, ["# F1 at other time budgets (exploratory)", "", BANNER, "",
                      "Object F1 x 100 at 10%, 50% and 100% of a budget B, read as `paper_compare.py` reads the registered cells: "
                      "the stage value at the last stage whose navigation time is at most t; a run that ended before t has no value; "
                      "n counts the runs with a value (\"n=k of m\" when some of the m runs have none). Cells are mean [min-max] n. "
                      "The paper columns are Fig. 4 (left) of arXiv 2510.05430v2, for the arms whose paper method is Frontier or "
                      "Ours(ASP); `-` elsewhere. The B marked registered is read at the exact registered second and equals the "
                      "registered cell of `paper_compare.json`; the script stops if it does not.", ""]
    for scene in SCENE_BUDGETS:
        arms, budgets = scene_arms(pc_json, scene), read_budgets(pc_json, scene)
        reg_label = registered_label(pc_json, scene)
        tables = {ref: budget_table(pc_json, scene, ref, arms, budgets) for ref in REFS}
        diffs = registered_mismatches(pc_json, scene, tables, reg_label)
        if diffs:
            raise ValueError(f"cells at the registered B of {scene} differ from paper_compare.json:\n" + "\n".join(diffs[:10]))
        scenes[scene] = {"budgets_s": budgets, "registered_B_label": reg_label, "registered_B_s": pc_json["meta"]["budgets"][scene],
                         "arms": arms, "tables": tables, "paper_fig4_f1_x100": {m: list(v["f1"]) for m, v in pc.PAPER[scene].items()}}
        md.append(f"## Scene {scene}\n")
        for ref, t in tables.items():
            md += [f"### Reference: {ref}", "",
                   "| Arm | Paper method | B s | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |", "|---|---|---|---|---|---|---|---|---|"]
            for arm in arms:
                method = pc.paper_method(arm)
                paper = pc.PAPER[scene][method]["f1"] if method else None
                for label in budgets:
                    parts = [arm, pc.PAPER_LABELS[method] if method else "-", label + (" (registered)" if label == reg_label else "")]
                    for i, (fl, _) in enumerate(pc.FRACTIONS):
                        parts += [fmt(t[arm][label][fl]), f"{paper[i]:.1f}" if paper else "-"]
                    md.append("| " + " | ".join(parts) + " |")
            md.append("")
    doc = {"registered": False, "banner": BANNER, "rule": BUDGET_RULE, "scenes": scenes}
    return doc, "\n".join(md)


# --------------------------------------------------------------------------

def write(folder: str, doc: dict, md: str) -> None:
    out = RESULTS / folder
    out.mkdir(exist_ok=True)
    (out / f"{folder}.json").write_text(json.dumps(doc, indent=1) + "\n")
    (out / f"{folder}.md").write_text(md)
    print(f"wrote {out / (folder + '.json')} and {folder}.md")


def main() -> int:
    pc_json = json.loads((RESULTS / "paper_compare.json").read_text())
    try:
        budget = budget_doc(pc_json)
    except ValueError as e:
        sys.exit(f"error: {e}")
    write("equal_path", *equal_path_doc(pc_json))
    write("budget_sensitivity", *budget)
    return 0


if __name__ == "__main__":
    sys.exit(main())
