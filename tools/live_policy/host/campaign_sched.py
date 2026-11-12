#!/usr/bin/env python3
"""Memory-aware scheduler for the live campaign (replaced campaign_chain.sh on 2026-10-28).

Every minute: reads sched_jobs.json and launches a job's single run with
start_runner.sh on an idle container when fewer than MAX_ACTIVE runs are going
and projected free memory stays above RESERVE_GB at every future moment until
the active runs and the new one end (each run grows at its measured rate; a
run that ends frees its memory). The first pending paid job and the first
pending $0 job are eligible, in list order.

Watchdog: if MemAvailable drops below STOP_GB with two runs going, stop the
youngest (STOP_<container>) unless the older one is about to finish. A
scheduled run that ends below 50 m is rerun once (..._rerun1), as the
pre-registration allows; a launch that never started (runner skipped it,
launch failed, or the job vanished) is relaunched once under its own name.
A run whose runner died while its pipeline runs is adopted by a new runner.

Job fields: name, scene, seed, policy, target_m, max_hours, max_cost_usd;
optional "pacing": "auto" (placebo: schedule from completed official runs,
as campaign_chain.sh did), "pacing_from": <run> (copy that run's exact
no_llm_delay_schedule from its manifest; the job waits until <run> has
launched) and "rerun_of": <run> (skip if <run> reached 50 m).
SCHED_PAUSE, PAUSE or STOP in the campaign dir stop launching.
"""
from __future__ import annotations

import glob
import json
import subprocess
import time
from pathlib import Path

W = Path("/home/sher/active-semantic-perception-workspace")
C = W / "runs" / "live_campaign"
T = W / "tools" / "live_policy"
JOBS, STATE, LOG = C / "sched_jobs.json", C / "sched_state.json", C / "sched.log"
POOL = ["asp-noetic", "asp-noetic-b", "asp-noetic-c", "asp-noetic-d", "asp-noetic-f", "asp-noetic-g"]
CAP = 30.0
MAX_ACTIVE = 3
RESERVE_GB = 10.0
STOP_GB = 12.0
MIN_LAUNCH_GB = 30.0
BASE_GB = 8.0                          # non-mapper memory of one run
MIN_RATE, NEW_RATE = 4.0, 7.0          # mapper growth, GB per hour per run
NEW_HOURS = {True: 6.5, False: 4.0}    # expected hours, paid vs $0 run
ENDING_SOON_H = 0.33
EXCLUDE_BELOW_M = 50.0
LOST_AFTER_S = 600
FREEZE_END = time.mktime(time.strptime("2026-10-31 09:00", "%Y-%m-%d %H:%M"))
POLL_S = 60
SCHED_KEYS = ("pacing", "pacing_from", "rerun_of")
NO_LLM = ("placebo", "observed_only", "oracle_visible")
RELAUNCH_OUTCOMES = ("skipped_host_memory", "launch_failed", "adopt_failed_not_running")
_hydra_cache: dict = {}


def log(msg: str) -> None:
    line = time.strftime("%Y-%m-%dT%H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def run(args: list[str], timeout: int = 60):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def mem_available() -> float:
    for line in open("/proc/meminfo"):
        if line.startswith("MemAvailable"):
            return int(line.split()[1]) / 1048576
    return 0.0


def runner_alive(c: str):
    r = run(["pgrep", "-f", f"live_runner.py --container {c} --"])
    return None if r is None else r.returncode == 0


def pipeline_alive(c: str):
    r = run(["docker", "exec", c, "pgrep", "-f", "run_pipeline_with_policy.py"])
    return None if r is None else r.returncode == 0


def hydra_gb(c: str) -> float:
    """Mapper RSS; on a failed docker exec, the last good reading."""
    r = run(["docker", "exec", c, "ps", "-C", "hydra_ros_node", "-o", "rss="])
    if r is None or r.returncode not in (0, 1):
        return _hydra_cache.get(c, 0.0)
    gb = sum(int(x) for x in r.stdout.split()) / 1048576
    _hydra_cache[c] = gb
    return gb


def load(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def status(c: str) -> dict:
    return load(C / f"status_{c}.json", {})


def save_state(state: dict) -> None:
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1))
    tmp.replace(STATE)


def paused() -> bool:
    return any((C / f).exists() for f in ("SCHED_PAUSE", "PAUSE", "STOP"))


def active_runs() -> list[dict]:
    """Runs going now: a live runner (named from its status file even if the
    docker check fails), or a pipeline left without one."""
    out = []
    for c in POOL:
        alive_r, alive_p = runner_alive(c), pipeline_alive(c)
        if not alive_r and alive_p is False:
            continue
        recs = [(n, r) for n, r in status(c).get("runs", {}).items() if "outcome" not in r]
        if (alive_r or alive_p) and recs:
            name, r = recs[-1]
            spec = r.get("spec", {})
            out.append({"container": c, "name": name, "runner": alive_r, "pipeline": alive_p,
                        "elapsed_h": float(r.get("elapsed_h") or 0.0), "path_m": float(r.get("path_m") or 0.0),
                        "max_hours": float(spec.get("max_hours", 7.5)), "target_m": float(spec.get("target_m", 60))})
        elif alive_r is None or alive_p is None or alive_r or alive_p:
            out.append({"container": c, "name": "?", "runner": alive_r, "pipeline": alive_p,
                        "elapsed_h": 0.0, "path_m": 0.0, "max_hours": 7.5, "target_m": 60})
    return out


def run_profile(a: dict) -> tuple:
    """(current GB, growth GB/h, hours left) for an active run."""
    e = a["elapsed_h"]
    if a["name"] == "?" or e < 0.5:
        rem = a["max_hours"] - e
        return BASE_GB + NEW_RATE * e, NEW_RATE, max(0.25, rem)
    h = hydra_gb(a["container"])
    rate, pace = max(MIN_RATE, h / e), a["path_m"] / e
    rem = min(a["max_hours"] - e, (a["target_m"] - a["path_m"]) / max(pace, 4.0))
    return BASE_GB + h, rate, max(0.25, rem)


def min_projected_free(avail: float, active: list[dict], paid: bool) -> float:
    """Lowest free memory over time if the new run starts now."""
    profiles = [run_profile(a) for a in active]
    h_new = NEW_HOURS[paid]
    horizon = max([h_new] + [p[2] for p in profiles])
    lowest, t = avail, 0.0
    while t <= horizon + 1e-9:
        used = sum(rate * t if t < rem else -cur for cur, rate, rem in profiles)
        new = BASE_GB + NEW_RATE * t if t < h_new else 0.0
        lowest = min(lowest, avail - used - new)
        t += 0.1
    return lowest


def idle_containers(active: list[dict]) -> list[str]:
    busy = {a["container"] for a in active}
    out = []
    for c in POOL:
        if c in busy:
            continue
        r = run(["docker", "inspect", "-f", "{{.State.Running}}", c])
        if r is not None and r.stdout.strip() == "true":
            out.append(c)
    return out


def max_path(name: str) -> float:
    paths = [load(Path(f), {}).get("total_path_length_meters", 0.0)
             for f in glob.glob(str(C / name / "stages" / "*" / "navigation_stats.json"))]
    return max(paths, default=0.0)


def pacing_schedule() -> tuple:
    logs = " ".join(open(f).read() for f in glob.glob(str(C / "runner_*.log")))
    offs = [Path(d).name for d in sorted(glob.glob(str(C / "e1_*_official_60m")))
            if f"finished {Path(d).name}: target_reached" in logs]
    out = run(["python3", str(T / "pacing_update.py"), *offs])
    return out.stdout.strip().splitlines()[-1], offs


def schedule_of(run_name: str):
    """The no_llm_delay_schedule a launched run actually used, from its manifest."""
    try:
        first = (C / run_name / "config" / "run_manifest.txt").read_text().splitlines()[0]
    except (OSError, IndexError):
        return None
    sched = first.split("no_llm_delay_schedule=", 1)[1].strip() if "no_llm_delay_schedule=" in first else ""
    return sched if sched and sched != "0" else None


def deviation(line: str) -> None:
    with open(C / "DEVIATIONS.md", "a") as f:
        f.write(f"{time.strftime('%H:%M')} {line}\n")


def launch(job: dict, c: str) -> None:
    spec = {k: v for k, v in job.items() if k not in SCHED_KEYS}
    if job.get("pacing_from"):
        spec["no_llm_delay_schedule"] = schedule_of(job["pacing_from"])
        deviation(f"{spec['name']} ({spec['policy']}): pacing copied from {job['pacing_from']}: "
                  f"{spec['no_llm_delay_schedule']}")
    elif job.get("pacing") == "auto":
        sched, offs = pacing_schedule()
        spec["no_llm_delay_schedule"] = sched
        deviation(f"{spec['name']} ({spec['policy']}): pacing from completed official runs ({' '.join(offs)}): {sched}")
    q = f"queue_sched_{spec['name']}.json"
    (C / q).write_text(json.dumps({"runs": [spec]}))
    run([str(T / "clean_container.sh"), c], timeout=120)
    r = run([str(T / "start_runner.sh"), c, q, "99", str(CAP)], timeout=120)
    log(f"launched {spec['name']} on {c}: {(r.stdout.strip() if r else 'start_runner timed out')[-300:]}")


def rerun_job(spec: dict) -> dict:
    """A rerun keeps the original's settings under ..._rerun1. A placebo rerun
    takes its pacing from completed official runs (E1's update rule); an
    oracle rerun keeps its copied schedule (E3: pacing equals its placebo
    partner's)."""
    job = dict(spec)
    job["name"] = spec["name"] + "_rerun1"
    if spec.get("policy") in ("placebo", "observed_only"):
        job.pop("no_llm_delay_schedule", None)
        job["pacing"] = "auto"
    return job


def check_launched(state: dict) -> None:
    """Record finished runs; rerun those below 50 m; relaunch launches that never started."""
    now = time.time()
    for name, info in list(state["launched"].items()):
        if name in state["done"]:
            continue
        c = info["container"]
        rec = status(c).get("runs", {}).get(name)
        if rec and "finished" in rec:
            state["done"][name] = {"outcome": rec.get("outcome"), "path_m": rec.get("path_m"),
                                   "cost_usd": rec.get("cost_usd"), "finished": rec.get("finished")}
            log(f"finished {name}: {rec.get('outcome')} at {rec.get('path_m')} m, ${rec.get('cost_usd')}")
            if (rec.get("path_m") or 0) < EXCLUDE_BELOW_M and "_rerun" not in name:
                state["requeue"].append(rerun_job(rec["spec"]))
                log(f"queued rerun of {name} (ended below {EXCLUDE_BELOW_M} m)")
            save_state(state)
            continue
        early = rec.get("outcome") if rec else None
        started = time.mktime(time.strptime(info["at"], "%Y-%m-%dT%H:%M:%S"))
        lost = early is None and now - started > LOST_AFTER_S and runner_alive(c) is False and pipeline_alive(c) is False
        if early in RELAUNCH_OUTCOMES or lost:
            why = early or "no record and no runner"
            n = state["relaunched"].get(name, 0)
            job = state["launched"].pop(name).get("job")
            in_file = any(j["name"] == name for j in load(JOBS, {"jobs": []})["jobs"])
            if job and not in_file and n < 1:
                state["requeue"].insert(0, job)
            if n >= 1:
                state["skipped"][name] = f"never started twice ({why})"
                log(f"giving up on {name}: never started twice ({why})")
            else:
                state["relaunched"][name] = n + 1
                log(f"relaunch {name} once: {why}")
            save_state(state)
        elif early:
            state["done"][name] = {"outcome": early}
            log(f"FLAG {name}: runner returned {early} without running; not rerun (operator decision)")
            save_state(state)


def adopt_orphans(state: dict, active: list[dict], seen: dict) -> None:
    """A pipeline whose runner died gets an adopting runner after two polls."""
    for a in active:
        c = a["container"]
        if a["runner"] is False and a["pipeline"] is True and a["name"] != "?":
            seen[c] = seen.get(c, 0) + 1
            if seen[c] >= 2:
                q = C / f"queue_sched_{a['name']}.json"
                if not q.exists():
                    spec = status(c).get("runs", {}).get(a["name"], {}).get("spec")
                    if not spec:
                        continue
                    q = C / f"queue_adopt_{a['name']}.json"
                    q.write_text(json.dumps({"runs": [spec]}))
                r = run([str(T / "start_runner.sh"), c, q.name, "99", str(CAP), "--adopt"], timeout=120)
                log(f"adopted orphan {a['name']} on {c}: {(r.stdout.strip() if r else 'timed out')[-200:]}")
                seen[c] = 0
        else:
            seen[c] = 0


def watchdog(state: dict, active: list[dict], avail: float) -> None:
    known = [a for a in active if a["name"] != "?"]
    if avail >= STOP_GB or len(known) < 2 or state["stopping"]:
        return
    young = min(known, key=lambda a: a["elapsed_h"])
    old = [a for a in known if a is not young]
    if avail > 8.0 and any(run_profile(a)[2] < ENDING_SOON_H for a in old):
        log(f"watchdog: MemAvailable {avail:.1f} GB, older run ends within {ENDING_SOON_H} h; waiting")
        return
    if young["runner"]:
        (C / f"STOP_{young['container']}").touch()
    else:
        run(["docker", "exec", young["container"], "pkill", "-f", "run_pipeline_with_policy.py"])
    state["stopping"][young["container"]] = young["name"]
    log(f"watchdog: MemAvailable {avail:.1f} GB; stopping youngest run {young['name']} on {young['container']}")
    save_state(state)


def next_job(state: dict, jobs: list[dict], active: list[dict], avail: float, waiting_logged: set) -> None:
    pending = state["requeue"] + [j for j in jobs if j["name"] not in state["launched"]
                                  and j["name"] not in state["skipped"] and j["name"] not in state["done"]]
    if not pending:
        if not active and not state.get("all_done_logged"):
            log("all jobs done; waiting for new jobs")
            state["all_done_logged"] = True
            save_state(state)
        return
    state["all_done_logged"] = False
    if paused() or len(active) >= MAX_ACTIVE or state["stopping"]:
        return
    eligible, seen = [], set()
    for job in pending:
        paid = job["policy"] not in NO_LLM
        if job.get("pacing_from") and not schedule_of(job["pacing_from"]):
            if job["name"] not in waiting_logged:
                log(f"{job['name']} waits for {job['pacing_from']} to launch (pacing source)")
                waiting_logged.add(job["name"])
            continue
        if paid not in seen:
            seen.add(paid)
            eligible.append(job)
    for job in eligible:
        orig = job.get("rerun_of")
        skip = None
        if (C / job["name"]).exists():
            skip = "run dir exists"
        elif orig and max_path(orig) >= EXCLUDE_BELOW_M:
            skip = f"{orig} reached {max_path(orig):.1f} m"
        if skip:
            state["skipped"][job["name"]] = skip
            log(f"skip {job['name']}: {skip}")
            if job in state["requeue"]:
                state["requeue"].remove(job)
            save_state(state)
            return
        paid = job["policy"] not in NO_LLM
        if time.time() + NEW_HOURS[paid] * 3600 > FREEZE_END:
            continue
        low = min_projected_free(avail, active, paid)
        if avail >= MIN_LAUNCH_GB and low >= RESERVE_GB:
            idle = idle_containers(active)
            if not idle:
                return
            c = idle[0]
            log(f"launch {job['name']}: avail {avail:.1f} GB, lowest projected free {low:.1f} GB")
            launch(job, c)
            state["launched"][job["name"]] = {"container": c, "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "job": job}
            if job in state["requeue"]:
                state["requeue"].remove(job)
            save_state(state)
            time.sleep(120)
            return


def main() -> None:
    state = load(STATE, {})
    for key, default in (("launched", {}), ("skipped", {}), ("done", {}), ("requeue", []),
                         ("stopping", {}), ("relaunched", {})):
        state.setdefault(key, default)
    log("scheduler started")
    orphan_seen: dict = {}
    waiting_logged: set = set()
    while True:
        try:
            jobs = load(JOBS, {"jobs": []})["jobs"]
            check_launched(state)
            for c, name in list(state["stopping"].items()):
                if runner_alive(c) is False and pipeline_alive(c) is False:
                    (C / f"STOP_{c}").unlink(missing_ok=True)
                    del state["stopping"][c]
                    save_state(state)
            active = active_runs()
            avail = mem_available()
            adopt_orphans(state, active, orphan_seen)
            watchdog(state, active, avail)
            next_job(state, jobs, active, avail, waiting_logged)
        except Exception as exc:  # keep scheduling; a crash here would strand the queue
            log(f"error: {exc!r}")
        time.sleep(POLL_S)


if __name__ == "__main__":
    main()
