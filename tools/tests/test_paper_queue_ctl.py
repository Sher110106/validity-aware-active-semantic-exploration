"""Tests for tools/live_policy/host/paper_queue_ctl.sh.

Each test builds a fake workspace and puts fake docker, pgrep, ps, uptime, last,
whoami, nvidia-smi, df, flock, setsid and systemd-run on PATH, so the script runs here as it
would on tyrone. The fakes keep their state in files under the test's tmp dir.
"""
import hashlib
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
HOST = TOOLS / "live_policy" / "host"
SCRIPT = HOST / "paper_queue_ctl.sh"
OLD_QUEUE_SHA = "46f4d0d30a9db26fe51c5d98faf6c75405b7c4e6461ddeae91919d99da656468"
NEW_QUEUE_SHA = "6ffb56015253a361e1c4baf082a17364ae43bb8b9d75bff92bb2d1551848e253"
ALL = ("dry:00853:a:3 e7:00853:42 e7:00871:42 apr:00853:a apr:00871:a apr:00853:b apr:00871:b "
       "e7:00853:43 e7:00871:43 e7:00853:44 e7:00871:44 e7:00853:45 e7:00871:45 e7:00853:46 e7:00871:46")
DRY = "apr/dryrun_apr_00853_a_3wp"
E7 = "frontier_seeds/e7_00853_s42_frontier_end"
CLEAN = "reboot   system boot  6.8.0 Mon Nov  9 10:05\nshutdown system down  6.8.0 Mon Nov  9 09:20\n"
CRASH = "reboot   system boot  6.8.0 Mon Nov  9 10:05\nreboot   system boot  6.8.0 Fri Nov  6 09:00\n"
PATCHES = [
    ("path >= 250 m;\n", "path >= 250 m (e7 only: §2b gives tours no path cap);\n"),
    ('    if awk "BEGIN{exit !($p >= 250)}"; then', '    if [ "$kind" = e7 ] && awk "BEGIN{exit !($p >= 250)}"; then'),
    ("zstd-compressed (reversible).\nW=", "zstd-compressed (reversible).\n"
     "# Jobs run with PYTHONUNBUFFERED=1: Python holds back stdout written to a file, and the explorer\n"
     '# logs "Exploration complete" and then idles, so without it the line never reaches the log.\nW='),
    ('  docker exec -d asp-noetic "${launch[@]}"', '  docker exec -d -e PYTHONUNBUFFERED=1 asp-noetic "${launch[@]}"'),
]

FAKES = {
    "whoami": 'echo "${FAKE_USER:-sher}"',
    "uptime": 'echo "${FAKE_BOOT:-2026-11-09 10:05:00}"',
    "ps": '[ "$*" = "-p 1 -o comm=" ] && echo "${FAKE_PID1:-systemd}"',
    "last": 'cat "$T/last.txt" 2>/dev/null',
    "nvidia-smi": 'echo "fake gpu line"',
    "df": 'echo "Avail"; echo " 27G"',
    "flock": '[ -z "${FAKE_LOCKED:-}" ]',
    # The old queue stays alive for as many checks as alive_countdown says.
    "pgrep": r'''case "$*" in *paper_queue*)
  if [ -s "$T/alive_countdown" ]; then n=$(cat "$T/alive_countdown"); if [ "$n" -gt 0 ]; then echo $((n-1)) > "$T/alive_countdown"; echo "998 bash paper_queue.sh old"; exit 0; fi; fi
  [ -e "$T/queue_alive" ] && { echo "999 bash paper_queue.sh"; exit 0; }; exit 1;; esac; exit 1''',
    "setsid": 'echo "$*" > "$T/setsid_args"; touch "$T/queue_alive"',
    # Drops its options and runs the command, as systemd-run --scope does.
    "systemd-run": '[ -n "${FAKE_NO_SYSTEMD_RUN:-}" ] && exit 1; while [ "${1#-}" != "$1" ]; do shift; done; exec "$@"',
    "docker": r'''
echo "$*" >> "$T/docker_calls"
case "$1" in
  info) [ -z "${FAKE_NO_DOCKER:-}" ];;
  inspect) [ -e "$T/running" ] && echo true || echo false;;
  start) touch "$T/running"; [ -e "$T/stopped" ] && [ -n "${FAKE_GPU_AFTER_RESTART:-}" ] && touch "$T/gpu_ok"; true;;
  stop) rm -f "$T/running"; touch "$T/stopped";;
  exec) shift 2
    case "$1" in
      nvidia-smi) [ -e "$T/gpu_ok" ];;
      ps) cat "$T/container_ps" 2>/dev/null;;
      bash) echo "$3" >> "$T/docker_bash"; case "$3" in *"command -v zstd"*) [ -z "${FAKE_NO_ZSTD:-}" ];; esac;;
    esac;;
esac''',
}


def line(kind, rest):
    return f"2026-11-09T16:00:00+05:30 {kind} {rest}"


def launched(name):
    return line("launch", f"{name} (mem 90 GB, disk 27 GB, GPU free 40000 MB)")


def finished(name, why="exploration_complete at 120.5 m"):
    return [line("finished", f"{name}: {why}"),
            line("converted", f"12 stages of {name} and compressed their DSG (disk 25 GB free)")]


STALLED = "stalled: no new stage for 20 min at 2.02 m (GPU free 42000 MB)"
DRY_PASSED = [launched(DRY), *finished(DRY, "exploration_complete at 9.1 m"), line("dry", "run passed: {'kept': 90}")]
DRY_STALLED = [launched(DRY), *finished(DRY, STALLED), line("dry", "run passed: {'kept': 90}")]
DONE_BY_STOP = [line("paper", "queue done")]


def original_queue_text():
    s = (HOST / "paper_queue.sh").read_text(encoding="utf-8")
    assert hashlib.sha256(s.encode()).hexdigest() == NEW_QUEUE_SHA
    for old, new in PATCHES:
        assert s.count(new) == 1
        s = s.replace(new, old)
    assert hashlib.sha256(s.encode()).hexdigest() == OLD_QUEUE_SHA
    return s


@pytest.fixture
def env(tmp_path):
    T = tmp_path
    W = T / "W"
    (W / "runs" / "apr").mkdir(parents=True)
    scripts = W / "catkin_ws/src/active_semantic_perception/exploration/scripts"
    scripts.mkdir(parents=True)
    for f in ("run_coverage_tour.sh", "stop_coverage_tour.sh", "run_frontier_seed.sh"):
        shutil.copy(HOST / f, W / f)
    for f in ("coverage_tour.py", "tour_waypoints.py"):
        shutil.copy(HOST / f, scripts / f)
    (W / "runs/apr/paper_queue.sh").write_text(original_queue_text(), encoding="utf-8")
    bindir = T / "bin"
    bindir.mkdir()
    for name, body in FAKES.items():
        p = bindir / name
        p.write_text("#!/bin/bash\n" + body + "\n")
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
    (T / "running").touch()
    (T / "gpu_ok").touch()
    (T / "last.txt").write_text(CLEAN)
    base = {"PATH": f"{bindir}:{os.environ['PATH']}", "T": str(T), "PAPER_W": str(W), "HOME": str(T),
            "PAPER_POLL_S": "0"}

    class Env:
        tmp, w = T, W
        q = W / "runs/apr"
        log = W / "runs/apr/paper_queue.log"

        def write_log(self, lines):
            self.log.write_text("\n".join(lines) + "\n")

        def run_log(self, name, text):
            d = W / "runs" / name / "logs"
            d.mkdir(parents=True, exist_ok=True)
            (d / "frontier_baseline.log").write_text(text)

        def tour_summary(self, name, complete):
            d = W / "runs" / name / "config"
            d.mkdir(parents=True, exist_ok=True)
            (d / "tour_summary.json").write_text(
                f'{{"complete": {"true" if complete else "false"}, "waypoints_listed": 3, "waypoints_reached": 3, "floor_y": 0.018}}')

        def arm_handover(self):
            (self.q / "STOP_PAPER").touch()
            (self.q / "HANDOVER_1109").touch()

        def queue_sha(self):
            return hashlib.sha256((self.q / "paper_queue.sh").read_bytes()).hexdigest()

        def run(self, mode="check", **extra):
            r = subprocess.run(["/bin/bash", str(SCRIPT), mode], env={**base, **extra},
                               capture_output=True, text=True, timeout=60)
            return r.returncode, r.stdout + r.stderr

        def verdict(self, out):
            return [l for l in out.splitlines() if l.startswith("VERDICT:")][-1]

        def jobs_left(self, out):
            return [l for l in out.splitlines() if l.startswith("-- jobs left:")][0].split(": ", 1)[1].split()

        def started_with(self):
            args = (T / "setsid_args").read_text().split()
            return args[args.index("paper_queue.sh") + 1:]

    return Env()


WAITING = [line("waiting", "for GPU: 1875 MB free")]


# --- after a reboot (restart mode) -------------------------------------------

def test_queue_alive_with_gpu_means_leave_it(env):
    env.write_log(WAITING)
    (env.tmp / "queue_alive").touch()
    code, out = env.run()
    assert code == 0 and env.verdict(out).startswith("VERDICT: ALIVE")


def test_queue_alive_without_container_gpu_is_urgent(env):
    env.write_log(WAITING)
    (env.tmp / "queue_alive").touch()
    (env.tmp / "gpu_ok").unlink()
    code, out = env.run()
    assert code == 1 and "URGENT" in env.verdict(out)


@pytest.mark.parametrize("extra, words", [
    ({"FAKE_USER": "otheruser"}, "not running as user sher"),
    ({"FAKE_PID1": "bash"}, "PID 1 is not systemd"),
    ({"FAKE_NO_DOCKER": "1"}, "cannot use docker"),
])
def test_wrong_place_or_user_stops(env, extra, words):
    env.write_log(WAITING)
    code, out = env.run(**extra)
    assert code == 1 and words in env.verdict(out)


def test_missing_log_stops(env):
    code, out = env.run()
    assert code == 1 and "missing or empty" in env.verdict(out)


def test_stop_file_stops(env):
    env.write_log(WAITING)
    (env.q / "STOP_PAPER").touch()
    code, out = env.run()
    assert code == 1 and "STOP_PAPER" in env.verdict(out)


def test_dead_queue_without_reboot_stops(env):
    env.write_log(WAITING)
    code, out = env.run(FAKE_BOOT="2026-11-04 08:00:00")
    assert code == 1 and "did not restart" in env.verdict(out)


def test_reboot_while_waiting_restarts_everything(env):
    env.write_log(WAITING)
    code, out = env.run()
    assert code == 0 and env.verdict(out).startswith("VERDICT: RESTART OK")
    assert env.jobs_left(out) == ALL.split()


def test_reboot_mid_dry_run_reruns_it(env):
    env.write_log(WAITING + [launched(DRY)])
    code, out = env.run()
    assert code == 0 and "-- interrupted: " + DRY in out
    assert env.jobs_left(out) == ALL.split()


def test_cut_off_run_after_unclean_shutdown_stops(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    (env.tmp / "last.txt").write_text(CRASH)
    code, out = env.run()
    assert code == 1 and "did not shut down cleanly" in env.verdict(out)


def test_cut_off_run_when_shutdown_unknown_stops(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    (env.tmp / "last.txt").unlink()
    code, out = env.run()
    assert code == 1 and "did not shut down cleanly" in env.verdict(out)


def test_restart_mid_e7_after_clean_shutdown(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    code, out = env.run("restart")
    assert code == 0 and env.verdict(out).startswith("VERDICT: RESTARTED"), out
    left = ALL.split()[1:]
    args = (env.tmp / "setsid_args").read_text().split()
    assert args[:5] == ["nohup", "systemd-run", "--user", "--scope", "--quiet"], args
    assert args[5].startswith("--unit=paper-queue-") and args[6:8] == ["bash", "paper_queue.sh"]
    assert args[8:] == left
    assert env.queue_sha() == NEW_QUEUE_SHA
    bash_cmds = (env.tmp / "docker_bash").read_text()
    assert f"/workspace/runs/{E7}/config/frontier_config.original.yaml" in bash_cmds
    assert "X95-lock" in bash_cmds
    assert env.log.read_text().splitlines()[-1].endswith("restarted (restart) with: " + " ".join(left))


def test_restart_twice_keeps_patched_queue(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    env.run("restart")
    (env.tmp / "queue_alive").unlink()
    code, out = env.run("restart")
    assert code == 0, out
    assert env.queue_sha() == NEW_QUEUE_SHA


def test_gave_up_on_gpu_restarts_without_reboot(env):
    env.write_log(WAITING + [line("gave", "up waiting for GPU after 72 h"), line("paper", "queue done")])
    code, out = env.run(FAKE_BOOT="2026-11-04 08:00:00")
    assert code == 0 and env.jobs_left(out) == ALL.split()


def test_queue_that_finished_stops(env):
    env.write_log(DRY_PASSED + DONE_BY_STOP)
    code, out = env.run()
    assert code == 1 and "ended by itself" in env.verdict(out)


def test_failed_dry_run_drops_tours(env):
    env.write_log([launched(DRY), *finished(DRY), line("dry", "run FAILED (exploration_complete at 9 m); apr jobs cancelled"),
                   launched(E7)])
    code, out = env.run()
    assert code == 0, out
    assert env.jobs_left(out) == [j for j in ALL.split() if not j.startswith(("apr:", "dry:"))]


def test_skipped_dry_run_stops(env):
    env.write_log([line("skip", f"{DRY}: skipped: mem 20 GB, disk 27 GB"),
                   line("dry", "run FAILED (skipped: mem 20 GB, disk 27 GB); apr jobs cancelled")])
    code, out = env.run()
    assert code == 1 and "skipped for memory or disk" in env.verdict(out)


def test_finished_but_not_converted_stops(env):
    env.write_log(DRY_PASSED + [launched(E7), line("finished", f"{E7}: exploration_complete at 120 m")])
    code, out = env.run()
    assert code == 1 and "conversion" in env.verdict(out)


def test_dry_run_without_verdict_stops(env):
    env.write_log([launched(DRY), *finished(DRY)])
    code, out = env.run()
    assert code == 1 and "no pass/fail" in env.verdict(out)


@pytest.mark.parametrize("name, why", [
    (E7, STALLED),
    (E7, "explorer process gone at 3 m"),
    ("apr/apr_00853_a", "path_cap_250m at 251 m"),
    ("apr/apr_00853_a", STALLED),
])
def test_bad_endings_stop(env, name, why):
    env.write_log(DRY_PASSED + [launched(name), *finished(name, why)])
    code, out = env.run()
    assert code == 1 and "ended badly" in env.verdict(out)


@pytest.mark.parametrize("why", ["path_cap_250m at 250.2 m", "wall_clock_4h at 200 m"])
def test_frontier_caps_are_normal(env, why):
    env.write_log(DRY_PASSED + [launched(E7), *finished(E7, why)])
    code, out = env.run()
    assert code == 0 and "e7:00853:42" not in env.jobs_left(out)


def test_tour_four_hour_cap_is_normal(env):
    tour = "apr/apr_00853_a"
    env.write_log(DRY_PASSED + [launched(E7), *finished(E7), launched(tour), *finished(tour, "wall_clock_4h at 180 m")])
    code, out = env.run()
    assert code == 0 and "apr:00853:a" not in env.jobs_left(out), out


def test_dry_run_four_hour_cap_is_still_bad(env):
    env.write_log([launched(DRY), *finished(DRY, "wall_clock_4h at 9 m"), line("dry", "run passed: {'kept': 90}")])
    code, out = env.run()
    assert code == 1 and "ended badly" in env.verdict(out)


def test_stall_after_exploration_complete_is_normal(env):
    env.write_log(DRY_PASSED + [launched(E7), *finished(E7, STALLED)])
    env.run_log(E7, "...\n[INFO] Exploration complete. No more frontiers found. Stopping.\n")
    code, out = env.run()
    assert code == 0 and "e7:00853:42" not in env.jobs_left(out), out


def test_tour_stall_with_complete_summary_is_normal(env):
    env.write_log(DRY_STALLED)
    env.tour_summary(DRY, True)
    code, out = env.run()
    assert code == 0, out


def test_tour_stall_with_incomplete_summary_stops(env):
    env.write_log(DRY_STALLED)
    env.tour_summary(DRY, False)
    code, out = env.run()
    assert code == 1 and "ended badly" in env.verdict(out)


def test_queue_skips_are_not_rerun(env):
    skip = "frontier_seeds/e7_00853_s45_frontier_end"
    env.write_log(DRY_PASSED + [line("skip", f"{skip}: skipped: mem 90 GB, disk 9 GB")])
    code, out = env.run()
    assert code == 0 and "e7:00853:45" not in env.jobs_left(out)


def test_changed_code_stops(env):
    p = env.w / "catkin_ws/src/active_semantic_perception/exploration/scripts/coverage_tour.py"
    p.write_text(p.read_text() + "\n# edited\n")
    env.write_log(WAITING)
    code, out = env.run()
    assert code == 1 and "coverage_tour.py is not the reviewed version" in env.verdict(out)


def test_live_run_in_container_stops(env):
    (env.tmp / "container_ps").write_text("Z    [roslaunch] <defunct>\nSl   python coverage_tour.py\n")
    env.write_log(WAITING)
    code, out = env.run()
    assert code == 1 and "still alive in the container" in env.verdict(out)


def test_zombie_roslaunch_is_ignored(env):
    (env.tmp / "container_ps").write_text("Z    [roslaunch] <defunct>\nS    sleep infinity\n")
    env.write_log(WAITING)
    code, out = env.run()
    assert code == 0, out


def test_restart_starts_container_and_fixes_gpu(env):
    (env.tmp / "running").unlink()
    (env.tmp / "gpu_ok").unlink()
    env.write_log(WAITING)
    code, out = env.run("restart", FAKE_GPU_AFTER_RESTART="1")
    assert code == 0, out
    calls = (env.tmp / "docker_calls").read_text().splitlines()
    assert "start asp-noetic" in calls and "stop asp-noetic" in calls


def test_restart_stops_when_gpu_never_returns(env):
    (env.tmp / "gpu_ok").unlink()
    env.write_log(WAITING)
    code, out = env.run("restart")
    assert code == 1 and "still cannot see the GPU" in env.verdict(out)
    assert not (env.tmp / "setsid_args").exists()


def test_check_changes_nothing(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    before = env.log.read_text()
    code, out = env.run("check")
    assert code == 0
    assert env.log.read_text() == before
    assert env.queue_sha() == OLD_QUEUE_SHA
    assert not (env.tmp / "docker_bash").exists() and not (env.tmp / "setsid_args").exists()


# --- swapping a running queue (handover mode) ---------------------------------

def test_handover_waits_for_old_queue_then_restarts(env):
    env.write_log(DRY_STALLED + [launched(E7), *finished(E7, STALLED)] + DONE_BY_STOP)
    env.tour_summary(DRY, True)
    env.run_log(E7, "[INFO] Exploration complete. No more frontiers found. Stopping.\n")
    env.arm_handover()
    (env.tmp / "alive_countdown").write_text("3")
    code, out = env.run("handover", FAKE_BOOT="2026-11-09 10:05:00")
    assert code == 0 and env.verdict(out).startswith("VERDICT: RESTARTED"), out
    assert "waiting for the running queue" in out
    assert env.started_with() == ALL.split()[2:]
    assert env.queue_sha() == NEW_QUEUE_SHA
    assert not (env.q / "STOP_PAPER").exists() and not (env.q / "HANDOVER_1109").exists()
    assert "restarted (handover) with: e7:00871:42" in env.log.read_text()


def test_handover_needs_both_files(env):
    env.write_log(DRY_PASSED + DONE_BY_STOP)
    (env.q / "STOP_PAPER").touch()
    code, out = env.run("handover")
    assert code == 1 and "needs both" in env.verdict(out)


def test_handover_refuses_second_watcher(env):
    env.write_log(DRY_PASSED + DONE_BY_STOP)
    env.arm_handover()
    code, out = env.run("handover", FAKE_LOCKED="1")
    assert code == 1 and "already running" in env.verdict(out)


def test_handover_without_queue_done_stops(env):
    env.write_log(DRY_PASSED + [launched(E7), *finished(E7)])
    env.arm_handover()
    code, out = env.run("handover")
    assert code == 1 and "paper queue done" in env.verdict(out)


def test_handover_with_unfinished_job_stops(env):
    env.write_log(DRY_PASSED + [launched(E7)] + DONE_BY_STOP)
    env.arm_handover()
    code, out = env.run("handover")
    assert code == 1 and "never finished" in env.verdict(out)


def test_handover_with_real_stall_stops(env):
    env.write_log(DRY_STALLED + [launched(E7), *finished(E7, STALLED)] + DONE_BY_STOP)
    env.tour_summary(DRY, True)
    env.arm_handover()
    code, out = env.run("handover")
    assert code == 1 and "ended badly" in env.verdict(out)
    assert (env.q / "STOP_PAPER").exists()


def test_handover_ignores_reboot_rule(env):
    env.write_log(DRY_STALLED + DONE_BY_STOP)
    env.tour_summary(DRY, True)
    env.arm_handover()
    code, out = env.run("handover", FAKE_BOOT="2026-11-04 08:00:00")
    assert code == 0 and env.started_with() == ALL.split()[1:], out


def test_restart_refuses_while_handover_pending(env):
    env.write_log(DRY_PASSED + DONE_BY_STOP)
    env.arm_handover()
    code, out = env.run("restart")
    assert code == 1 and "handover is pending" in env.verdict(out)


# --- status ---------------------------------------------------------------------

def test_status_flags_bad_ending_after_restart(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    env.run("restart")
    with env.log.open("a") as f:
        f.write("\n".join([launched(E7), *finished(E7, "crashed at 5 m: x")]) + "\n")
    code, out = env.run("status")
    assert code == 1 and "STOP THE QUEUE" in env.verdict(out)


def test_status_ok_while_running(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    env.run("restart")
    code, out = env.run("status")
    assert code == 0 and env.verdict(out) == "VERDICT: OK"


def test_status_during_handover_wait(env):
    env.write_log(DRY_STALLED + [launched(E7)])
    env.tour_summary(DRY, True)
    env.arm_handover()
    (env.tmp / "queue_alive").touch()
    code, out = env.run("status", FAKE_LOCKED="1")
    assert code == 0 and "handover: pending" in out and env.verdict(out) == "VERDICT: OK"


def test_status_stops_when_handover_has_no_watcher(env):
    env.write_log(DRY_STALLED + [launched(E7)])
    env.tour_summary(DRY, True)
    env.arm_handover()
    (env.tmp / "queue_alive").touch()
    code, out = env.run("status")
    assert code == 1 and "no watcher" in env.verdict(out)


def test_status_reports_skips_and_keeps_going(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    env.run("restart")
    with env.log.open("a") as f:
        f.write("\n".join([*finished(E7), line("skip", "frontier_seeds/e7_00871_s42_frontier_end: skipped: mem 20 GB, disk 30 GB")]) + "\n")
    code, out = env.run("status")
    assert code == 0 and env.verdict(out).startswith("VERDICT: REPORT"), out
    assert "e7_00871_s42_frontier_end: skipped" in out


def test_status_after_gpu_give_up_is_not_done(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    env.run("restart")
    (env.tmp / "queue_alive").unlink()
    with env.log.open("a") as f:
        f.write("\n".join([*finished(E7), line("gave", "up waiting for GPU after 72 h"), line("paper", "queue done")]) + "\n")
    code, out = env.run("status")
    assert code == 1 and "gave up waiting for the GPU" in env.verdict(out)


def test_status_done_names_skips(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    env.run("restart")
    (env.tmp / "queue_alive").unlink()
    with env.log.open("a") as f:
        f.write("\n".join([*finished(E7), line("skip", "frontier_seeds/e7_00853_s46_frontier_end: skipped: mem 90 GB, disk 9 GB"),
                            line("paper", "queue done")]) + "\n")
    code, out = env.run("status")
    assert code == 0 and "skipped the jobs above" in env.verdict(out)


def test_restart_stops_without_zstd_in_container(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    code, out = env.run("restart", FAKE_NO_ZSTD="1")
    assert code == 1 and "no zstd" in env.verdict(out)
    assert not (env.tmp / "setsid_args").exists()


def test_restart_without_systemd_user_manager_warns(env):
    env.write_log(DRY_PASSED + [launched(E7)])
    code, out = env.run("restart", FAKE_NO_SYSTEMD_RUN="1")
    assert code == 0 and "WARNING: no systemd user manager" in out
    assert (env.tmp / "setsid_args").read_text().split()[:3] == ["nohup", "bash", "paper_queue.sh"]
