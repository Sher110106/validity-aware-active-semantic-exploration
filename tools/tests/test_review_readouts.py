"""Tests for tools/live_policy/review_readouts.py: small made-up inputs for each readout, plus one run on
the real saved files that pins a few values. The module loads by file path (tools/live_policy also holds a
live_policy.py that other tests import under that name)."""
import copy
import importlib.util
import json
import math
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
LIVE = os.path.abspath(os.path.join(HERE, "..", "live_policy"))
_spec = importlib.util.spec_from_file_location("review_readouts_under_test", os.path.join(LIVE, "review_readouts.py"))
rr = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = rr
_spec.loader.exec_module(rr)

LV = ("L1", "L2", "L3")


def sc(l1=None, l2=None, l3=None):
    return {"L1": l1, "L2": l2, "L3": l3}


def rec(row_id, cluster, model, comps=None, rnd=1, possible=(True, True, True), seed=42, arm="official"):
    return {"row_id": row_id, "cluster": cluster, "scene": "S", "seed": seed, "arm": arm, "stage": 1, "round": rnd,
            "is_gemini_row": False, "possible": dict(zip(LV, possible)), "n_unobserved": 3,
            "model": model, "comparators": comps or {}}


def saved_results(recs_by_model, rounds=(1,)):
    return {"rounds_used": list(rounds),
            "models": {m: {"analysis": rr.scorer().analyse([r for r in recs if r["round"] in rounds], m)}
                       for m, recs in recs_by_model.items()}}


# ---------------------------------------------------------------------------------------- 1. ceiling

def toy_ceiling_records():
    return [
        # cluster A: member 0 and 1; model 1.0 and 0.5, B3 1.0 and 1.0 -> row 0.75 vs 1.0
        rec("a1", "A", {"0": sc(l1=1.0), "1": sc(l1=0.5)},
            {"B3": {"0": sc(l1=1.0), "1": sc(l1=1.0)}, "B1": {"0": sc(l1=0.5), "1": sc(l1=0.5), "2": sc(l1=0.5)}}),
        # cluster B: model 1.0, B3 0.5
        rec("b1", "B", {"0": sc(l1=1.0)}, {"B3": {"0": sc(l1=0.5)}, "B1": {"0": sc(l1=1.0)}}),
        # cluster C: model 1.0, B3 1.0
        rec("c1", "C", {"0": sc(l1=1.0)}, {"B3": {"0": sc(l1=1.0)}, "B1": {"0": sc(l1=0.0)}}),
        # a row with no model score at L1 leaves L1
        rec("c2", "C", {"0": sc()}, {"B3": {"0": sc(l1=1.0)}}),
        # a row where nothing can hit leaves L1
        rec("c3", "C", {"0": sc(l1=0.0)}, {"B3": {"0": sc(l1=1.0)}}, possible=(False, True, True)),
        # a row in a round outside the analysis set
        rec("c4", "C", {"0": sc(l1=0.0)}, {"B3": {"0": sc(l1=1.0)}}, rnd=2),
    ]


def test_ceiling_small_values():
    recs = {"m": toy_ceiling_records()}
    doc = rr.ceiling(recs, saved_results(recs), rounds=[1])
    b3 = doc["models"]["m"]["L1"]["comparators"]["B3"]
    assert (b3["n_rows"], b3["n_clusters"]) == (3, 3)
    assert b3["model_score"] == pytest.approx((0.75 + 1 + 1) / 3)
    assert b3["comparator_score"] == pytest.approx((1 + 0.5 + 1) / 3)
    assert b3["mean_diff"] == pytest.approx(b3["model_score"] - b3["comparator_score"])
    assert (b3["comparator_rows_at_1"], b3["comparator_clusters_at_1"]) == (2, 2)
    assert b3["max_gain_perfect_model"] == pytest.approx(1 - 2.5 / 3)
    pm = b3["perfect_model"]  # d = [0, .5, 0]: 2 zero clusters of 3, so p = 2^2 / 2^3
    assert (pm["n_zero_clusters"], pm["p_min"], pm["p_min_holm6"], pm["can_reach_alpha"]) == (2, 0.5, 1.0, False)
    b1 = doc["models"]["m"]["L1"]["comparators"]["B1"]  # row-paired: the model's row score against the draws' mean
    assert b1["comparator_score"] == pytest.approx((0.5 + 1.0 + 0.0) / 3)
    assert "perfect_model" not in b1
    assert doc["models"]["m"]["L3"]["comparators"]["D"]["n_clusters"] == 0


def test_perfect_model_p_all_clusters_below_one():
    clusters = {c: 0.5 for c in "ABCDE"}
    pm = rr.perfect_model_p(clusters)
    assert pm["p_min"] == 1 / 32
    assert pm["p_min_holm6"] == pytest.approx(6 / 32)
    assert pm["can_reach_alpha"] is False
    clusters = {c: 0.5 for c in "ABCDEFGHIJ"}  # 10 clusters: 1/1024, after Holm 6/1024
    assert rr.perfect_model_p(clusters)["can_reach_alpha"] is True


def test_ceiling_fails_loudly_when_results_differ():
    recs = {"m": toy_ceiling_records()}
    res = saved_results(recs)
    bad = copy.deepcopy(res)
    bad["models"]["m"]["analysis"]["levels"]["L1"]["comparators"]["B3"]["mean_diff"] += 0.01
    with pytest.raises(rr.ReadoutCheckError):
        rr.ceiling(recs, bad, rounds=[1])
    bad = copy.deepcopy(res)
    bad["models"]["m"]["analysis"]["levels"]["L1"]["comparators"]["B3"]["n_rows"] += 1
    with pytest.raises(rr.ReadoutCheckError):
        rr.ceiling(recs, bad, rounds=[1])
    assert rr.ceiling(recs, res, rounds=[1])["readout"] == "ceiling"


# ------------------------------------------------------------------------------------ 2. common rows

def toy_sources():
    def row(rid, cluster, rnd, members, g=None):
        return rid, cluster, rnd, members

    def mk(scores, b3=None):
        # scores: {row_id: {member: (l1, l2, l3)}}
        out = []
        for (rid, cl, rnd) in (("r1", "X", 4), ("r2", "X", 4), ("r3", "Y", 4), ("r4", "Y", 1)):
            mem = {k: sc(*v) for k, v in scores.get(rid, {}).items()}
            comps = {"B3": {k: sc(*v) for k, v in (b3 or {}).get(rid, {}).items()}}
            out.append(rec(rid, cl, mem, comps, rnd=rnd))
        return out

    gem = mk({"r1": {"0": (1.0, 0.5, 0.2), "1": (1.0, 1.0, 0.0)}, "r2": {"0": (1.0, 0.8, 0.1)},
              "r3": {"0": (None, 1.0, 0.3)}},
             b3={"r1": {"0": (1.0, 0.9, None), "1": (1.0, 0.7, None)}, "r2": {"0": (1.0, 0.6, None)},
                 "r3": {"0": (1.0, 0.5, None)}})
    other = lambda a, b, c: mk({"r1": {"0": (1.0, a, c)}, "r2": {"0": (1.0, b, c)}, "r3": {"0": (1.0, 0.5, c)},
                                "r4": {"0": (1.0, 1.0, 1.0)}})
    return {"gemini": gem, "claude-opus-5-5": other(0.5, 0.8, 0.1), "claude-haiku-5-5": other(0.9, 0.2, 0.3),
            "deepseek": other(0.75, 0.8, 0.0), "placebo": other(0.0, 0.0, 0.0)}


def test_common_rows_small():
    doc = rr.common_rows(toy_sources())
    assert doc["anchor_rows"] == ["r1", "r2", "r3"]  # r4 holds no Gemini members
    l2 = doc["levels"]["L2"]
    assert l2["rows"] == ["r1", "r2", "r3"] and l2["n_rows"] == 3
    assert l2["mean_row_score"]["gemini"] == pytest.approx((0.75 + 0.8 + 1.0) / 3)
    assert l2["mean_row_score"]["placebo"] == pytest.approx((0 + 0 + 0.5) / 3)
    # Gemini rows 0.75, 0.8, 1.0 against opus 0.5, 0.8, 0.5: above, tie, above
    assert l2["anchor_vs"]["claude-opus-5-5"] == {"above": 2, "tie": 1, "below": 0}
    # haiku 0.9, 0.2, 0.5: below, above, above
    assert l2["anchor_vs"]["claude-haiku-5-5"] == {"above": 2, "tie": 0, "below": 1}
    assert l2["anchor_members"] == 4 and l2["n_clusters"] == 2
    # B3 paired with Gemini's members: r1 mean(.9,.7)=.8, r2 .6, r3 .5
    assert l2["b3_score_anchor_members"] == pytest.approx((0.8 + 0.6 + 0.5) / 3)
    l1 = doc["levels"]["L1"]  # Gemini has no L1 score on r3, so r3 leaves L1
    assert l1["rows"] == ["r1", "r2"] and l1["n_clusters"] == 1 and l1["anchor_members"] == 3
    assert l1["anchor_vs"]["deepseek"] == {"above": 0, "tie": 2, "below": 0}
    assert doc["levels"]["L3"]["b3_score_anchor_members"] is None  # B3 has no L3 score


def test_common_rows_drops_a_row_one_source_lacks():
    src = toy_sources()
    src["deepseek"][1]["model"] = {}  # r2: deepseek has no member
    doc = rr.common_rows(src)
    assert doc["levels"]["L2"]["rows"] == ["r1", "r3"]


# ---------------------------------------------------------------------------------- 3. room test

def run(name, scene, arm, of, predicted, seed=42):
    return {"run": name, "scene": scene, "seed": seed, "arm": arm, "n_regions_unseen_at_stage0": of,
            "predicted_stages_with_8_members_typed": list(range(predicted)),
            "predicted_all_stages_typed": list(range(predicted)), "n_stages": 10, "n_stages_with_8_members": 5}


def test_permutation_test_counts_and_p_by_hand():
    rows = rr.run_rows([run("o1", "S", "official", 4, 3), run("o2", "S", "official", 4, 3),
                        run("p1", "S", "placebo", 4, 0), run("p2", "S", "placebo", 4, 0)],
                       "predicted_stages_with_8_members_typed")
    t = rr.permutation_test(rows, "official", "placebo")
    # C(4,2) = 6 relabelings: both 3s official (+.75), both placebo (-.75), four mixed (0): 2 are as extreme
    assert t["relabelings"] == 6 and t["as_extreme"] == 2
    assert t["p_two_sided"] == pytest.approx(1 / 3) and t["observed_diff"] == pytest.approx(0.75)


def test_permutation_test_swaps_within_scene_only():
    runs = [run("o1", "S", "official", 4, 3), run("o2", "S", "official", 4, 3),
            run("p1", "S", "placebo", 4, 0), run("p2", "S", "placebo", 4, 0),
            run("o3", "T", "official", 2, 1), run("p3", "T", "placebo", 2, 1),
            run("f1", "T", "filter_only", 2, 0)]  # a third arm in the data is left alone
    rows = rr.run_rows(runs, "predicted_all_stages_typed")
    t = rr.permutation_test(rows, "official", "placebo")
    assert t["relabelings"] == 6 * 2  # C(4,2) in scene S, C(2,1) in scene T
    assert t["per_scene"]["S"]["relabelings"] == 6 and t["per_scene"]["T"]["relabelings"] == 2
    # a scene that holds only one arm cannot swap: one way
    t2 = rr.permutation_test(rr.run_rows([run("o1", "S", "official", 4, 3), run("p1", "S", "placebo", 4, 0),
                                          run("o2", "U", "official", 4, 1)], "predicted_all_stages_typed"), "official", "placebo")
    assert t2["relabelings"] == 2


def test_room_test_runs_pooled_and_tests():
    doc = {"live": {"runs": [run("o1", "S", "official", 4, 2), run("o2", "S", "official", 4, 0),
                             run("p1", "S", "placebo", 4, 1), run("p2", "S", "placebo", 4, 1),
                             run("f1", "S", "filter_only", 4, 0), run("f2", "S", "filter_only", 4, 1)]}}
    out = rr.room_test_runs(doc)
    v = out["views"]["eight_member_stages"]
    assert v["pooled"]["official"] == {"runs": 2, "predicted": 2, "of": 8, "rate": 0.25}
    assert v["pooled"]["placebo"]["rate"] == 0.25
    assert v["tests"]["official_vs_placebo"]["p_two_sided"] == 1.0  # equal rates, every relabeling at least as extreme
    assert v["tests"]["filter_only_vs_placebo"]["relabelings"] == 6
    assert out["fields"]["predicted before found, eight_member_stages"] == "predicted_stages_with_8_members_typed"


# ---------------------------------------------------------------------------------- 4. all true

def stage(run_name, stage_no, **arms):
    return {"run": run_name, "stage": stage_no, "arms": {a: {"ig": v} for a, v in arms.items()}}


def test_all_true_small():
    rows = [stage("r", 0, F0=[0, 0.5, 1, 2], F6=[0, 0.5, 1, 2], F1=[0, 1, 2.5, 3]),
            stage("r", 1, F0=[2, 1, 0.5, 0], F6=[0, 0.5, 1, 2], F1=[1, 1, 1, 4]),
            stage("r", 2, F0=[0, 0, 0, 0], F6=[0, 0.5, 1, 2], F1=[1, 2, 3, 4])]  # F0 constant: undefined
    out = rr.all_true(rows)
    assert out["arms"]["F1"]["max_ig"] == 4 and out["arms"]["F1"]["at"] == {"run": "r", "stage": 1, "candidate": 3}
    assert out["arms"]["F1"]["above_cap"] == 5  # 2.5, 3, 4, 3, 4
    assert out["arms"]["F0"]["max_ig"] == 2.0 and out["F0_exceeds_cap"] is False and out["F6_exceeds_cap"] is False
    sp = out["spearman"]
    assert sp["n_used"] == 2 and sp["n_undefined"] == 1 and sp["undefined_stages"] == [["r", 2]]
    assert sp["mean"] == pytest.approx(0.0)  # +1 and -1


def test_all_true_flags_an_arm_above_the_cap():
    rows = [stage("r", 0, F0=[0, 1, 2.5, 1], F6=[0, 1, 2, 1])]
    out = rr.all_true(rows)
    assert out["F0_exceeds_cap"] is True and out["F6_exceeds_cap"] is False
    assert rr.all_true(rows, bits_cap=3.0)["F0_exceeds_cap"] is False


# ---------------------------------------------------------------------------------- real files

REAL = os.path.join(LIVE, "results_semantic_1113", "claude", "records_claude-opus-5-5.json")
REAL_M2 = os.path.join(LIVE, "results_m2_1113", "pass1", "factorial_stages.jsonl")


@pytest.mark.skipif(not (os.path.exists(REAL) and os.path.exists(REAL_M2)), reason="saved result files absent")
def test_real_files_pin_values(tmp_path):
    res = rr.run_all(out_sem=tmp_path / "sem", out_m2=tmp_path / "m2")
    c = res["ceiling"]["models"]
    opus_b3 = c["claude-opus-5-5"]["L1"]["comparators"]["B3"]
    assert (opus_b3["n_rows"], opus_b3["n_clusters"]) == (41, 12)
    assert opus_b3["comparator_score"] == pytest.approx(0.9120, abs=5e-4)
    assert opus_b3["mean_diff"] == pytest.approx(-0.0576, abs=5e-4)  # RESULTS.md: -5.8 points
    assert c["claude-haiku-5-5"]["L1"]["comparators"]["B3"]["comparator_score"] == pytest.approx(1.0)
    assert c["claude-haiku-5-5"]["L1"]["comparators"]["B3"]["perfect_model"]["p_min"] == 1.0
    assert c["claude-opus-5-5"]["L2"]["comparators"]["B3"]["perfect_model"]["p_min"] == pytest.approx(2 ** 5 / 2 ** 12)
    assert c["claude-opus-5-5"]["L2"]["comparators"]["B3"]["perfect_model"]["p_min_holm6"] == pytest.approx(6 * 2 ** 5 / 2 ** 12)
    assert c["claude-haiku-5-5"]["L2"]["comparators"]["B3"]["perfect_model"]["can_reach_alpha"] is False

    cr = res["common_rows"]
    assert len(cr["anchor_rows"]) == 8 and cr["anchor_rounds"] == [4]
    assert cr["levels"]["L2"]["n_rows"] == 8 and cr["levels"]["L2"]["anchor_members"] == 29
    assert cr["levels"]["L3"]["n_clusters"] == 3

    rt = res["room_test_runs"]["views"]["eight_member_stages"]
    assert rt["pooled"]["official"]["predicted"] == 10 and rt["pooled"]["official"]["of"] == 59
    assert rt["pooled"]["placebo"]["predicted"] == 6 and rt["pooled"]["placebo"]["of"] == 69
    assert rt["tests"]["official_vs_placebo"]["relabelings"] == 200
    assert rt["tests"]["filter_only_vs_placebo"]["relabelings"] == 400
    assert rt["tests"]["official_vs_placebo"]["p_two_sided"] == pytest.approx(25 / 200)

    at = res["all_true"]
    assert at["arms"]["F0"]["max_ig"] == 2.0 and at["arms"]["F6"]["max_ig"] == 2.0
    assert at["F0_exceeds_cap"] is False and at["F6_exceeds_cap"] is False
    assert at["spearman"]["n_used"] == 382 and math.isfinite(at["spearman"]["mean"])

    names = {p.name for p in res["written"]}
    assert names == {"ceiling.md", "ceiling.json", "common_rows.md", "common_rows.json",
                     "room_test_runs.md", "room_test_runs.json", "all_true.md", "all_true.json"}
    for p in res["written"]:
        text = p.read_text()
        if p.suffix == ".md":
            assert text.startswith("> **Exploratory.**") and "2026-11-19" in text.splitlines()[0]
        else:
            assert "see DEVIATIONS_NOVEMBER.md" in json.loads(text)["banner"]
