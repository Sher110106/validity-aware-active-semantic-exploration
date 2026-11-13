"""Tests for the C1 area table (tools/live_policy/c1_area.py)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "live_policy"))
import c1_area  # noqa: E402


def test_mask_area_counts_cells():
    mask = np.zeros((10, 10), dtype=bool)
    mask[2:4, 3:8] = True  # 2 x 5 cells
    assert c1_area.mask_area(mask, 0.5) == pytest.approx(10 * 0.25)


def test_hull_of_one_cell_is_one_cell():
    mask = np.zeros((5, 5), dtype=bool)
    mask[2, 2] = True
    assert c1_area.hull_area(mask, 0.05) == pytest.approx(0.05 * 0.05)


def test_hull_fills_an_l_shape_and_box_holds_it():
    mask = np.zeros((20, 20), dtype=bool)
    mask[0:10, 0:2] = True   # upright bar, 10 x 2
    mask[8:10, 0:10] = True  # foot, 2 x 10
    cells = 10 * 2 + 2 * 10 - 2 * 2
    assert c1_area.mask_area(mask, 1.0) == cells
    hull = c1_area.hull_area(mask, 1.0)
    assert cells < hull < 100
    assert c1_area.box_area(mask, 1.0) == 100
    # The hull of a full rectangle is the rectangle.
    full = np.ones((4, 6), dtype=bool)
    assert c1_area.hull_area(full, 1.0) == pytest.approx(24)


def test_empty_mask_has_no_area():
    mask = np.zeros((4, 4), dtype=bool)
    assert c1_area.mask_area(mask, 1.0) == 0
    assert c1_area.hull_area(mask, 1.0) == 0
    assert c1_area.box_area(mask, 1.0) == 0


def test_scene_areas_take_the_union_over_regions(tmp_path):
    floor = np.zeros((2, 10, 10), dtype=bool)
    floor[0, 0:4, 0:4] = True
    floor[1, 2:6, 2:6] = True  # overlaps region 0 on a 2 x 2 patch
    anything = floor.copy()
    anything[1, 8:10, 8:10] = True
    path = tmp_path / "x_region_footprints.npz"
    np.savez(path, cell_size=np.array(1.0), region_ids=np.array([1, 2]), floor_masks=floor, any_masks=anything)
    got = c1_area.scene_areas(path)
    assert got["n_regions"] == 2
    assert got["labelled_floor_m2"] == 16 + 16 - 4
    assert got["labelled_footprint_m2"] == 28 + 4
    assert got["footprint_box_m2"] == 100
    assert got["floor_hull_m2"] >= got["labelled_floor_m2"]


def test_c_check_areas_reads_one_record_per_scene(tmp_path):
    path = tmp_path / "c_checks.json"
    path.write_text(json.dumps({
        "00853": {"C1": {"start_island_area_m2": 77.0, "kept_area_estimate_m2": 191.25, "paper_area_m2": 207.63}},
        "00871": {"C1": {"start_island_area_m2": 59.3, "kept_area_estimate_m2": 148.5, "paper_area_m2": 235.03}},
    }))
    got = c1_area.c_check_areas(path, "00871")
    assert got == {"navmesh_start_island_m2": 59.3, "waypoint_grid_m2": 148.5, "paper_m2": 235.03}


def test_c_check_areas_refuses_a_file_with_no_record(tmp_path):
    path = tmp_path / "c_checks.json"
    path.write_text(json.dumps({"00853": {"C2": {}}}))
    with pytest.raises(ValueError):
        c1_area.c_check_areas(path, "00853")


def test_real_files_give_the_filed_figures():
    out = {s: {**c1_area.c_check_areas(c1_area.C_CHECKS, s),
               **c1_area.scene_areas(c1_area.TRUTH / f"{s}_region_footprints.npz")} for s in c1_area.SCENES}
    assert out["00853"]["paper_m2"] == pytest.approx(207.63)
    assert out["00871"]["paper_m2"] == pytest.approx(235.03)
    assert out["00853"]["navmesh_start_island_m2"] == pytest.approx(77.0, abs=0.01)
    for s in c1_area.SCENES:
        r = out[s]
        assert r["navmesh_start_island_m2"] < r["labelled_floor_m2"] < r["labelled_footprint_m2"]
        assert r["labelled_footprint_m2"] < r["footprint_hull_m2"] < r["footprint_box_m2"]
    md = c1_area.table_md(out)
    table = [line for line in md.splitlines() if line.startswith("|")]
    assert len(table) == len(c1_area.ROWS) + 4
    assert "Reading." in md and "item 59" in md
