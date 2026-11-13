"""Write the part 3 values of slots.json from the result files, so every number has a file and a path.

Reads (all under tools/live_policy/):
  results_semantic_1113/claude/{results,room_test,validity}.json, claude/records_*.json
  results_semantic_1113/exploratory/{results,room_test,validity,mdd_table}.json, exploratory/error_sample_*.json
  results_semantic_1113/claude/error_sample_*.json
  results_semantic_1113/nohint_haiku/records_claude-haiku-5-5.json
  results_semantic_1113/independent_recompute/margin_summary.json
  results_m2_1113/pass2/summary_factorial.json
The part 2 keys (paper_compare_json, table871_updated, asp853_full_budget) and the outcome pick are kept as they are
unless the result files say otherwise. The outcome comes from results.json family.thesis.

Run from the project root:
    .venv_offline/bin/python docs/endsem_2026-11/fill_slots_part3.py
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
LP = os.path.join(PROJECT, "tools", "live_policy")
RS = os.path.join(LP, "results_semantic_1113")
M2 = os.path.join(LP, "results_m2_1113", "pass2")
SLOTS = os.path.join(HERE, "slots.json")

MODELS = {"opus": ("claude", "claude-opus-5-5"), "haiku": ("claude", "claude-haiku-5-5"),
          "deepseek": ("exploratory", "deepseek")}


def J(*parts):
    return json.load(open(os.path.join(*parts)))


def cluster_mean(d):
    v = list(d.values())
    return sum(v) / len(v)


def main():
    old = J(SLOTS)
    cl, ex = J(RS, "claude", "results.json"), J(RS, "exploratory", "results.json")
    res = {"claude": cl, "exploratory": ex}
    fam = {"claude": cl["family"]["hypotheses"], "exploratory": ex["models"]["deepseek"]["exploratory_family"]["hypotheses"]}
    wh = {"claude": cl["family"]["wrong_house_gate"],
          "exploratory": ex["models"]["deepseek"]["exploratory_family"]["wrong_house_gate"]}
    plc = ex["models"]["placebo"]["analysis"]["levels"]

    models = {}
    for key, (part, name) in MODELS.items():
        lv = res[part]["models"][name]["analysis"]["levels"]
        out = {}
        for L in ("L1", "L2", "L3"):
            h = fam[part][f"{name}|{L}"]
            named = lv[L]["comparators"][h["named"]]
            e = {"score": cluster_mean(lv[L]["model_cluster_scores"]), "named": h["named"],
                 "diff": named["mean_diff"], "lo": named["ci"][0], "hi": named["ci"][1],
                 "margin": h["delta"], "verdict": h["verdict"], "p_holm": h["p_holm"]}
            if L in ("L1", "L2"):
                b1 = lv[L]["comparators"]["B1"]
                e["placebo"] = {"diff": b1["mean_diff"], "lo": b1["ci"][0], "hi": b1["ci"][1], "p": b1["p"]}
            e["placebo_score"] = cluster_mean(plc[L]["model_cluster_scores"])
            out[L] = e
        models[key] = out

    mdd_t = J(RS, "exploratory", "mdd_table.json")["levels"]
    mdd = {L: {"mdd": mdd_t[L]["mdd"], "half_width": mdd_t[L]["half_width"], "margin": mdd_t[L]["delta"],
               "contrast": mdd_t[L]["contrast"], "n_clusters": mdd_t[L]["n_clusters"]} for L in mdd_t}

    wrong = {}
    for key, (part, name) in MODELS.items():
        wrong[key] = {L: {"mean_diff": wh[part][f"{name}|{L}"]["mean_diff"], "p": wh[part][f"{name}|{L}"]["p"],
                          "n_pairs": wh[part][f"{name}|{L}"]["n_pairs"], "pass": wh[part][f"{name}|{L}"]["pass"]}
                      for L in ("L1", "L2")}

    ms = J(RS, "independent_recompute", "margin_summary.json")["summary"]
    ks = ("claude-opus-5-5|200", "claude-opus-5-5|5000")
    opus_check = {"registered_upper": cl["family"]["hypotheses"]["claude-opus-5-5|L3"]["ci_upper_named"],
                  "margin": 0.03, "runs": sum(ms[k]["runs"] for k in ks),
                  "rerun_min": min(ms[k]["ci_high_min"] for k in ks), "rerun_max": max(ms[k]["ci_high_max"] for k in ks),
                  "below_margin": sum(ms[k]["below_0.03"] for k in ks)}

    # members: 4 per row, 44 rows, per model
    members = {}
    for key in ("opus", "haiku"):
        st = cl["models"][MODELS[key][1]]["status"]
        flat = [v for row in st.values() for v in row.values()]
        members[key] = {"members": len(flat), "parsed": sum(1 for v in flat if v == "ok")}

    # placement error samples
    def err(path, part, name):
        a = np.array(J(path), float)
        left = res[part]["models"][name]["error_sample_left_out"]
        assert res[part]["models"][name]["error_sample_n"] == len(a)
        return {"n": int(len(a)), "median": float(np.median(a)), "left_out": int(left),
                "all_guesses": int(len(a) + left)}
    placement = {"deepseek": err(os.path.join(RS, "exploratory", "error_sample_deepseek.json"), "exploratory", "deepseek"),
                 "gemini": err(os.path.join(RS, "exploratory", "error_sample_gemini.json"), "exploratory", "gemini"),
                 "haiku": err(os.path.join(RS, "claude", "error_sample_claude-haiku-5-5.json"), "claude",
                              "claude-haiku-5-5"),
                 "opus": err(os.path.join(RS, "claude", "error_sample_claude-opus-5-5.json"), "claude",
                             "claude-opus-5-5"),
                 "placebo": err(os.path.join(RS, "exploratory", "error_sample_placebo.json"), "exploratory",
                                "placebo")}

    # room test
    rt = J(RS, "claude", "room_test.json")
    assert rt["live"]["by_arm"] == J(RS, "exploratory", "room_test.json")["live"]["by_arm"]
    arms = rt["live"]["by_arm"]["arms"]
    live = {}
    for a, k in (("llm", "official"), ("filter", "filter_only"), ("placebo", "placebo")):
        d = arms[k]
        live[a] = {"of": d["of"], "typed_all": d["predicted_all_stages_typed"],
                   "untyped_all": d["predicted_all_stages_untyped"],
                   "typed_8": d["predicted_stages_with_8_members_typed"],
                   "untyped_8": d["predicted_stages_with_8_members_untyped"],
                   "runs": d["runs"], "stages_8": d["stages_with_8_members"]}
    paper = rt["live"]["by_arm"]["paper"]
    ex_rt = J(RS, "exploratory", "room_test.json")["replay"]
    rep = {}
    for key, src in (("opus", rt["replay"]["claude-opus-5-5"]), ("haiku", rt["replay"]["claude-haiku-5-5"]),
                     ("deepseek", ex_rt["deepseek"]), ("placebo", ex_rt["placebo"])):
        t = src["totals"]
        rep[key] = {"of": t["of"], "t1": t["predicted_1of4_typed"], "t2": t["predicted_2of4_typed"],
                    "u1": t["predicted_1of4_untyped"], "u2": t["predicted_2of4_untyped"]}
    room = {"live": live, "paper": {"hit": paper["predicted"], "of": paper["of"]}, "replay": rep}

    # prompt hint, round-1 rows
    def pool(recs, rnd):
        t = {"l1_n": 0, "l1_hits": 0, "l2_n": 0, "l2_hits": 0, "l3_n": 0, "l3_hits": 0.0, "rows": 0}
        for r in recs:
            if r["round"] != rnd:
                continue
            t["rows"] += 1
            for v in r["model"].values():
                for k in ("l1_n", "l1_hits", "l2_n", "l2_hits", "l3_n", "l3_hits"):
                    t[k] += v["counts"][k]
        return t
    hint = {"with": pool(J(RS, "claude", "records_claude-haiku-5-5.json")["records"], 1),
            "without": pool(J(RS, "nohint_haiku", "records_claude-haiku-5-5.json")["records"], 1)}

    # M2
    m2 = J(M2, "summary_factorial.json")
    main = m2["analysis"]["main"]["all"]
    rho = {k: {"mean": v["mean"], "lo": v["lo"], "hi": v["hi"]} for k, v in main["arm_mean_rho"].items()}
    diff = {k: {"mean": v["mean"], "lo": v["lo"], "hi": v["hi"]} for k, v in main["differences"].items()}
    m2_out = {"rho": rho, "diff": diff, "verdicts": main["reading"]["verdicts"],
              "a_separates": main["reading"]["A_separates"], "n_stages": m2["counts_all_stages"]["n_stages"],
              "n_runs": main["n_runs"],
              "f0_ig_zero": {"stages": m2["counts_all_stages"]["ig_zero_stage_share"]["F0"]["stages_ig_zero_for_every_candidate"],
                             "of": m2["counts_all_stages"]["ig_zero_stage_share"]["F0"]["n_stages"]},
              "f3_error_median": {"deepseek": placement["deepseek"]["median"], "haiku": placement["haiku"]["median"],
                                  "opus": placement["opus"]["median"]}}

    # validity layer
    def val(part, name):
        v = J(RS, part, "validity.json")[name]
        top = v["kept_vs_guesses"]["V+vote1.0"]
        return {"removed_share": v["share_removed"]["share_removed"], "n_removed": v["share_removed"]["n_removed"],
                "n_guesses": v["share_removed"]["n_guesses"],
                "l3_diff": v["kept_vs_removed"]["L3"]["mean_diff"], "l3_verdict": v["kept_vs_removed"]["L3"]["verdict"],
                "brier": v["reliability"]["brier"], "tau1_l3_hits": top["l3_hits"], "tau1_l3_items": top["l3_items"]}
    validity = {"opus": val("claude", "claude-opus-5-5"), "haiku": val("claude", "claude-haiku-5-5"),
                "deepseek": val("exploratory", "deepseek"), "random": val("exploratory", "placebo")}

    new = {k: old[k] for k in ("_how", "paper_compare_json", "_table871", "table871_updated", "asp853_full_budget")}
    new["_how"] = ("Part 3 values below come from the result files named in _sources, written by fill_slots_part3.py. "
                   "Edit part 2 keys by hand; rerun the script after any result file changes.")
    new["outcome"] = {"The claim holds": "works", "Mixed": "mixed", "The claim fails": "fails",
                      "Inconclusive": "inconclusive"}[cl["family"]["thesis"]]
    new["thesis"] = cl["family"]["thesis"]
    new["_sources"] = {
        "blind": "results_semantic_1113/{claude,exploratory}/results.json: models.<m>.analysis.levels.<L>, family.hypotheses",
        "mdd": "results_semantic_1113/exploratory/mdd_table.json: levels",
        "wrong_house": "results_semantic_1113/{claude,exploratory}/results.json: family.wrong_house_gate",
        "opus_check": "results_semantic_1113/independent_recompute/margin_summary.json: summary",
        "placement": "results_semantic_1113/{claude,exploratory}/error_sample_*.json",
        "room": "results_semantic_1113/claude/room_test.json: live.by_arm, replay.<m>.totals",
        "hint": "results_semantic_1113/{claude,nohint_haiku}/records_claude-haiku-5-5.json: records[round 1].model.<member>.counts",
        "m2": "results_m2_1113/pass2/summary_factorial.json: analysis.main.all",
        "validity": "results_semantic_1113/{claude,exploratory}/validity.json",
        "members": "results_semantic_1113/claude/results.json: models.<m>.status; cost $35.78 from docs/ENDSEM_FINAL_PLAN_2026-11-13.md (progress log 11-13 20:38)"}
    new["blind"] = {"models": models, "mdd": mdd, "wrong_house": wrong, "opus_l3_check": opus_check,
                    "members": members, "replay_cost_usd": 35.78}
    new["placement"] = placement
    new["room_test"] = room
    new["hint"] = hint
    new["m2"] = m2_out
    new["validity"] = validity
    json.dump(new, open(SLOTS, "w"), indent=1)
    print("wrote", SLOTS, "outcome:", new["outcome"], "|", new["thesis"])


if __name__ == "__main__":
    main()
