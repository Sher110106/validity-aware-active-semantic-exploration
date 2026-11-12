#!/usr/bin/env python3
"""Build the results package from a run_final_analysis.sh output directory.

Inputs: <analysis_dir> (all_scores.json, E*.json, covariates.json,
stage_precision.json, stage_diagnostics.json), <logs_dir> (runner_*.log and
sched_state.json copied from the host), the frontier explorer's scores.
Outputs in <out_dir>: run_table.csv/.md, tests.csv/.md (with Holm for E1+E2),
mechanism.md, numbers.csv, and figures/*.png.

Usage: build_results.py <analysis_dir> <logs_dir> <frontier_scores.json> <out_dir>
"""
import csv
import glob
import json
import math
import os
import re
import sys

ARMS = ["official", "placebo", "filter_only", "oracle_visible"]
LABEL = {"official": "Official (DeepSeek)", "placebo": "Placebo", "filter_only": "Filter",
         "oracle_visible": "Oracle"}
COLOR = {"official": "#2a78d6", "placebo": "#eb6834", "filter_only": "#1baf7a", "oracle_visible": "#eda100"}
MARKER = {"official": "o", "placebo": "s", "filter_only": "^", "oracle_visible": "D"}
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
NAME = re.compile(r"e\d+_(?P<scene>\d{5})_s(?P<seed>\d+)_(?P<arm>[a-z_]+)_(?P<budget>\d+)m(?:_rerun(?P<rerun>\d+))?$")
CONTRASTS = [("E1", "official", "placebo"), ("E2", "official", "filter_only"),
             ("E3", "oracle_visible", "placebo"), ("E3_vs_official", "oracle_visible", "official")]


def load(path, default=None):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def run_logs(logs_dir):
    """name -> {outcome, path_m, cost_usd, launched, finished} from runner logs.

    A name can be launched more than once (earlier attempts were renamed on
    disk), so events from all logs are read in time order and the latest
    attempt that ended is kept."""
    pat_launch = re.compile(r"^(\S+) \[(\S+)\] launched (\S+):")
    pat_end = re.compile(r"^(\S+) \[(\S+)\] (\S+): (\w+) at ([\d.]+|None) m, \$([\d.]+|None)")
    events = []
    for f in glob.glob(os.path.join(logs_dir, "runner_*.log")):
        for line in open(f):
            m = pat_launch.match(line)
            if m:
                events.append((m.group(1)[:19], "launch", m.group(3), {"launched": m.group(1), "container": m.group(2)}))
                continue
            m = pat_end.match(line)
            if m:
                events.append((m.group(1)[:19], "end", m.group(3), {
                    "finished": m.group(1), "outcome": m.group(4),
                    "path_m": float(m.group(5)) if m.group(5) != "None" else None,
                    "cost_usd": float(m.group(6)) if m.group(6) != "None" else None}))
    current, out = {}, {}
    for _, kind, name, fields in sorted(events, key=lambda e: (e[0], e[1] == "end")):
        if kind == "launch":
            current[name] = dict(fields)
        else:
            rec = current.setdefault(name, {})
            rec.update(fields)
            out[name] = dict(rec)
    return out


def exclusion_reasons(logs_dir):
    """run -> reason from EXCLUDED_<run>.json markers copied into logs_dir."""
    out = {}
    for p in glob.glob(os.path.join(logs_dir, "EXCLUDED_*.json")):
        name = os.path.basename(p)[len("EXCLUDED_"):-len(".json")]
        out[name] = (load(p, {}) or {}).get("reason", "excluded")
    return out


def hours(rec):
    import datetime as dt
    try:
        a = dt.datetime.strptime(rec["launched"][:19], "%Y-%m-%dT%H:%M:%S")
        b = dt.datetime.strptime(rec["finished"][:19], "%Y-%m-%dT%H:%M:%S")
        return round((b - a).total_seconds() / 3600, 2)
    except (KeyError, ValueError):
        return None


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, running = [None] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = running
    return adj


def fmt(x, nd=4, signed=True):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    if not isinstance(x, float):
        return str(x)
    return f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}"


def main():
    adir, ldir, frontier_path, out = sys.argv[1:5]
    os.makedirs(os.path.join(out, "figures"), exist_ok=True)
    scores = {os.path.basename(r["run_dir"].rstrip("/")): r for r in load(os.path.join(adir, "all_scores.json"), [])}
    cov = {r["run"]: r for r in load(os.path.join(adir, "covariates.json"), [])}
    logs = run_logs(ldir)
    reasons = exclusion_reasons(ldir)
    frontier = {("00853" if "853" in r["run_dir"] else "00871"): r for r in load(frontier_path, [])}
    tests = {}
    for f in glob.glob(os.path.join(adir, "E*_*m.json")):
        tests[os.path.basename(f)[:-5]] = load(f, {})
    counted = set()
    dropped = {}
    for t in tests.values():
        counted |= set(t.get("counted_runs", []))
        for d in t.get("dropped", []):
            dropped.setdefault(d["run"], d["reason"])
    numbers = []

    def num(key, value, source):
        numbers.append({"key": key, "value": value, "source": source})

    # 1. Run table.
    rows = []
    for name in sorted(scores):
        m = NAME.search(name)
        if not m:
            continue
        r, c, lg = scores[name], cov.get(name, {}), logs.get(name, {})
        row = {"run": name, "arm": m.group("arm"), "scene": m.group("scene"), "seed": int(m.group("seed")),
               "rerun": m.group("rerun") or "", "container": lg.get("container", ""), "outcome": lg.get("outcome", "running?"),
               "hours": hours(lg), "path_m": round(r.get("final_path_m", 0), 1), "cost_usd": lg.get("cost_usd"),
               "status": "counted" if name in counted else ("excluded: " + reasons.get(name, dropped[name]) if name in dropped else "not in a contrast"),
               "stages": c.get("stages"), "m_per_stage": c.get("m_per_stage"),
               "dropped_member_rate": c.get("dropped_member_rate"), "llm_wait_mean_s": c.get("llm_wait_mean_s"),
               "sleep_s_per_m": c.get("sleep_s_per_m"), "fallback_share": c.get("fallback_share")}
        for ref, pre in (("hm3d", "hm3d_"), ("frontier", "")):
            for b in (50, 60):
                row[f"auc_{ref}_{b}m"] = r.get(f"{pre}auc_af_f1_to_{b}m")
        rows.append(row)
        num(f"auc_hm3d_60m:{name}", row["auc_hm3d_60m"], "all_scores.json:hm3d_auc_af_f1_to_60m")
        num(f"auc_hm3d_50m:{name}", row["auc_hm3d_50m"], "all_scores.json:hm3d_auc_af_f1_to_50m")
        num(f"auc_frontier_60m:{name}", row["auc_frontier_60m"], "all_scores.json:auc_af_f1_to_60m")
        num(f"path_m:{name}", row["path_m"], "all_scores.json:final_path_m")
        num(f"hours:{name}", row["hours"], "runner logs: launch to end of the last attempt")
        num(f"cost_usd:{name}", row["cost_usd"], "runner logs: stop line of the last attempt")
        for k in ("llm_wait_mean_s", "dropped_member_rate", "sleep_s_per_m", "stages", "m_per_stage"):
            if row.get(k) is not None:
                num(f"{k}:{name}", row[k], f"covariates.json:{k}")
    fields = list(rows[0].keys()) if rows else []
    with open(os.path.join(out, "run_table.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out, "run_table.md"), "w") as f:
        cols = ["run", "status", "path_m", "hours", "cost_usd", "auc_hm3d_60m", "auc_hm3d_50m", "auc_frontier_60m",
                "dropped_member_rate", "llm_wait_mean_s", "sleep_s_per_m"]
        f.write("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n")
        for row in rows:
            f.write("| " + " | ".join("" if row[k] is None else (f"{row[k]:.4f}" if isinstance(row[k], float) and k.startswith("auc") else str(row[k])) for k in cols) + " |\n")

    # 2. Tests, with Holm over E1 and E2 per reference and budget.
    trows = []
    for ref in ("hm3d", "frontier"):
        for b in (60, 50):
            group = {}
            for cname, a, bb in CONTRASTS:
                t = tests.get(f"{cname}_{ref}_{b}m", {})
                if "statistic" not in t:
                    continue
                n = t.get("n_relabelings") or 0
                pci = t.get("permutation_95ci")
                unbounded = n == 0 or 2 / n > 0.05
                group[cname] = {"contrast": t["contrast"], "ref": ref, "budget_m": b, "statistic": t["statistic"],
                                "p": t["blocked_permutation_p"], "n_relabelings": n,
                                "min_p": round(2 / n, 4) if n else None,
                                "bootstrap_ci": t.get("bootstrap_95ci"),
                                "permutation_ci": "unbounded at this n" if unbounded else (
                                    [("<= " if abs(pci[0] - (t["statistic"] - 0.1)) < 1e-9 else "") + f"{pci[0]:.4f}",
                                     (">= " if abs(pci[1] - (t["statistic"] + 0.1)) < 1e-9 else "") + f"{pci[1]:.4f}"]
                                    if pci else pci),
                                "mde": t.get("mde_alpha05_power80"),
                                "signflip_p": t.get("seed_paired_signflip_p"),
                                "per_scene": {s: v["diff_of_means"] for s, v in t.get("per_scene", {}).items()},
                                "n_runs": {s: (len(v[a]), len(v[bb])) for s, v in t.get("per_scene", {}).items()}}
            fam = [k for k in ("E1", "E2") if k in group]
            for k, adj in zip(fam, holm([group[k]["p"] for k in fam])):
                group[k]["holm_p_E1E2"] = adj
            for k, g in group.items():
                g["family"] = k
                trows.append(g)
                num(f"{k}:{ref}:{b}m:statistic", g["statistic"], f"{k}_{ref}_{b}m.json:statistic")
                num(f"{k}:{ref}:{b}m:p", g["p"], f"{k}_{ref}_{b}m.json:blocked_permutation_p")
                src = f"{k}_{ref}_{b}m.json"
                t = tests[f"{k}_{ref}_{b}m"]
                for i, side in enumerate(("lo", "hi")):
                    num(f"{k}:{ref}:{b}m:bootstrap_{side}", t["bootstrap_95ci"][i], f"{src}:bootstrap_95ci/{i}")
                    num(f"{k}:{ref}:{b}m:permutation_{side}", t["permutation_95ci"][i], f"{src}:permutation_95ci/{i}")
                num(f"{k}:{ref}:{b}m:mde", t["mde_alpha05_power80"], f"{src}:mde_alpha05_power80")
                num(f"{k}:{ref}:{b}m:signflip_p", t.get("seed_paired_signflip_p"), f"{src}:seed_paired_signflip_p")
                if g.get("holm_p_E1E2") is not None:
                    num(f"{k}:{ref}:{b}m:holm_p", g["holm_p_E1E2"], "Holm over E1 and E2 p-values (tests.json)")
                for scene, v in t.get("per_scene", {}).items():
                    num(f"{k}:{ref}:{b}m:per_scene_d:{scene}", v["diff_of_means"], f"{src}:per_scene/{scene}/diff_of_means")
    json.dump(trows, open(os.path.join(out, "tests.json"), "w"), indent=1, default=str)
    with open(os.path.join(out, "tests.md"), "w") as f:
        f.write("| family | contrast | ref | budget | d | p | Holm p (E1+E2) | relabelings (min p) | bootstrap 95% CI | permutation 95% CI | MDE | per-scene d | runs per scene |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for g in trows:
            bci = g["bootstrap_ci"]
            pci = g["permutation_ci"]
            f.write(f"| {g['family']} | {g['contrast']} | {g['ref']} | {g['budget_m']} m | {g['statistic']:+.4f} | {g['p']:.3f} | "
                    f"{fmt(g.get('holm_p_E1E2'), 3, False) if g.get('holm_p_E1E2') is not None else ''} | {g['n_relabelings']} ({g['min_p']}) | "
                    f"[{bci[0]:+.4f}, {bci[1]:+.4f}] | {pci if isinstance(pci, str) else '[' + ', '.join(pci) + ']'} | "
                    f"{g['mde']:.4f} | " + ", ".join(f"{s}: {v:+.4f}" for s, v in g["per_scene"].items()) + " | "
                    + ", ".join(f"{s}: {x}v{y}" for s, (x, y) in g["n_runs"].items()) + " |\n")

    # 3. Mechanism tables.
    sp = load(os.path.join(adir, "stage_precision.json"), {"rows": []})
    diag = load(os.path.join(adir, "stage_diagnostics.json"), [])
    # Gate verdicts were registered from single-run calls of stage_diagnostics.py
    # (fresh generator, seed 0), saved as E3_gate_*.json. The final pass runs all
    # runs through one generator, so its p-values differ by Monte Carlo noise.
    # Use the registered files when they are present in logs_dir.
    gate_files = {}
    for gp in sorted(glob.glob(os.path.join(ldir, "E3_gate_*.json"))):
        for g in load(gp, []):  # stage_diagnostics.py writes a list, one entry per run
            if g.get("gate"):
                gate_files[g["run"]] = dict(g, source=os.path.basename(gp))
    agg = {}
    per_run = {}
    for r in sp["rows"]:
        if r["run"] not in counted:
            continue
        for part in ("final", "raw", "removed"):
            if part not in r:
                continue
            key = (r["arm"], r["scene"], part)
            t = agg.setdefault(key, {"n_new": 0, "h05": 0, "h10": 0, "h20": 0})
            t["n_new"] += r[part]["n_new"]
            t["h05"] += r[part]["new_hits_0.5"]
            t["h10"] += r[part]["new_hits_1.0"]
            t["h20"] += r[part]["new_hits_2.0"]
            if part == "final":
                pr = per_run.setdefault(r["run"], [0, 0])
                pr[0] += r[part]["n_new"]
                pr[1] += r[part]["new_hits_0.5"]
    with open(os.path.join(out, "mechanism.md"), "w") as f:
        f.write("## Precision of new hypothesis objects against the human labels (counted runs; counts are (stage, member) instances, runs are the independent unit)\n\n")
        f.write("| arm | scene | part | new objects | within 0.5 m (hits) | within 1 m (hits) | within 2 m (hits) | per-run range at 0.5 m |\n|---|---|---|---|---|---|---|---|\n")
        for (arm, scene, part), t in sorted(agg.items()):
            runs = [v[1] / v[0] for k, v in per_run.items() if NAME.search(k) and NAME.search(k).group("arm") == arm
                    and NAME.search(k).group("scene") == scene and v[0]]
            rng = f"{min(runs) * 100:.2f}-{max(runs) * 100:.2f}%" if runs and part == "final" else ""
            n = t["n_new"] or 1
            f.write(f"| {LABEL.get(arm, arm)} | {scene} | {part} | {t['n_new']} | {100 * t['h05'] / n:.2f}% ({t['h05']}) | "
                    f"{100 * t['h10'] / n:.2f}% ({t['h10']}) | {100 * t['h20'] / n:.2f}% ({t['h20']}) | {rng} |\n")
            num(f"precision05:{arm}:{scene}:{part}", round(t["h05"] / n, 4), "stage_precision.json rows (counted runs)")
        lf_rows = [r for r in load(os.path.join(adir, "later_found.json"), []) if r["run"] in counted and r.get("unique_hypotheses")]
        if lf_rows:
            f.write("\n## Later found (D3, descriptive): share of each run's unique hypotheses found later in the final map (later_found.json, counted runs)\n\n")
            f.write("| arm | scene | runs | unique hypotheses | found | share (pooled) | per-run range |\n|---|---|---|---|---|---|---|\n")
            by = {}
            for r in lf_rows:
                m = NAME.search(r["run"])
                by.setdefault((m.group("arm"), m.group("scene")), []).append(r)
            for (arm, scene), rs in sorted(by.items()):
                u, fd = sum(r["unique_hypotheses"] for r in rs), sum(r["found"] for r in rs)
                f.write(f"| {LABEL.get(arm, arm)} | {scene} | {len(rs)} | {u} | {fd} | {100 * fd / u:.2f}% | "
                        f"{100 * min(r['share'] for r in rs):.2f}-{100 * max(r['share'] for r in rs):.2f}% |\n")
                num(f"later_found_share:{arm}:{scene}", round(fd / u, 4), "later_found.json (counted runs, pooled)")
        f.write("\n## Base mapping rate and scanned share (stage_diagnostics.json)\n\n| run | arm | base rate k+1 | base rate k+2 | share of new hypotheses in scanned space |\n|---|---|---|---|---|\n")
        for d in diag:
            br = d.get("base_rate", {})
            f.write(f"| {d['run']} | {d['arm']} | {fmt(br.get('mapped_k1'), 3, False)} | {fmt(br.get('mapped_k2'), 3, False)} | {fmt(d.get('scanned_share_of_new_hypotheses'), 3, False)} |\n")
        gates = list(gate_files.values()) or [d for d in diag if d.get("gate")]
        if gates:
            f.write("\n## E3 gate: drawn vs undrawn eligible candidates (one-sided permutation p within stage and track)\n\n")
            f.write("Source: " + ("registered single-run gate files (E3_gate_*.json, seed 0)" if gate_files else "stage_diagnostics.json") + ".\n\n")
            f.write("| run | source | subset | approach gap | p | mapping gap (k+1) | p | k+2 gap | drawn / undrawn rows | later found (unique drawn) |\n|---|---|---|---|---|---|---|---|---|---|\n")
            for d in gates:
                for sub, g in d["gate"].items():
                    lf = d.get("later_found", {})
                    f.write(f"| {d['run']} | {d.get('source', 'stage_diagnostics.json')} | {sub} | {fmt(g['approach']['gap'], 3)} | {g['approach']['p_one_sided']:.3f} | "
                            f"{fmt(g['mapped1']['gap'], 3)} | {g['mapped1']['p_one_sided']:.3f} | {fmt(g.get('mapped2_gap'), 3)} | "
                            f"{g['approach']['n_drawn']} / {g['approach']['n_undrawn']} | "
                            f"{lf.get('unique')} ({fmt(lf.get('share'), 3, False)}) |\n")
                    if sub == "all":
                        src = d.get("source", "stage_diagnostics.json")
                        num(f"gate_approach_p:{d['run']}", round(g["approach"]["p_one_sided"], 4), src)
                        num(f"gate_mapping_p:{d['run']}", round(g["mapped1"]["p_one_sided"], 4), src)
                        num(f"gate_approach_gap:{d['run']}", round(g["approach"]["gap"], 4), src)
                        num(f"gate_mapping_gap:{d['run']}", round(g["mapped1"]["gap"], 4), src)
                        num(f"gate_rows_drawn:{d['run']}", g["approach"]["n_drawn"], src)
                        num(f"gate_rows_undrawn:{d['run']}", g["approach"]["n_undrawn"], src)
                        num(f"gate_stages_used:{d['run']}", d.get("stages_used"), src)
                        num(f"gate_base_rate_k1:{d['run']}", round(d["base_rate"]["mapped_k1"], 4), src)
    # 4. Figures.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE})
    counted_rows = [r for r in rows if r["status"] == "counted"]
    # (a) AUC per run by arm and scene, frontier as a dashed reference line (HM3D reference).
    for b in (60, 50):
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
        for ax, scene in zip(axes, ("00853", "00871")):
            arms = [a for a in ARMS if any(r["arm"] == a and r["scene"] == scene for r in counted_rows)]
            for i, arm in enumerate(arms):
                vals = [r for r in counted_rows if r["arm"] == arm and r["scene"] == scene]
                ys = [r[f"auc_hm3d_{b}m"] for r in vals]
                xs = [i + (j - (len(ys) - 1) / 2) * 0.15 for j in range(len(ys))]
                ax.scatter(xs, ys, s=55, marker=MARKER[arm], color=COLOR[arm], edgecolor=SURFACE, linewidth=1.5, zorder=3)
                if ys:
                    mean = sum(ys) / len(ys)
                    ax.plot([i - 0.28, i + 0.28], [mean, mean], color=INK, linewidth=2, zorder=4)
                    ax.annotate(f"{mean:.3f}", (i + 0.3, mean), color=INK2, fontsize=9, va="center")
            fr = frontier.get(scene, {}).get(f"hm3d_auc_af_f1_to_{b}m")
            if fr:
                ax.axhline(fr, color=INK2, linestyle="--", linewidth=1)
                # Value at the right edge, outside the data area; the title names the line.
                ax.annotate(f"{fr:.3f}", (1.0, fr), xycoords=("axes fraction", "data"), xytext=(3, 0),
                            textcoords="offset points", ha="left", va="center", fontsize=8, color=INK2)
            ax.set_xlim(-0.5, len(arms) - 0.3)
            ax.set_xticks(range(len(arms)), [LABEL[a].replace(" (", "\n(") for a in arms])
            ax.set_title(f"Scene {scene}", color=INK, fontsize=11)
            ax.grid(axis="y", color=GRID, linewidth=0.8)
            ax.set_axisbelow(True)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
        axes[0].set_ylabel(f"Object F1 AUC to {b} m (human labels)")
        fig.suptitle(f"Map quality per run, by arm (dots = runs; bar = arm mean; dashed = frontier explorer, one run)", color=INK, fontsize=11)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "figures", f"auc_by_arm_{b}m.png"), dpi=160)
        plt.close(fig)
    # (b) F1 vs path per scene, every counted run, HM3D reference.
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    for ax, scene in zip(axes, ("00853", "00871")):
        for arm in ARMS:
            runs = [r for r in counted_rows if r["arm"] == arm and r["scene"] == scene]
            for k, r in enumerate(runs):
                st = scores[r["run"]].get("hm3d_stages", [])
                xs = [s["path_m"] for s in st]
                ys = [s["af_f1"] for s in st]
                ax.plot(xs, ys, color=COLOR[arm], linewidth=2, alpha=0.85, label=LABEL[arm] if k == 0 else None)
        ax.set_xlim(0, 62)
        ax.set_title(f"Scene {scene}", color=INK, fontsize=11)
        ax.set_xlabel("Path (m)")
        ax.grid(color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("Object F1 (human labels)")
    axes[1].legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "figures", "f1_vs_path.png"), dpi=160)
    plt.close(fig)
    # (c) Precision of new hypotheses at three radii by arm (both scenes pooled, counted runs).
    fig, ax = plt.subplots(figsize=(7.5, 4))
    # The oracle is 100% by construction and would flatten the others; it is in the table.
    bars = [(arm, part) for arm in ARMS if arm != "oracle_visible" for part in (("final",) if arm != "filter_only" else ("final", "removed"))
            if any(k[0] == arm and k[2] == part for k in agg)]
    width = 0.8 / max(1, len(bars))
    for i, (arm, part) in enumerate(bars):
        tot = {"n_new": 0, "h05": 0, "h10": 0, "h20": 0}
        for (a, s, p), t in agg.items():
            if a == arm and p == part:
                for key in tot:
                    tot[key] += t[key]
        vals = [100 * tot[h] / max(1, tot["n_new"]) for h in ("h05", "h10", "h20")]
        for h, v in zip(("0.5m", "1m", "2m"), vals):
            num(f"precision_pooled:{arm}:{part}:{h}", round(v / 100, 4), "stage_precision.json rows (counted runs, both scenes)")
        xs = [j + (i - (len(bars) - 1) / 2) * width for j in range(3)]
        lab = LABEL[arm] + (" (kept)" if arm == "filter_only" and part == "final" else " (removed)" if part == "removed" else "")
        ax.bar(xs, vals, width=width * 0.92, color=COLOR[arm], alpha=1.0 if part == "final" else 0.45, label=lab)
        for x, v in zip(xs, vals):
            ax.annotate(f"{v:.1f}", (x, v), xytext=(0, 2), textcoords="offset points", ha="center", fontsize=7, color=INK2)
    ax.set_xticks(range(3), ["within 0.5 m", "within 1 m", "within 2 m"])
    ax.set_ylabel("% of new hypothesis objects near a\nsame-label unmapped labelled object")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "figures", "precision_by_arm.png"), dpi=160)
    plt.close(fig)
    # (d) E3 gate: drawn-minus-undrawn gaps per oracle run, with one-sided p beside each dot.
    gate_rows = [d for d in (list(gate_files.values()) or diag) if d.get("gate") and "all" in d["gate"]]
    gate_rows.sort(key=lambda d: (d["run"].split("_")[1], d["run"]))
    if gate_rows:
        status = {r["run"]: r["status"] for r in rows}
        fig, axes = plt.subplots(1, 2, figsize=(10, 0.55 * len(gate_rows) + 1.6), sharey=True)
        names = [d["run"] for d in gate_rows]
        ylabels = []
        for d in gate_rows:
            m = NAME.search(d["run"])
            tag = f"{m.group('scene')} s{m.group('seed')}" + (" retry" if m.group("rerun") else "") if m else d["run"]
            ylabels.append(tag + ("" if status.get(d["run"]) == "counted" else " (excluded)" if d["run"] in status else " (archived attempt)"))
        for ax, key, title in zip(axes, ("approach", "mapped1"), ("Approach: stop within 3.5 m", "Mapping: same label within 0.5 m at k+1")):
            for y, d in enumerate(gate_rows):
                g = d["gate"]["all"][key]
                counted_run = status.get(d["run"]) == "counted"
                ax.scatter([g["gap"]], [y], s=55, marker="D", color=COLOR["oracle_visible"] if counted_run else SURFACE,
                           edgecolor=COLOR["oracle_visible"], linewidth=1.5, zorder=3)
                ax.annotate(f"p {g['p_one_sided']:.2f}", (g["gap"], y), xytext=(8, 0), textcoords="offset points",
                            va="center", fontsize=8, color=INK2)
            ax.axvline(0, color=INK2, linewidth=1)
            ax.xaxis.set_major_locator(plt.MaxNLocator(4))
            ax.set_title(title, color=INK, fontsize=10)
            ax.set_xlabel("drawn minus undrawn rate")
            ax.grid(axis="x", color=GRID, linewidth=0.8)
            ax.set_axisbelow(True)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
        axes[0].set_yticks(range(len(names)), ylabels)
        axes[0].invert_yaxis()
        fig.suptitle("E3 gate per oracle run (registered single-run p, one-sided; hollow = not counted)", color=INK, fontsize=11)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "figures", "e3_gate.png"), dpi=160)
        plt.close(fig)
    # numbers.csv last, so the figure values recorded above are included.
    with open(os.path.join(out, "numbers.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["key", "value", "source"])
        w.writeheader()
        w.writerows(numbers)
    print(f"wrote {out}: {len(rows)} runs, {len(trows)} tests")


if __name__ == "__main__":
    main()
