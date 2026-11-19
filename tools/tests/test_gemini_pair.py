"""gemini_pair.py: the exploratory contrast between two models scored by the wrapper."""
import json
import sys
from pathlib import Path

import pytest

LP = Path(__file__).resolve().parents[1] / "live_policy"
sys.path.insert(0, str(LP))
import gemini_pair as gp  # noqa: E402

RES = LP / "results_semantic_1113"


def records(path, rows):
    """rows: {row_id: (cluster, [member L2 scores or None])}"""
    recs = [{"row_id": r, "cluster": c, "model": {str(k): {"L1": None, "L2": v, "L3": None} for k, v in enumerate(vals)}}
            for r, (c, vals) in rows.items()]
    path.write_text(json.dumps({"records": recs}))
    return str(path)


def test_row_then_cluster_means_on_shared_rows_only(tmp_path):
    a = gp.row_scores(records(tmp_path / "a.json", {"r1": ("c1", [1.0, 0.5]), "r2": ("c1", [0.5, None]), "r3": ("c2", [0.2, 0.4]),
                                                    "r4": ("c3", [1.0, 1.0])}))
    b = gp.row_scores(records(tmp_path / "b.json", {"r1": ("c1", [0.5, 0.5]), "r2": ("c1", [None, None]), "r3": ("c2", [0.1, 0.1])}))
    t = gp.contrast(a, b, "L2")
    assert t["clusters"] == 2 and t["rows"] == 2            # r2 has no score in b, r4 is not in b
    assert t["a"] == pytest.approx((0.75 + 0.3) / 2) and t["b"] == pytest.approx((0.5 + 0.1) / 2)
    assert t["diff"] == pytest.approx(((0.75 - 0.5) + (0.3 - 0.1)) / 2)
    assert t["p_two_sided"] == pytest.approx(0.5)          # two clusters, both positive: 2 of 4 patterns are as far out
    assert gp.contrast(a, b, "L3")["clusters"] == 0 and gp.contrast(a, b, "L3")["diff"] is None


@pytest.mark.skipif(not (RES / "gemini_1119" / "records_gemini-3.8-flash.json").is_file(), reason="filed records absent")
def test_it_reproduces_the_wrappers_registered_differences():
    a = gp.row_scores(RES / "gemini_1119" / "records_gemini-3.8-flash.json")
    b = gp.row_scores(RES / "claude" / "records_claude-opus-5-5.json")
    l2, l3 = gp.contrast(a, b, "L2"), gp.contrast(a, b, "L3")
    assert l2["clusters"] == 12 and l2["rows"] == 36
    assert round(100 * l2["diff"], 1) == 21.0 and round(100 * l3["diff"], 1) == 2.7
    assert [round(100 * x, 1) for x in l2["interval"]] == [13.5, 28.8]
