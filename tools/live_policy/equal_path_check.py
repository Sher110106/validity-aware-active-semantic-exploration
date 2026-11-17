#!/usr/bin/env python3
"""Exploratory: the paper-scale F1 read at equal path length instead of equal time.

Written on 2026-11-18, after the November results were seen, because a review pointed out that ASP's
clock and frontier's clock run at different speeds per metre on 00853. It is not a registered readout
(PREREGISTRATION_PAPER.md section 4 reads at fractions of a time budget), it enters no table of
paper_compare.md and no slide, and it decides nothing. It only answers: how much of a gap at equal
time is left at equal distance?

It reads the per-stage scores that paper_compare.py already wrote, and scores nothing itself:
    .venv_offline/bin/python tools/live_policy/equal_path_check.py
writes results_paper_compare_1113/equal_path/equal_path.{json,md}.

Rule, the path analogue of section 4: a run's value at L metres is its stage value at the last stage
whose path length is at most L; a run whose last stage lies short of L has no value at L.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results_paper_compare_1113"
ARMS = ("official", "official_nov", "filter_only", "placebo", "frontier_60m", "frontier_end")
LENGTHS = (20, 30, 40, 50, 55, 60, 70, 80, 90, 100)


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
        runs = [r for r in pc_json["runs"] if r["scene"] == scene and r["arm"] == arm]
        row = {}
        for length in lengths:
            vals = [v for v in (value_at(r["stages"], length, reference) for r in runs) if v is not None]
            row[str(length)] = ({"mean": 100 * sum(vals) / len(vals), "min": 100 * min(vals), "max": 100 * max(vals), "n": len(vals)}
                                if vals else {"mean": None, "min": None, "max": None, "n": 0})
            row[str(length)]["n_runs"] = len(runs)
        out[arm] = row
    return out


def to_md(tables: dict, scene: str, lengths=LENGTHS) -> str:
    L = [f"# F1 at equal path length, scene {scene} (exploratory)", "",
         "**Not a registered readout.** Written on 2026-11-18, after the results were seen (`DEVIATIONS_NOVEMBER.md`, item 66). "
         "It is in no table of `paper_compare.md` and on no slide. It reads the per-stage scores of `paper_compare.json` at the last "
         "stage whose path is at most L metres; a run that ends short of L has no value there. Object F1 x 100, mean [min-max] and n.", ""]
    for ref, t in tables.items():
        L += [f"## Reference: {ref}", "", "| Arm | " + " | ".join(f"{x} m" for x in lengths) + " |", "|---|" + "---|" * len(lengths)]
        for arm, row in t.items():
            cells = []
            for x in lengths:
                c = row[str(x)]
                cells.append("-" if not c["n"] else f"{c['mean']:.1f} [{c['min']:.1f}-{c['max']:.1f}] n={c['n']}"
                             + ("" if c["n"] == c["n_runs"] else f" of {c['n_runs']}"))
            L.append(f"| {arm} | " + " | ".join(cells) + " |")
        L.append("")
    return "\n".join(L)


def main() -> int:
    pc_json = json.loads((RESULTS / "paper_compare.json").read_text())
    scene = "00853"
    tables = {ref: table(pc_json, scene, ref) for ref in ("apr", "hm3d", "frontier_made")}
    out = RESULTS / "equal_path"
    out.mkdir(exist_ok=True)
    (out / "equal_path.json").write_text(json.dumps({"scene": scene, "rule": "last stage with path <= L; no value past the run's last stage",
                                                    "registered": False, "tables": tables}, indent=1) + "\n")
    (out / "equal_path.md").write_text(to_md(tables, scene))
    print(to_md({"apr": tables["apr"]}, scene))
    return 0


if __name__ == "__main__":
    sys.exit(main())
