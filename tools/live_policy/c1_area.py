"""The C1 area table: several measures of each house's area beside the paper's figure.

C1 (PREREGISTRATION_PAPER.md §3) compares the navmesh area of the start floor with the area
the paper prints for the scene, and the two are far apart. This script adds measures taken
from the HM3D semantic mesh, so the gap can be read. It is descriptive: the measures below
were added on 11-13, after C1's result was known (DEVIATIONS_NOVEMBER.md, item 59).

Inputs, all in the repository:
- semantic/truth/<scene>_region_footprints.npz: per region, a mask of floor triangles and a
  mask of all labelled geometry, on a 0.05 m grid seen from above;
- results_paper_compare_1112/c_checks.json: the navmesh island of the start, the waypoint
  grid's area and the paper's figure.

Usage:
    python tools/live_policy/c1_area.py --out tools/live_policy/results_paper_compare_1113
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

HERE = Path(__file__).resolve().parent
TRUTH = HERE / "semantic" / "truth"
C_CHECKS = HERE / "results_paper_compare_1112" / "c_checks.json"
SCENES = ("00853", "00871")


def mask_area(mask: np.ndarray, cell: float) -> float:
    """Area of the true cells of a 2-D mask, in square metres."""
    return float(np.count_nonzero(mask)) * cell * cell


def hull_area(mask: np.ndarray, cell: float) -> float:
    """Area of the convex hull of the true cells, corners included; 0 for an empty mask."""
    rows, cols = np.nonzero(mask)
    if rows.size == 0:
        return 0.0
    # A cell covers [i, i+1] x [j, j+1]: take its four corners, so one cell has area cell**2.
    corners = np.concatenate([np.c_[cols + dx, rows + dy] for dx in (0, 1) for dy in (0, 1)])
    return float(ConvexHull(corners).volume) * cell * cell


def box_area(mask: np.ndarray, cell: float) -> float:
    """Area of the smallest box, along the grid's axes, that holds the true cells."""
    rows, cols = np.nonzero(mask)
    if rows.size == 0:
        return 0.0
    return float((rows.max() - rows.min() + 1) * (cols.max() - cols.min() + 1)) * cell * cell


def scene_areas(footprints: Path) -> dict:
    """The mesh-based measures for one scene."""
    z = np.load(footprints, allow_pickle=True)
    cell = float(z["cell_size"])
    floor = z["floor_masks"].any(axis=0)
    anything = z["any_masks"].any(axis=0)
    return {
        "cell_size_m": cell,
        "n_regions": int(len(z["region_ids"])),
        "labelled_floor_m2": mask_area(floor, cell),
        "labelled_footprint_m2": mask_area(anything, cell),
        "floor_hull_m2": hull_area(floor, cell),
        "footprint_hull_m2": hull_area(anything, cell),
        "footprint_box_m2": box_area(anything, cell),
    }


def c_check_areas(c_checks: Path, scene: str) -> dict:
    """The navmesh island, the waypoint grid's area and the paper's figure, as C1 filed them."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            if "paper_area_m2" in node and "start_island_area_m2" in node:
                found.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    data = json.loads(c_checks.read_text())
    walk(data.get(scene, data.get(str(int(scene)), data)) if isinstance(data, dict) else data)
    if len(found) != 1:
        raise ValueError(f"expected one C1 record for scene {scene}, found {len(found)}")
    rec = found[0]
    return {
        "navmesh_start_island_m2": float(rec["start_island_area_m2"]),
        "waypoint_grid_m2": float(rec["kept_area_estimate_m2"]),
        "paper_m2": float(rec["paper_area_m2"]),
    }


ROWS = (
    ("navmesh_start_island_m2", "Navmesh island that holds the start (walkable floor)"),
    ("labelled_floor_m2", "HM3D labelled floor (all regions' floor triangles)"),
    ("labelled_footprint_m2", "Footprint of all labelled geometry, seen from above"),
    ("waypoint_grid_m2", "Waypoint grid of the tour (cells kept times cell area)"),
    ("floor_hull_m2", "Convex hull of the labelled floor"),
    ("footprint_hull_m2", "Convex hull of all labelled geometry"),
    ("footprint_box_m2", "Box around all labelled geometry, along the mesh axes"),
    ("paper_m2", "The paper's figure"),
)


def table_md(result: dict) -> str:
    lines = ["| Measure, m² | " + " | ".join(SCENES) + " |", "|---|" + "---|" * len(SCENES)]
    for key, label in ROWS:
        lines.append(f"| {label} | " + " | ".join(f"{result[s][key]:.1f}" for s in SCENES) + " |")
    lines.append("| Paper's figure over the navmesh island | "
                 + " | ".join(f"{result[s]['paper_m2'] / result[s]['navmesh_start_island_m2']:.2f}" for s in SCENES) + " |")
    lines.append("| Paper's figure over the hull of all labelled geometry | "
                 + " | ".join(f"{result[s]['paper_m2'] / result[s]['footprint_hull_m2']:.2f}" for s in SCENES) + " |")
    def ratios(key):
        return " and ".join(f"{result[s]['paper_m2'] / result[s][key]:.1f}" for s in SCENES)

    hull = " and ".join(f"{result[s]['paper_m2'] / result[s]['footprint_hull_m2']:.2f}" for s in SCENES)
    reading = (
        "\nReading. No measure of floor comes near the paper's figure. It is "
        f"{ratios('navmesh_start_island_m2')} times the navmesh island that holds the start, and "
        f"{ratios('labelled_floor_m2')} times the labelled floor. It lies close to the convex hull of all "
        f"labelled geometry ({hull} of it). We do not know how the paper measured area; the area of the "
        "house's outline, with walls and furniture, would fit these figures. Both houses have one level.\n"
        "\nDescriptive. C1 as registered compares the navmesh island with the paper's figure; the other "
        "rows were added on 11-13, after C1's result was known (DEVIATIONS_NOVEMBER.md, item 59). Built by "
        "`tools/live_policy/c1_area.py` from `semantic/truth/` and `results_paper_compare_1112/c_checks.json`.\n"
    )
    return "\n".join(lines) + "\n" + reading


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--truth", type=Path, default=TRUTH)
    ap.add_argument("--c-checks", type=Path, default=C_CHECKS)
    args = ap.parse_args()
    result = {}
    for scene in SCENES:
        result[scene] = {**c_check_areas(args.c_checks, scene),
                         **scene_areas(args.truth / f"{scene}_region_footprints.npz")}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "c1_area_table.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.out / "c1_area_table.md").write_text(table_md(result))
    print(table_md(result))


if __name__ == "__main__":
    main()
