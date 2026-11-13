import json, numpy as np
import os
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = json.load(open(f"{B}/pass2/summary_factorial.json"))
F1p = json.load(open(f"{B}/pass1/summary_factorial.json"))
M = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mine.json")))
views = {"main": ("main", "all"), "ig_alone": ("ig_alone", "all"), "Ucone_audit": ("audit_Ucone", "all"),
         "U360": ("U360", "all"), "official": ("main", "official")}
worst = 0; rows = []
for mine, (fv, sub) in views.items():
    f = F["analysis"][fv][sub]; m = M[mine]
    for c in ["A", "B_deepseek", "B_haiku", "B_opus", "C", "F0-F5", "F6-F5"]:
        a = m["contrasts"][c]; b = f["differences"][c]
        d = max(abs(a[0]-b["mean"]), abs(a[1]-b["lo"]), abs(a[2]-b["hi"])); worst = max(worst, d)
        rows.append((mine, c, a[:3], (b["mean"], b["lo"], b["hi"]), d))
    for c in ["B_deepseek", "B_haiku", "B_opus", "C"]:
        a = m["contrasts"][c + "-0.5A"]; b = f["reading_series"][c]
        d = max(abs(a[0]-b["mean"]), abs(a[1]-b["lo"]), abs(a[2]-b["hi"])); worst = max(worst, d)
        rows.append((mine, c+"-0.5A", a[:3], (b["mean"], b["lo"], b["hi"]), d))
        mv = m["verdicts"][c]; fvd = f["reading"]["verdicts"][c]
        if not fvd.startswith(mv): print("VERDICT DIFF", mine, c, mv, fvd)
    for A in m["arm_mean"]:
        dm = abs(m["arm_mean"][A] - f["arm_mean_rho"][A]["mean"]); dmed = abs(m["arm_median_stage"][A] - f["median_stage_rho"][A])
        worst = max(worst, dm, dmed)
        if max(dm, dmed) > 1e-9: print("arm diff", mine, A, dm, dmed)
    print(mine, "n kept filed", f["n_stages_kept"], "mine", m["n_stages"], "runs", f["n_runs"], m["n_runs"])
    # per-run means check
    if "per_run_mean_rho" in f and mine == "main":
        pass
for r in rows: print(f"{r[0]:12s} {r[1]:16s} mine {r[2][0]:+.4f} [{r[2][1]:+.4f},{r[2][2]:+.4f}] filed {r[3][0]:+.4f} [{r[3][1]:+.4f},{r[3][2]:+.4f}] maxdiff {r[4]:.4f}")
print("worst", worst)
# pass1 vs pass2 consistency for shared arms
for fv in ["main", "ig_alone", "audit_Ucone", "U360"]:
    for c in ["A", "B_deepseek", "C", "F0-F5", "F6-F5"]:
        a = F1p["analysis"][fv]["all"]["differences"][c]; b = F["analysis"][fv]["all"]["differences"][c]
        if any(abs(a[x]-b[x]) > 1e-12 for x in ("mean", "lo", "hi")): print("pass1/pass2 differ", fv, c)
print("ig zero share filed", F["counts_all_stages"]["ig_zero_stage_share"])
