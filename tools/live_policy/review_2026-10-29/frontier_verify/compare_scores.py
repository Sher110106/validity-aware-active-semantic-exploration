import json
mine = json.load(open("/tmp/cvp_verify_step7/scores.json"))["runs"]
D = "/Users/sher/project/cvp/project/tools/live_policy/results_2026-10-31/frontier_seeds/"
for fn in ("all_scores_with_frontier.json", "frontier_seeds_scores.raw.json"):
    data = json.load(open(D + fn))
    if isinstance(data, dict):
        print(fn, "dict keys", list(data)[:10]); data = data.get("runs", data)
    print(fn, type(data).__name__, len(data))
    keys = [k for k in data[0] if not isinstance(data[0][k], (list, dict))]
    print("  scalar keys:", keys)
    worst = 0
    for r in data:
        n = r["run_dir"].rstrip("/").split("/")[-1]
        if n not in mine or "auc60" not in mine[n]:
            continue
        for mk, tk in (("auc60", "hm3d_auc_af_f1_to_60m"), ("auc50", "hm3d_auc_af_f1_to_50m"), ("final_path_m", "final_path_m")):
            if tk not in r:
                print("  missing", tk, n); continue
            d = abs(mine[n][mk] - r[tk]); worst = max(worst, d) if mk != "final_path_m" else worst
            if d > 0.00005 if mk != "final_path_m" else d > 1e-6:
                print(f"  DIFF {n} {mk}: mine {mine[n][mk]:.6f} theirs {r[tk]}")
    print("  worst AUC |diff| over matched runs:", worst)
