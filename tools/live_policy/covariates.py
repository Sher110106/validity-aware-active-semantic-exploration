#!/usr/bin/env python3
"""Per-run covariates for the live campaign analysis (FINAL_PLAN section 4, O3).

For each run, from stages/*/live_policy.jsonl and navigation_stats.json:
stages with a policy record, final path, metres per stage, mean and median
LLM wait per stage (paid arms), mean stage duration (time between the first
records of consecutive stages), dropped-member rate (paid arms: share of the
4 x 2 ensemble slots missing on the last attempt of each stage), total sleep
and sleep seconds per metre ($0 arms), oracle fallback share and median
candidates in reach, and the retry count (attempts beyond the first).

Usage: covariates.py <campaign_dir> <out.json> <run> [<run> ...]
"""
import glob
import json
import os
import statistics
import sys

SLOTS = 8


def records(run_dir):
    out = {}
    for f in glob.glob(os.path.join(run_dir, "stages", "*", "live_policy.jsonl")):
        k = os.path.basename(os.path.dirname(f))
        if k.isdigit():
            out[int(k)] = [json.loads(l) for l in open(f) if l.strip()]
    return dict(sorted(out.items()))


def final_path(run_dir):
    paths = []
    for f in glob.glob(os.path.join(run_dir, "stages", "*", "navigation_stats.json")):
        try:
            paths.append(json.load(open(f)).get("total_path_length_meters", 0.0))
        except ValueError:
            pass
    return max(paths, default=0.0)


def main():
    campaign, out_path = sys.argv[1], sys.argv[2]
    rows = []
    for run in sys.argv[3:]:
        recs = records(os.path.join(campaign, run))
        path = final_path(os.path.join(campaign, run))
        firsts = [r[0]["ts"] for r in recs.values() if r]
        durations = [b - a for a, b in zip(firsts, firsts[1:])]
        waits = [r[-1].get("llm_wait_s") for r in recs.values() if r and r[-1].get("llm_wait_s") is not None]
        delays = [r[-1].get("delay_s") for r in recs.values() if r and r[-1].get("delay_s") is not None]
        dropped = []
        fallback, in_reach = [], []
        for r in recs.values():
            last = r[-1]
            members = [m for t in last.get("tracks", {}).values() for m in t.get("members", [])]
            if "llm_wait_s" in last:
                dropped.append(1 - sum(t.get("available", 0) for t in last.get("tracks", {}).values()) / SLOTS)
            for m in members:
                if "fallback" in m:
                    fallback.append(bool(m["fallback"]))
                    in_reach.append(m.get("n_candidates_in_reach", 0))
        n = len(recs)
        rows.append({
            "run": run, "stages": n, "final_path_m": round(path, 2),
            "m_per_stage": round(path / n, 3) if n else None,
            "retries": sum(len(r) - 1 for r in recs.values()),
            "llm_wait_mean_s": round(statistics.mean(waits), 1) if waits else None,
            "llm_wait_median_s": round(statistics.median(waits), 1) if waits else None,
            "stage_duration_mean_s": round(statistics.mean(durations), 1) if durations else None,
            "dropped_member_rate": round(statistics.mean(dropped), 4) if dropped else None,
            "sleep_total_s": round(sum(delays), 1) if delays else None,
            "sleep_s_per_m": round(sum(delays) / path, 2) if delays and path else None,
            "fallback_share": round(sum(fallback) / len(fallback), 4) if fallback else None,
            "candidates_in_reach_median": statistics.median(in_reach) if in_reach else None,
        })
    json.dump(rows, open(out_path, "w"), indent=1)
    for r in rows:
        print(json.dumps(r))


if __name__ == "__main__":
    main()
