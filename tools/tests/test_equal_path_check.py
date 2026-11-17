"""Tests for the exploratory equal-path readout (tools/live_policy/equal_path_check.py)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "live_policy"))
import equal_path_check as ep  # noqa: E402


def stages(*pairs):
    return [{"stage": i, "path_m": p, "time_s": 6.0 * p, "scores": {"apr": {"f1": f}}} for i, (p, f) in enumerate(pairs)]


def test_value_is_read_at_the_last_stage_at_or_under_the_length():
    st = stages((0.0, 0.05), (20.0, 0.20), (48.0, 0.40), (61.0, 0.55))
    assert ep.value_at(st, 50, "apr") == 0.40
    assert ep.value_at(st, 48, "apr") == 0.40
    assert ep.value_at(st, 61, "apr") == 0.55
    assert ep.value_at(st, 10, "apr") == 0.05


def test_a_run_that_ends_short_has_no_value_and_a_missing_reference_gives_none():
    st = stages((0.0, 0.05), (20.0, 0.20), (48.0, 0.40))
    assert ep.value_at(st, 50, "apr") is None
    assert ep.value_at(st, 40, "hm3d") is None
    assert ep.value_at([], 10, "apr") is None


def test_table_gives_mean_range_and_n_over_the_runs_that_reach_the_length():
    pcj = {"runs": [{"scene": "00853", "arm": "official_nov", "stages": stages((0.0, 0.0), (50.0, 0.40), (100.0, 0.60))},
                    {"scene": "00853", "arm": "official_nov", "stages": stages((0.0, 0.0), (55.0, 0.50))},
                    {"scene": "00871", "arm": "official_nov", "stages": stages((0.0, 0.0), (55.0, 0.90))},
                    {"scene": "00853", "arm": "frontier_end", "stages": stages((0.0, 0.0), (60.0, 0.45))}]}
    t = ep.table(pcj, "00853", "apr", arms=("official_nov", "frontier_end"), lengths=(55, 100))
    assert t["official_nov"]["55"] == {"mean": pytest.approx(45.0), "min": pytest.approx(40.0), "max": pytest.approx(50.0), "n": 2, "n_runs": 2}
    assert t["official_nov"]["100"]["n"] == 1 and t["official_nov"]["100"]["mean"] == pytest.approx(60.0)
    assert t["frontier_end"]["55"]["mean"] == pytest.approx(0.0) and t["frontier_end"]["100"] == {"mean": None, "min": None, "max": None, "n": 0, "n_runs": 1}
    md = ep.to_md({"apr": t}, "00853", lengths=(55, 100))
    assert "Not a registered readout" in md and "| official_nov | 45.0 [40.0-50.0] n=2 | 60.0 [60.0-60.0] n=1 of 2 |" in md
