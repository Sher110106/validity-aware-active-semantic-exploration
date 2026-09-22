<goal>
Implement and deploy a host-resident supervisor for the ASP 12-run matrix that adopts the current run without restarting it, enforces the 120 m budget, safely sequences the remaining runs, and recovers from clear host/container failures within the user-approved resource limits.
</goal>

<context>
Read `SPEC.md`, `IMPLEMENTATION_PLAN.md`, and the latest entries in `tyrone_mirror/DEVIATIONS.md`. The live workspace is `/home/sher/active-semantic-perception-workspace` on tyrone; the Docker container is `asp-noetic`; the pinned author checkout is under `catkin_ws/src/active_semantic_perception` and is protected. Reuse the established `run_llm_pipeline_scene.sh` launch contract but do not assume it provides monitoring, cleanup, queueing, or restart safety.
</context>

<constraints>
Use Python's standard library only. Do not edit pinned research code. Do not restart the healthy current run. Keep one active run, one supervisor lock, one retry maximum after the initial attempt, a 3,000-call cap for future runs, a 25 GB disk floor, a 60-second poll interval, and pause-without-kill for ambiguous 30-minute stalls. Preserve every failed attempt under a unique archival name. Docker GPU self-healing may run only after host GPU health succeeds and two container GPU checks fail.
</constraints>

<scorecard>
Primary checklist: focused behavior tests all pass; live dry-run returns adoption/no-op; deployed service is active and singular; status agrees with raw path/call artifacts. Passing threshold is 100%. Regression checks are the existing offline suite plus unchanged live pipeline PID/start time/stage progress across deployment. Stop when all `SPEC.md` done-when checks pass.
</scorecard>

<done_when>
1. `python3 -m unittest discover -s tools/matrix_supervisor/tests -v` passes.
2. Existing offline tests pass unchanged.
3. Live `--check` reports one healthy active pipeline with matching GPU, disk, path, calls, and attempt 2.
4. Live `--once --dry-run` proposes no launch or restart.
5. The user systemd service is active and user lingering is enabled.
6. Restarting the supervisor leaves the exploration PID and run artifacts unchanged.
7. Atomic status and append-only event artifacts expose thresholds, blocker, current run, attempt, and next check.
8. A before/after hash check shows no pinned-checkout source changes.
</done_when>

<feedback_loop>
For each vertical slice, run the focused unittest module (expected under five seconds). Use fake command/filesystem fixtures to exercise state transitions without Docker. Before deployment, run the full focused suite and a remote read-only `--check`; then run `--once --dry-run`. The slower final check is service installation/restart plus live PID/artifact comparison and the existing offline test suite.
</feedback_loop>

<workflow>
Implement in vertical TDD slices: queue/adoption; health snapshot and read-only status; budget stop policy; retry/archive policy; GPU repair policy; launch/cleanup; daemon lock/control reload; service installation. Deploy only after local tests. Run remote check and dry-run before enabling actions. Enable the service, observe at least two cycles, restart only the supervisor, and verify the experiment is untouched.
</workflow>

<working_memory>
Maintain `PLAN.md` for phases, `ATTEMPTS.md` after each meaningful test/deployment attempt, and `NOTES.md` for durable live-system discoveries. Do not use conversation memory as the operational state; runtime state belongs under `runs/matrix_supervisor/` on tyrone.
</working_memory>

<human_control_surface>
Maintain `CONTROL.md` for implementation governance and deploy `tools/matrix_supervisor/CONTROL.json` for runtime knobs. Reread runtime control every cycle. A human may pause automatic launches/retries without disabling budget monitoring. Strategic changes, destructive cleanup, retry-limit increases, disk-floor reductions, or pinned-code edits require explicit approval.
</human_control_surface>

<verification_loop>
Run focused tests after each slice, then all supervisor tests, compileall, existing offline tests, remote `--check`, remote `--once --dry-run`, systemd status, and a before/after comparison of exploration PID/start time/path plus pinned-checkout hashes. On any mismatch, disable the supervisor service without touching the experiment and investigate.
</verification_loop>

<execution_rules>
Check git status before edits and preserve unrelated changes. Prefer dedicated read/search/edit tools. Keep the scorecard current and use the fastest representative test. Record meaningful attempts. Run focused tests before broad tests. Do not paper over failures, widen scope, delete evidence, expose credentials, or alter a healthy live run.
</execution_rules>

<output_contract>
Deliver tested source and service files under `tools/matrix_supervisor/`, local specification/control records, deployed host files, active service evidence, and a concise final report with live run status, safeguards, remaining limitations, and exact operator commands.
</output_contract>

<scope_note date="2026-09-16">
The experiment's final size was descoped for cost/time to 3 scenes x 1 seed
(3 runs), not the original 12-run matrix this goal was written against --
see IMPLEMENTATION_PLAN.md section 0. The line above is left as the
historical record of what this supervisor was built to sequence; the
supervisor's own behavior did not need to change, since it now stops early
via CONTROL.json's max_completed_runs rather than by a different queue.
</scope_note>
