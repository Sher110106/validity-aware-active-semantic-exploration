import glob, json, os, sys, time
C = "/home/sher/active-semantic-perception-workspace/runs/live_campaign"
prefix = sys.argv[1] if len(sys.argv) > 1 else "e1_"
now = time.time()
print(f"{'run':34} {'path':>6} {'stg':>4} {'calls':>6} {'cost':>7} {'$/m':>6} {'cache':>6} {'bad':>4} {'drop%':>6} {'delay':>6} {'llmwait':>8} {'age':>5}")
for run in sorted(glob.glob(f"{C}/{prefix}*")):
    if not os.path.isdir(run): continue
    name = os.path.basename(run)
    paths = []
    for nav in glob.glob(f"{run}/stages/*/navigation_stats.json"):
        try: paths.append(float(json.load(open(nav))["total_path_length_meters"]))
        except Exception: pass
    path = max(paths, default=0.0)
    stages = len([d for d in glob.glob(f"{run}/stages/*") if os.path.isdir(d)])
    U = []
    try: U = [json.loads(l) for l in open(f"{run}/prompts/usage.jsonl")]
    except FileNotFoundError: pass
    cost = sum(u["cost"] for u in U)
    P = sum(u.get("prompt_tokens") or 0 for u in U); Cc = sum(u.get("cached_tokens") or 0 for u in U)
    bad = sum(1 for u in U if u.get("status") == 200 and u.get("provider") is not None and (u.get("provider") != "DeepInfra" or "1017" not in (u.get("model") or "")))
    steps = avail = 0; delays = []; waits = []
    for f in glob.glob(f"{run}/stages/*/live_policy.jsonl"):
        for l in open(f):
            r = json.loads(l); steps += 4 * len(r.get("tracks", {}))
            avail += sum(t.get("available", 0) for t in r.get("tracks", {}).values())
            if r.get("delay_s") is not None: delays.append(r["delay_s"])
            if r.get("llm_wait_s") is not None: waits.append(r["llm_wait_s"])
    drop = 100 * (1 - avail / steps) if steps else 0
    acts = [os.path.getmtime(p) for p in glob.glob(f"{run}/stages/*") + glob.glob(f"{run}/prompts/usage.jsonl") + glob.glob(f"{run}/logs/exploration_pipeline.log")]
    age = now - max(acts) if acts else -1
    excl = " EXCLUDED" if os.path.exists(f"{C}/EXCLUDED_{name}.json") else ""
    print(f"{name:34} {path:6.1f} {stages:4d} {len(U):6d} {cost:7.3f} {cost/max(path,1):6.3f} {Cc/max(P,1):6.2f} {bad:4d} {drop:6.1f} {(sum(delays)/len(delays) if delays else 0):6.0f} {(sum(waits)/len(waits) if waits else 0):8.0f} {age:5.0f}{excl}")
for f in sorted(glob.glob(f"{C}/runner_asp-noetic*.log")):
    lines = open(f).read().splitlines()
    print(os.path.basename(f), "|", lines[-1][:150] if lines else "")
print("STOP/PAUSE files:", [os.path.basename(p) for p in glob.glob(f"{C}/STOP*") + glob.glob(f"{C}/PAUSE*")])
