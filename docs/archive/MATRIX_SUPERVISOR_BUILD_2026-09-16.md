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
- Run it on the project host, not inside Docker, so it can inspect and repair
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

---

The sections below were merged on 2026-11-12 from five sibling files of this folder (CONTROL, GOAL, PLAN, NOTES, ATTEMPTS), which are removed from the tree and remain in git history. Cross-references to them are now section references. Where the originals named the host machine or its workspace path, this text says "the host" and "<host workspace>". Nothing else in the Notes and Attempts log sections is changed.

## Governance

Merged from CONTROL.md. This is the build governance. Runtime knobs live in `tools/matrix_supervisor/CONTROL.json`.

### Status contract

- Implementation plan: section "Deployment state" below.
- Attempt log: section "Attempts log" below.
- Durable notes: section "Notes" below.
- Runtime status after deployment: `runs/matrix_supervisor/status.json` on the host.
- Runtime event log: `runs/matrix_supervisor/events.jsonl` on the host.

### Priorities

- Primary: resource safety and evidence preservation.
- Secondary: unattended throughput.

### Scope

- Allowed: `tools/matrix_supervisor/**`, supervisor documentation, user-level service files, and supervisor runtime state.
- Protected: pinned author checkout, existing run artifacts, credentials, unrelated local changes.

### Resource policy

Same as "User-approved policy" above:

- One GPU experiment at a time.
- 60-second checks.
- 25 GB free-disk launch floor.
- 120 m path target.
- 3,000 calls for future runs.
- One automatic retry after an initial failure.
- Ambiguous 30-minute stalls pause for review without killing.

### Approval gates

Explicit approval is required for pinned-code changes, deletion, retry-limit increases, lower disk floors, concurrent runs, or changes to scientific parameters.

## Build order and rules

Merged from GOAL.md, the agent goal prompt for this build. Its constraints and eight done-when items repeat "User-approved policy" and "Done when" above. What it adds:

Goal, as written: implement and deploy a host-resident supervisor for the ASP 12-run matrix that adopts the current run without restarting it, enforces the 120 m budget, safely sequences the remaining runs, and recovers from clear host or container failures within the user-approved resource limits. The scope note at the top of this file says the matrix was later cut to 3 runs.

Context it gave: read this specification, `IMPLEMENTATION_PLAN.md` and the latest entries in `tyrone_mirror/DEVIATIONS.md`. The Docker container is `asp-noetic`. The pinned author checkout is under `catkin_ws/src/active_semantic_perception` and is protected. Reuse the `run_llm_pipeline_scene.sh` launch contract, but do not assume it provides monitoring, cleanup, queueing or restart safety.

Build order, in vertical TDD slices:

1. Queue and adoption.
2. Health snapshot and read-only status.
3. Budget stop policy.
4. Retry and archive policy.
5. GPU repair policy.
6. Launch and cleanup.
7. Daemon lock and control reload.
8. Service installation.

Deploy only after local tests. Run the remote check and the dry-run before enabling actions. Enable the service, watch at least two cycles, restart only the supervisor, and verify the experiment is untouched.

Rules:

- Standard library only. Do not edit pinned research code. Do not restart the healthy current run.
- Keep one active run, one supervisor lock, one retry after the first attempt, a 3,000-call cap for future runs, a 25 GB disk floor, a 60-second poll, and pause-without-kill for ambiguous 30-minute stalls.
- Keep every failed attempt under a unique archive name.
- Docker GPU self-healing runs only after host GPU health succeeds and two container GPU checks fail.
- Runtime state lives under `runs/matrix_supervisor/` on the host, not in chat memory.
- Keep the plan (section "Deployment state"), the attempt log (section "Attempts log") and the notes (section "Notes") current after each meaningful test or deployment.
- A human may pause launches and retries without disabling budget monitoring. `CONTROL.json` is re-read every cycle. Strategic changes, destructive cleanup, retry-limit increases, disk-floor cuts and pinned-code edits need explicit approval.
- Verification loop: run focused tests after each slice, then all supervisor tests, compileall, the offline tests, remote `--check`, remote `--once --dry-run`, systemd status, and a before/after comparison of exploration PID, start time, path and pinned-checkout hashes. **On any mismatch, disable the supervisor service without touching the experiment and investigate.**
- Do not paper over failures, widen scope, delete evidence, expose credentials or alter a healthy live run.

Scorecard: focused behavior tests pass; the live dry-run returns adoption or no-op; the deployed service is active and singular; status agrees with raw path and call artifacts. Threshold 100%. Stop when all "Done when" checks above pass.

## Deployment state

Merged from PLAN.md. Its phase checklist (audit; freeze policy; queue and adoption; safety transitions; local and remote dry-run; install service; two healthy cycles with unchanged PID) is the build order above, all ticked. Open decisions: none. Any need to touch pinned code or raise retry limits returns to the user.

State at deployment, 2026-09-16:

- User service: `asp-matrix-supervisor.service` active and enabled on the host.
- Persistence: `Linger=yes`; the service does not depend on an SSH session.
- Active experiment: `scene00069_seed42_matrix120m`, attempt 2, adopted without restart.
- Pipeline identity: PID 933 and `ASP_LLM_LOG_DIR` both match the expected run.
- Runtime truth: `<host workspace>/runs/matrix_supervisor/`.

## Notes

Merged verbatim from NOTES.md (host name and workspace path generalised).

### Chronological notes

- 2026-09-16 10:46 IST: Active run was healthy, with working container GPU, ROS stack, and pipeline.
- 2026-09-16 10:49 IST: Run reached 35.1 m; observed call/path fits forecast roughly 2,067–2,265 calls at 120 m, so the current 2,500 cap is likely sufficient but not generous.
- 2026-09-16 10:50 IST: `restart=unless-stopped` restarts only the container's `sleep infinity`; Docker-exec children do not resume.
- 2026-09-16 10:51 IST: No crontab, matrix systemd timer/service, tmux queue, or active path-budget watcher exists. Only run 1 is launched.
- 2026-09-16 11:10 IST: `asp-matrix-supervisor.service` was enabled under the user manager and user lingering was enabled, making supervision independent of SSH sessions.
- 2026-09-16 11:22 IST: All four frozen scene paths were verified readable. The active run manifest confirms low reasoning effort, 16,000 max tokens, and its original 2,500-call cap; future runs use the user-approved 3,000 cap.
- 2026-09-16 11:27 IST: The active pipeline routes logging to `/workspace/runs/scene00069_seed42_matrix120m/prompts`, so the supervisor can reject a stale pipeline belonging to another run.
- 2026-09-16 11:27 IST: The final remote suite has 36 passing tests. Transient Docker/process-inspection errors produce no destructive action, launch intent is write-ahead, failed-run archiving is idempotent, and safety pauses require an explicit `resume_generation` increment.
- 2026-09-16 11:27 IST: Pinned-checkout status hash `c9193c5e...` and diff hash `20874bc5...` match their pre-deployment values exactly.
- 2026-09-16 11:30 IST: Regression checks passed: 36 supervisor tests on the host, 38 offline ASP tests locally, and 11 evaluator tests in the pinned container environment.
- 2026-09-16 13:27 IST: Run 1 reached its first completed checkpoint beyond budget at 125.325 m (stage 27), used 1,922 calls, and passed artifact validation.
- 2026-09-16 13:28 IST: Docker creates run directories as `root:root`; host-side completion-marker writes therefore failed safely after the pipeline had stopped. Marker writes now use an atomic Python operation inside `asp-noetic`, preserving ownership and avoiding chmod/chown of evidence.
- 2026-09-16 13:29 IST: Run 2's first launch exposed a second container-restart edge case: `/tmp/.X99-lock` and `/tmp/.X11-unix/X99` survive Docker stop/start even though Xvfb does not. The pipeline failed before any LLM call. Launch preflight now removes only display 99's stale files after proving no live Xvfb owns the display.
- 2026-09-16 13:35 IST: Run 2 attempt 2 is healthy on scene 00573 / seed 42 with the frozen DeepSeek configuration and 3,000-call cap. The first attempt used zero calls and remains archived.

## Attempts log

Merged verbatim from ATTEMPTS.md (host name generalised). Rows 2 to 4 have one cell fewer than the header, as in the original.

| Time | Attempt | Evidence | Result | Next adjustment |
| --- | --- | --- | --- | --- |
| 2026-09-16 10:46 IST | Audit existing protection and active run. | No cron/systemd supervisor; Docker command is `sleep infinity`; only one matrix run exists; direct LAN required because local Tailscale was stopped. | Existing setup is healthy but not permanently supervised. | Build a host-resident supervisor and adopt run 1. |
| 2026-09-16 11:08 IST | Test policy, host boundary, and state machine; run a remote dry-run against run 1. | Focused tests passed and dry-run proposed `none`; PID 933 was unchanged. | Persist adoption and install the service. |
| 2026-09-16 11:10 IST | Install the user service, enable linger, observe two cycles, and restart only the supervisor. | Service remained active; experiment PID and start time did not change. | Harden crash windows and pipeline identity checks. |
| 2026-09-16 11:27 IST | Deploy the final supervisor and verify tests, logger routing, service lock, scene files, and source hashes. | 36 remote tests passed; pinned-checkout status and diff hashes are unchanged. | Leave the service active and report only milestones or blockers. |
| 2026-09-16 13:27 IST | Reconcile completed run 1 into the queue. | Run 1 stopped cleanly at 125.325 m and validated, but host marker creation failed because Docker-owned run directories are root-only for writes. No API process remained and run 2 had not launched. | Stop the supervisor, write markers atomically through Docker, test, and replay the idempotent completion transition. |
| 2026-09-16 13:28 IST | Deploy container-boundary marker fix and replay run-1 completion. | 37 tests passed; marker recorded 1,922 calls and final stage 27; container cleanup succeeded and queue advanced to run 2 without rerunning run 1. | Verify run 2 starts with frozen settings and leave supervision active. |
| 2026-09-16 13:29 IST | Launch scene 00573 / seed 42. | The first launch failed before any LLM call because stale display-99 lock/socket files survive Docker restarts after Xvfb dies. | Archive the failed launch, add live-owner-checked display cleanup, and use the one approved retry. |
| 2026-09-16 13:35 IST | Relaunch scene 00573 / seed 42 after display cleanup. | 39 tests passed; PID 985 is healthy, logger route and frozen settings match, and calls began increasing under the 3,000 cap. | Resume unattended supervision. |
