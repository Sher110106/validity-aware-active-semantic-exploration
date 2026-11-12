#!/usr/bin/env python3
"""Print markdown tables from summary.json (stdout only)."""
import json
import os

OUT = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(OUT, "summary.json")))
SETS = ["actual", "none", "placebo_A", "placebo_B", "oracle"]
RULES = ["R1", "R2", "R3", "R4", "R5", "R6"]


def f(x, d=2):
    return "NA" if x is None else f"{x:.{d}f}"


def cell(c, d=2):
    return f"{f(c['mean'], d)} [{f(c['ci95'][0], d)}, {f(c['ci95'][1], d)}]"


def tab(name, grp, d=2):
    t = S["tables"][name][grp]
    print(f"\n**{name} / {grp}** (n = {t['n_stages']} stages, {t.get('n_runs')} runs)\n")
    print("| rule | " + " | ".join(SETS) + " |")
    print("|---|" + "---|" * len(SETS))
    for r in RULES:
        print(f"| {r} | " + " | ".join(cell(t["cells"][r][s], d) for s in SETS) + " |")


y = S["yardstick_check"]
print("## Yardstick check\n")
print("| yardstick | n_in | mapped_in | share_in | n_out | mapped_out | share_out | in-out [CI] | ratio [CI] |")
print("|---|---|---|---|---|---|---|---|---|")
for k in ("Uwall", "U360"):
    v = y[k]
    print(f"| {k} | {v['n_in']} | {v['in_mapped']} | {f(v['share_in'], 3)} | {v['n_out']} | {v['out_mapped']} | "
          f"{f(v['share_out'], 4)} | {f(v['separation_in_minus_out'], 3)} [{f(v['separation_ci95'][0], 3)}, "
          f"{f(v['separation_ci95'][1], 3)}] | {f(v['ratio_in_over_out'], 1)} [{f(v['ratio_ci95'][0], 1)}, "
          f"{f(v['ratio_ci95'][1], 1)}] |")
print(f"\nstages {y['n_stages']}; U_wall - U_360 separation {f(y['Uwall']['minus_U360_separation'], 3)} "
      f"CI {y['Uwall']['minus_U360_ci95']}; verdict: {y['verdict']}")
print("\nSensitivity (not pre-registered):")
for k, v in S["sensitivity"]["yardstick_check"].items():
    if isinstance(v, dict) and "share_in" in v:
        print(f"- {k}: n_in {v['n_in']}, share_in {f(v['share_in'], 3)}, share_out {f(v['share_out'], 4)}, "
              f"sep {f(v['separation_in_minus_out'], 3)}, minus U360 {f(v.get('minus_U360_separation'), 3)} "
              f"{v.get('minus_U360_ci95')}")
print("\n## Decision rule (U_wall, raw regret)\n")
print("| rule | (a) oracle | (a) placebo A | ratio [CI] | (a) pass | (b) n | LLM | pA | pB | LLM-pA [CI] | floor | (b) pass |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in ["R1", "R2", "R3", "R4"]:
    a, b = S["decision"][r]["a"], S["decision"][r]["b"]
    print(f"| {r} | {f(a['oracle_mean'])} | {f(a['placebo_A_mean'])} | {f(a['ratio'], 3)} [{f(a['ratio_ci95'][0], 3)}, "
          f"{f(a['ratio_ci95'][1], 3)}] | {a['pass']} | {b['n_stages']} | {f(b['LLM_mean'])} | {f(b['placebo_A_mean'])} | "
          f"{f(b['placebo_B_mean'])} | {f(b['LLM_minus_A'], 3)} [{f(b['LLM_minus_A_ci95'][0], 3)}, "
          f"{f(b['LLM_minus_A_ci95'][1], 3)}] | {f(b['noise_floor_p2.5'], 3)} | {b['pass']} |")
print(f"\ngo_live = {S['decision']['go_live']}")
for nm, D in S["decision_reported_only"].items():
    print(f"\n{nm} (reported only): " + "; ".join(
        f"{r}: ratio {f(D[r]['a']['ratio'], 3)} {[round(x, 3) for x in D[r]['a']['ratio_ci95']]} a={D[r]['a']['pass']}, "
        f"LLM-pA {f(D[r]['b']['LLM_minus_A'], 3)} {[round(x, 3) for x in D[r]['b']['LLM_minus_A_ci95']]} "
        f"floor {f(D[r]['b']['noise_floor_p2.5'], 3)} b={D[r]['b']['pass']}" for r in ["R1", "R2", "R3", "R4"]))
print("\nSensitivity decisions (not pre-registered):")
for v, D in S["sensitivity"]["decision"].items():
    print(f"- {v}: go_live {D['go_live']}; " + "; ".join(
        f"{r} ratio {f(D[r]['a_ratio'], 3)} a={D[r]['a_pass']} b={D[r]['b_pass']}" for r in ["R1", "R2", "R3", "R4"]))
print("\nfilter_only actual vs placebo A (reported separately):")
for r, v in S["filter_only_actual_vs_placebo"].items():
    print(f"- {r}: n {v['n_stages']}, actual-pA {f(v['actual_minus_A'], 3)} {[round(x, 3) for x in v['ci95']]}, "
          f"floor {f(v['floor_p2.5'], 3)}")
print("\n## R5 comparisons (rule - R5; negative = rule better)")
for nm, D in S["R5_comparisons"].items():
    print(f"\n{nm} (n {D['n_stages']}): beats R5: {D['any_guess_rule_beats_R5']}")
    for s in SETS:
        print(f"- {s}: " + "; ".join(f"{r} {f(D[s][r]['rule_minus_R5'], 2)} {[round(x, 2) for x in D[s][r]['ci95']]}"
                                     for r in ["R1", "R2", "R3", "R4"]))
print("\n## Regret tables")
for name in ("Uwall", "Ucone", "Uwall_norm", "Ucone_norm"):
    for grp in ("pooled", "official", "placebo", "filter_only", "oracle_visible"):
        tab(name, grp, 3 if "norm" in name else 2)
print("\n## Descriptors\n", json.dumps(S["descriptors"], indent=1))
print("\nn_used", S["n_used"], S["n_by_arm"], S["n_runs_by_arm"])
print("drops", json.dumps(S["drops"]))
