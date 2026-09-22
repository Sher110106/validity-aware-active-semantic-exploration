# ASP Matrix Supervisor Specification

**Scope note (2026-09-16):** the experiment's final size was descoped for
cost/time to 3 scenes × 1 seed (see `IMPLEMENTATION_PLAN.md` section 0) —
this spec's "4-scene × 3-seed" text below describes the matrix as planned
when this supervisor was built, and is left as the historical record rather
than silently rewritten. The supervisor's own behavior does not depend on
the count: it sequences whatever `matrix_plan.json`/`build_seed_major_plan()`
enumerates and now stops early via `CONTROL.json`'s `max_completed_runs: 3`.

## Goal

~~Run the 4-scene × 3-seed, 120 m ASP matrix sequentially~~ Run the ASP
matrix sequentially, 120 m per run, without relying on an
agent session or SSH connection for safety. A host-resident supervisor must
adopt the currently running `scene00069_seed42_matrix120m` process without
restarting it, stop every run at the first completed checkpoint at or beyond
120 m, and launch the next run only after validating and cleaning up the
previous one.

## User-approved policy

- Queue order is seed-major: all four scenes for seed 42, then seed 43, then
  seed 44.
- Allow one automatic full-run retry after an unambiguous failure (two total
  attempts per scene/seed). The current 00069/42 run is already attempt 2
  because its first attempt was lost to a host reboot.
- Future runs use a 3,000-call hard cap. The adopted run keeps its existing
  2,500-call environment and must not be restarted merely to change the cap.
- Poll every 60 seconds.
- Do not launch a new run when free disk is below 25 GB.
- An ambiguous 30-minute stall pauses queue automation for human review; it
  must not kill the live process.

## Architecture

- Add a standard-library-only Python supervisor outside the pinned author
  checkout under `tools/matrix_supervisor/`.
- Run it on the tyrone host, not inside Docker, so it can inspect and repair
  the `asp-noetic` container.
- Install it as a user systemd service with restart-on-failure and enable user
  lingering so it starts after a host reboot without an SSH login.
- Use an exclusive `flock` lock so only one supervisor can act.
- Keep the immutable queue and scene paths in `matrix_plan.json`.
- Keep human-editable operational knobs in `CONTROL.json`.
- Write current state atomically to `runs/matrix_supervisor/state.json`, a
  concise status view to `status.json`, and append events to `events.jsonl`.

## Safety behavior

1. Never edit files in the pinned author checkout.
2. Never overwrite or merge a failed attempt. Rename it with an attempt,
   reason, and timestamp before a retry.
3. Never run two exploration pipelines or ROS stacks concurrently.
4. Treat Docker `restart=unless-stopped` only as container recovery; do not
   mistake the restarted `sleep infinity` container for a resumed experiment.
5. Check host GPU first. If host GPU works but container GPU fails twice,
   perform one full Docker stop/start cycle and verify GPU access again.
6. If the host GPU is unhealthy, pause and request human intervention.
7. On a clear pre-120 m failure (missing pipeline, dead container, hard-cap
   loop), retry only when the attempt budget permits; otherwise pause.
8. On an ambiguous stall, record and pause automation without killing.
9. At path ≥120 m, send the pipeline's normal double-Escape shutdown, wait for
   it to exit, then clean the ROS/Xvfb processes. Escalate to targeted signals
   only after a timeout.
10. Validate path, required configuration/artifacts, non-empty graph outputs,
    and absence of an uncaptured traceback before marking a run complete.
11. Never launch the next run below the disk floor or while cleanup is
    incomplete.
12. The external 30-minute agent check is reporting only, not a safety
    mechanism.

## Public interface

```text
python3 tools/matrix_supervisor/supervisor.py --check
python3 tools/matrix_supervisor/supervisor.py --once [--dry-run]
python3 tools/matrix_supervisor/supervisor.py --daemon
```

- `--check` is read-only and exits nonzero only for an unsafe/blocked state.
- `--once --dry-run` prints proposed actions and changes no process or file
  except optional diagnostic stdout.
- `--once` performs one reconciliation cycle.
- `--daemon` reconciles at the configured interval.

## Non-goals

- No true mid-run resume or checkpoint restoration.
- No changes to `exploration_pipeline.py` or other pinned research code.
- No silent repair of malformed scientific outputs.
- No concurrent matrix runs on the shared GPU.
- No deletion of failed or superseded evidence.

## Scorecard

- Primary checklist: all supervisor behavior tests pass and remote dry-run
  reports adoption/no-op for the healthy current run.
- Passing threshold: 100% focused tests; no duplicate process; service active;
  lock held by one daemon; status reports the same path/call counter as raw
  artifacts.
- Regression checks: existing offline test suite remains green; current run's
  PID/start time/path do not change during deployment.
- Stop condition: service survives a controlled restart, re-adopts the current
  run without launching another, and the next scheduled cycle is visible in
  status.

## Done when

1. `python3 -m unittest discover -s tools/matrix_supervisor/tests -v` passes.
2. Existing offline tests pass unchanged.
3. Remote `--check` reports exactly one healthy pipeline and correct GPU,
   disk, path, call count, and attempt number.
4. Remote `--once --dry-run` proposes no restart/launch for the active run.
5. `systemctl --user is-active asp-matrix-supervisor.service` returns
   `active`, and `loginctl show-user sher -p Linger` reports `yes`.
6. Restarting only the supervisor service does not change the active
   exploration PID or stage directory.
7. `status.json` and `events.jsonl` identify run 1 as attempt 2 and expose the
   next wakeup, thresholds, and any blocker.
8. No file under the pinned author checkout changes during installation.
