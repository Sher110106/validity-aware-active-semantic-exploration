"""Pre-registered wave-2 pacing: per-stage median llm_wait_s over the wave-1
official runs for the stages they reached; the prior (260, 400, 500) for later
stages. Prints the schedule string."""
import glob, json, statistics, sys
C = "/home/sher/active-semantic-perception-workspace/runs/live_campaign"
runs = sys.argv[1:]
prior = [260.0, 400.0, 500.0]
by_stage = {}
for r in runs:
    for f in glob.glob(f"{C}/{r}/stages/*/live_policy.jsonl"):
        stage = int(f.split("/stages/")[1].split("/")[0])
        for l in open(f):
            w = json.loads(l).get("llm_wait_s")
            if w is not None:
                by_stage.setdefault(stage, []).append(w)
n = max(by_stage) + 1 if by_stage else 0
sched = []
for k in range(max(n, 3)):
    sched.append(round(statistics.median(by_stage[k])) if by_stage.get(k) else round(prior[min(k, 2)]))
sched.append(500)  # prior for stages beyond those reached
print(json.dumps({"per_stage_n": {k: len(v) for k, v in sorted(by_stage.items())}}))
print(",".join(str(int(x)) for x in sched))
