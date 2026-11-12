#!/usr/bin/env python3
"""Host-side queue runner for the 2026-10-28 live campaign.

Runs the queue's runs one after another in one container: cleans up stale
processes, launches tools/live_policy/run_live_run.sh, watches the run, and
stops it with the author's double-Escape path when the path budget is
reached, the per-run cost cap trips, or the run stalls. One runner per
container; several runners may share the campaign cost cap.

Usage:
    nohup setsid python3 live_runner.py --container asp-noetic \
        --queue queue_a.json --display 99 > runner_a.out 2>&1 &

Control files in the campaign directory (append _<container> to target one runner):
    PAUSE  - finish the current run, then start no new one
    STOP   - stop the current run now (graceful), then exit
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

HOST_WS = Path("/home/sher/active-semantic-perception-workspace")
CAMPAIGN = HOST_WS / "runs" / "live_campaign"
CONTAINER_CAMPAIGN = "/workspace/runs/live_campaign"
LAUNCHER = "/workspace/tools/live_policy/run_live_run.sh"
CONFIG_REL = "catkin_ws/src/active_semantic_perception/exploration/config/pipeline_config.yaml"
PIPELINE_PATTERN = "run_pipeline_with_policy.py"
CLEAN_PATTERNS = (
    PIPELINE_PATTERN,
    "exploration_pipeline.py",
    "roslaunch",
    "rosmaster",
    "rosout",
    "hydra_ros_node",
    "clio_ros/app/task_server",
    "segmenter",
    "Xvfb",
)
SCENES = {
    "00069": ("/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/train/00069-Y8Y6ukxGMvn/Y8Y6ukxGMvn.basis.glb", 69),
    "00573": ("/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/train/00573-1zDbEdygBeW/1zDbEdygBeW.basis.glb", 573),
    "00853": ("/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/val/00853-5cdEh9F2hJL/5cdEh9F2hJL.basis.glb", 853),
    "00871": ("/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/val/00871-VBzV5z6i1WS/VBzV5z6i1WS.basis.glb", 871),
}
POLL_S = 30
STALL_S = 40 * 60
GRACEFUL_S = 180
# Loop guards: a normal stage makes 30-80 LLM calls (8 members x 4-10 turns).
MAX_CALLS_PER_STAGE = 400
# Shared host: six runs plus leftovers exhausted 123 GB on 2026-10-28 and the
# kernel OOM-killed other users' processes. Launch only with room to spare;
# stop our own run before the host runs out.
MIN_AVAILABLE_GB_TO_LAUNCH = 30.0
MIN_AVAILABLE_GB_RUNNING = 6.0
MAX_PLANNING_ERRORS = 5
# Quality gates (pre-registered exclusions): every call served by DeepInfra
# with the 1017 model; at most 50% of ensemble members dropped over a run.
REQUIRED_PROVIDER = "DeepInfra"
REQUIRED_MODEL_TAG = "deepseek-v4.1-flash-1017"
# Live stop only for a broken arm; the reported drop rate is a covariate
# (pre-registration: exclusion above 50% run-mean dropped members).
MAX_DROPPED_FRACTION = 0.50
MIN_STAGES_FOR_DROP_GATE = 5
ENSEMBLE_SLOTS = 8


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


class Runner:
    def __init__(self, container: str, display: int, campaign_cap: float, catkin_host: Path):
        self.container = container
        self.display = display
        self.campaign_cap = campaign_cap
        self.catkin_host = catkin_host
        self.log_path = CAMPAIGN / f"runner_{container}.log"
        self.status_path = CAMPAIGN / f"status_{container}.json"
        self.status: dict = {"container": container, "display": display, "runs": {}}

    def log(self, msg: str) -> None:
        line = f"{now_iso()} [{self.container}] {msg}"
        print(line, flush=True)
        with open(self.log_path, "a") as f:
            f.write(line + "\n")

    def save(self) -> None:
        self.status["updated"] = now_iso()
        tmp = self.status_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.status, indent=2, sort_keys=True) + "\n")
        tmp.replace(self.status_path)

    def dexec(self, *args: str, timeout: int = 60, detach: bool = False) -> subprocess.CompletedProcess:
        cmd = ["docker", "exec"] + (["-d"] if detach else []) + [self.container, *args]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(cmd, 124, "", "timeout")

    def pids(self, pattern: str) -> Optional[list[int]]:
        """Matching PIDs; None when the check itself failed (docker exec timed
        out under load), which must never be read as 'no process'."""
        r = self.dexec("pgrep", "-f", pattern)
        if r.returncode == 0:
            return [int(p) for p in r.stdout.split()]
        if r.returncode == 1:
            return []
        return None

    def confirmed_gone(self, pattern: str, checks: int = 3) -> bool:
        """True only after `checks` successful, empty pgrep results in a row."""
        for i in range(checks):
            if self.pids(pattern) != []:
                return False
            if i < checks - 1:
                time.sleep(5)
        return True

    @staticmethod
    def mem_available_gb() -> float:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1048576
        return float("inf")

    def kill_all(self) -> None:
        """Between runs nothing but PID 1 should live in the container. A
        pattern list missed the detector, nvblox, nodelets and, worse, the
        pipeline's spawn workers, which kept making paid LLM calls after a
        stop (2026-10-28), so kill everything except PID 1 and this shell."""
        self.dexec("bash", "-c", "for p in $(ps -eo pid=); do "
                   "[ \"$p\" -ne 1 ] && [ \"$p\" -ne $$ ] && kill -9 \"$p\" 2>/dev/null; done; true")
        time.sleep(3)
        self.dexec("rm", "-f", f"/tmp/.X{self.display}-lock", f"/tmp/.X11-unix/X{self.display}")

    def restore_config(self, pristine: Path) -> None:
        target = self.catkin_host / CONFIG_REL
        if pristine.exists():
            r = self.dexec("cp", f"/workspace/runs/live_campaign/{pristine.name}", f"/workspace/{CONFIG_REL}")
            if r.returncode != 0:
                self.log(f"WARNING config restore failed: {r.stderr.strip()} (target {target})")

    @staticmethod
    def max_path(run: Path) -> float:
        best = 0.0
        for nav in run.glob("stages/*/navigation_stats.json"):
            try:
                best = max(best, float(json.loads(nav.read_text())["total_path_length_meters"]))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return best

    @staticmethod
    def stage_count(run: Path) -> int:
        return len([p for p in run.glob("stages/*") if p.is_dir()])

    @staticmethod
    def provider_violations(run: Path) -> list:
        bad = []
        try:
            with open(run / "prompts" / "usage.jsonl") as f:
                for line in f:
                    r = json.loads(line)
                    # A 200 with no provider is an error body (nothing was served);
                    # only a completion served elsewhere breaks the pin.
                    if r.get("status") == 200 and r.get("provider") is not None and (
                            r.get("provider") != REQUIRED_PROVIDER
                            or REQUIRED_MODEL_TAG not in (r.get("model") or "")):
                        bad.append({"provider": r.get("provider"), "model": r.get("model"), "id": r.get("id")})
        except (OSError, ValueError):
            pass
        return bad

    @staticmethod
    def member_stats(run: Path) -> tuple[int, int]:
        """(member slots, completions available) over the run, counting only
        the tracks present at each step: the pipeline sometimes hands over one
        tracked graph instead of two, which is not a dropped member."""
        slots = available = 0
        for f in run.glob("stages/*/live_policy.jsonl"):
            try:
                for line in f.read_text().splitlines():
                    tracks = json.loads(line).get("tracks", {}).values()
                    slots += ENSEMBLE_SLOTS // 2 * len(tracks)
                    available += sum(t.get("available", 0) for t in tracks)
            except (OSError, ValueError):
                continue
        return slots, available

    @staticmethod
    def calls(run: Path) -> int:
        try:
            with open(run / "prompts" / "usage.jsonl") as f:
                return sum(1 for _ in f)
        except OSError:
            return 0

    @staticmethod
    def cost(run: Path) -> float:
        try:
            return float((run / "prompts" / "_cost_usd").read_text().strip())
        except (OSError, ValueError):
            return 0.0

    @staticmethod
    def last_activity(run: Path) -> float:
        times = [run.stat().st_mtime] if run.exists() else [0.0]
        for p in (run / "prompts" / "usage.jsonl", run / "logs" / "exploration_pipeline.log"):
            try:
                times.append(p.stat().st_mtime)
            except OSError:
                pass
        times += [p.stat().st_mtime for p in run.glob("stages/*") if p.is_dir()]
        return max(times)

    @staticmethod
    def log_flags(run: Path) -> dict:
        try:
            text = (run / "logs" / "exploration_pipeline.log").read_text(errors="replace")
        except OSError:
            text = ""
        return {
            "policy_failed": "[live_policy] FAILED" in text,
            "call_cap": "ASP_LLM_MAX_CALLS hard cap" in text,
            "planning_errors": text.count("Error during planning"),
        }

    def campaign_committed(self) -> float:
        """Spent over all run dirs plus the unspent cap of every run that is
        still active (marker files written under the launch lock)."""
        spent = sum(self.cost(p) for p in CAMPAIGN.iterdir() if p.is_dir())
        held = 0.0
        for marker in CAMPAIGN.glob(".active_*"):
            try:
                info = json.loads(marker.read_text())
                held += max(0.0, float(info["max_cost_usd"]) - self.cost(CAMPAIGN / info["name"]))
            except (OSError, ValueError, KeyError):
                continue
        return spent + held

    def exclude(self, run: Path, reason: str, detail) -> None:
        # Run dirs are root-owned (written from the container); the campaign
        # dir is ours.
        (CAMPAIGN / f"EXCLUDED_{run.name}.json").write_text(
            json.dumps({"reason": reason, "detail": detail, "at": now_iso()}, indent=2) + "\n")

    def _dropped_gate(self, run: Path) -> bool:
        slots, available = self.member_stats(run)
        if slots < MIN_STAGES_FOR_DROP_GATE * ENSEMBLE_SLOTS:
            return False
        return 1 - available / slots > MAX_DROPPED_FRACTION

    def graceful_stop(self) -> str:
        for _ in range(2):
            self.dexec("env", f"DISPLAY=:{self.display}", "xdotool", "key", "Escape")
            time.sleep(0.25)
        deadline = time.time() + GRACEFUL_S
        while time.time() < deadline:
            if self.pids(PIPELINE_PATTERN) == []:
                return "escape"
            time.sleep(5)
        for sig in ("-TERM", "-KILL"):
            pids = self.pids(PIPELINE_PATTERN)
            if pids == []:
                break
            if pids is None:
                continue
            self.dexec("kill", sig, *map(str, pids))
            time.sleep(10)
        return "killed"

    def stop_workers(self) -> None:
        """Spawn workers outlive a stopped pipeline and keep calling the LLM."""
        self.dexec("pkill", "-9", "-f", "multiprocessing.spawn")

    def run_one(self, spec: dict, pristine: Path, adopt: bool = False) -> dict:
        name = spec["name"]
        run = CAMPAIGN / name
        rec = {"spec": spec, "started": now_iso()}
        if adopt:
            # Take over monitoring of a run an earlier runner launched.
            if not run.exists() or not self.pids(PIPELINE_PATTERN):
                rec.update(outcome="adopt_failed_not_running")
                return rec
            rec["adopted"] = now_iso()
            self.log(f"adopted {name}")
            t0 = (run / "config").stat().st_mtime
            try:
                return self._monitor(spec, pristine, rec, run, t0)
            finally:
                (CAMPAIGN / f".active_{name}").unlink(missing_ok=True)
        if run.exists():
            rec.update(outcome="skipped_exists")
            return rec
        import fcntl

        paid = spec["policy"] not in ("observed_only", "placebo", "oracle_visible")
        marker = CAMPAIGN / f".active_{name}"
        with open(CAMPAIGN / ".launch.lock", "a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            committed = self.campaign_committed()
            if paid and committed + spec["max_cost_usd"] > self.campaign_cap:
                rec.update(outcome="skipped_campaign_cap", campaign_committed=committed)
                return rec
            if self.mem_available_gb() < MIN_AVAILABLE_GB_TO_LAUNCH:
                rec.update(outcome="skipped_host_memory", mem_available_gb=round(self.mem_available_gb(), 1))
                return rec
            if paid:
                marker.write_text(json.dumps({"name": name, "max_cost_usd": spec["max_cost_usd"]}))
        try:
            return self._run_launched(spec, pristine, rec, run)
        finally:
            marker.unlink(missing_ok=True)

    def _run_launched(self, spec: dict, pristine: Path, rec: dict, run: Path) -> dict:
        name = spec["name"]
        paid = spec["policy"] not in ("observed_only", "placebo", "oracle_visible")
        scene_id, scene_number = SCENES[spec["scene"]]
        self.kill_all()
        self.restore_config(pristine)
        args = [LAUNCHER, scene_id, str(scene_number), name, str(self.display), spec["policy"],
                str(spec["seed"]), str(spec["max_cost_usd"]), str(spec.get("no_llm_delay_schedule", "0"))]
        # Optional per-job environment (plan step 8: ASP_DSG_QUIESCENT_S), exported before launch.
        exports = "".join(f"export {k}={shlex.quote(str(v))}; " for k, v in spec.get("env", {}).items()
                          if re.fullmatch(r"ASP_[A-Z0-9_]+", k))
        cmd = exports + "exec " + " ".join(shlex.quote(a) for a in args) + f" >> {CONTAINER_CAMPAIGN}/launcher_{name}.log 2>&1"
        r = self.dexec("bash", "-lc", cmd, detach=True)
        if r.returncode != 0:
            rec.update(outcome="launch_failed", error=r.stderr.strip())
            return rec
        self.log(f"launched {name}: {spec}")
        t0 = time.time()
        time.sleep(90)
        return self._monitor(spec, pristine, rec, run, t0)

    def _monitor(self, spec: dict, pristine: Path, rec: dict, run: Path, t0: float) -> dict:
        name = spec["name"]
        paid = spec["policy"] not in ("observed_only", "placebo", "oracle_visible")
        outcome = None
        stage_seen, calls_at_stage = -1, 0
        while outcome is None:
            stages_now, calls_now = self.stage_count(run), self.calls(run)
            if stages_now != stage_seen:
                stage_seen, calls_at_stage = stages_now, calls_now
            path_m, cost_usd = self.max_path(run), self.cost(run)
            flags = self.log_flags(run)
            rec.update(path_m=path_m, cost_usd=round(cost_usd, 6), stages=stages_now, calls=calls_now,
                       elapsed_h=round((time.time() - t0) / 3600, 3), flags=flags)
            self.status["runs"][name] = rec
            self.save()
            if (CAMPAIGN / "STOP").exists() or (CAMPAIGN / f"STOP_{self.container}").exists():
                outcome = "stopped_by_control_file"
            elif path_m >= spec["target_m"]:
                outcome = "target_reached"
            elif (run / "prompts" / "_cost_cap_reached").exists():
                outcome = "cost_cap"
            elif flags["policy_failed"]:
                outcome = "policy_failed"
            elif flags["call_cap"]:
                outcome = "call_cap"
            elif self.mem_available_gb() < MIN_AVAILABLE_GB_RUNNING:
                outcome = "host_memory_low"
            elif paid and self.provider_violations(run):
                outcome = "provider_violation"
                self.exclude(run, outcome, self.provider_violations(run)[:5])
            elif paid and self._dropped_gate(run):
                outcome = "dropped_members"
                self.exclude(run, outcome, dict(zip(("slots", "available"), self.member_stats(run))))
            elif calls_now - calls_at_stage > MAX_CALLS_PER_STAGE:
                outcome = "call_loop"
            elif flags["planning_errors"] > MAX_PLANNING_ERRORS:
                outcome = "planning_error_loop"
            elif self.confirmed_gone(PIPELINE_PATTERN):
                outcome = "pipeline_exited"
            elif time.time() - self.last_activity(run) > STALL_S:
                outcome = "stalled"
            elif time.time() - t0 > spec.get("max_hours", 8) * 3600:
                outcome = "wall_clock_limit"
            else:
                time.sleep(POLL_S)
        self.log(f"{name}: {outcome} at {rec.get('path_m')} m, ${rec.get('cost_usd')}")
        rec["stop_method"] = "already_exited" if self.pids(PIPELINE_PATTERN) == [] else self.graceful_stop()
        self.stop_workers()
        time.sleep(5)
        self.kill_all()
        self.restore_config(pristine)
        rec.update(outcome=outcome, finished=now_iso(), path_m=self.max_path(run),
                   cost_usd=round(self.cost(run), 6), stages=self.stage_count(run))
        return rec

    def run_queue(self, runs: list[dict], adopt: bool = False) -> None:
        pristine = CAMPAIGN / f"pipeline_config.pristine.{self.container}.yaml"
        if not pristine.exists():
            r = self.dexec("cp", f"/workspace/{CONFIG_REL}", f"{CONTAINER_CAMPAIGN}/{pristine.name}")
            if r.returncode != 0:
                self.log(f"cannot save pristine config: {r.stderr.strip()}")
                sys.exit(2)
        self.status["queue"] = [r["name"] for r in runs]
        self.save()
        for spec in runs:
            if any((CAMPAIGN / f).exists() for f in ("PAUSE", "STOP", f"PAUSE_{self.container}", f"STOP_{self.container}")):
                self.log("PAUSE/STOP present; not starting more runs")
                break
            rec = self.run_one(spec, pristine, adopt=adopt and spec is runs[0])
            self.status["runs"][spec["name"]] = rec
            self.save()
            self.log(f"finished {spec['name']}: {rec.get('outcome')}")
        self.status["done"] = now_iso()
        self.save()
        self.log("queue finished")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", required=True)
    ap.add_argument("--queue", required=True, type=Path)
    ap.add_argument("--display", type=int, default=99)
    ap.add_argument("--campaign-cap", type=float, required=True,
                    help="USD over all run dirs plus unspent caps of active runs (shared by all runners)")
    ap.add_argument("--catkin-host", type=Path, default=HOST_WS / "catkin_ws")
    ap.add_argument("--adopt", action="store_true", help="monitor the queue's first run, already launched by an earlier runner")
    a = ap.parse_args()
    CAMPAIGN.mkdir(parents=True, exist_ok=True)
    runs = json.loads(a.queue.read_text())["runs"]
    for spec in runs:
        if spec["scene"] not in SCENES or spec["policy"] not in ("official", "filter_only", "unanimity", "observed_only", "placebo", "oracle_visible"):
            raise SystemExit(f"bad spec {spec}")
    Runner(a.container, a.display, a.campaign_cap, a.catkin_host).run_queue(runs, adopt=a.adopt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
