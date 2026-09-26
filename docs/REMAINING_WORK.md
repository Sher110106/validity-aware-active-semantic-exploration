# Remaining work (no new runs)

All items below use existing files, local checks, or read-only host inspection. None requires a new simulation, replay computation, or provider call.

## Documentation closeout (this pass)

- [x] Rewrote `README.md` around the supported conclusion and added a repository map.
- [x] Added `docs/ARCHITECTURE.md` with the dataflow, module roles, metric glossary, and status labels.
- [x] Added `docs/REMOTE_AUDIT_2026-09-26.md` with the read-only SSH observation and corrected Gemini accounting.
- [x] Added `docs/audit/2026-09-26-ledger-summary.json` with sanitized aggregate ledger rows.
- [x] Copied the three existing matrix static-replay JSON files into `tyrone_mirror/runs/matrix120m_scoring/` with `STATIC_REPLAY_SHA256SUMS`.
- [x] Propagate the corrected accounting into `FINAL_REPORT.md`.
- [x] Point `docs/RESULTS_INDEX.md` at the three newly mirrored static-replay files and state which evaluator each table uses.
- [x] Split `docs/REPRODUCE.md` into inspect, fixture-test, local-replay, and host-only tiers with one consistent interpreter.

## Evidence packaging

- [ ] Add an input-availability matrix: mirrored result present, raw input present, or host-only export required. Known host-only gaps include non-00069 calibration `stages/` directories, the three matrix run directories, and the original v6 stage graph corpus.
- [ ] Quarantine stale operational invitations (probe, deploy, resume, live-mode sequences) as historical provenance; keep one frozen-campaign statement in canonical docs.
- [ ] Reconcile `campaign_status.json` (earlier breadth snapshot, omits v3 through v6) against the ledger aggregates without editing the original; add a dated note rather than rewriting history.
- [ ] Resolve three `DISPATCHED` probe/verification requests ($0.009147 reserved) from existing response archives or billing records only; record them as unknown cost if no record exists.
- [ ] If submission requires full replay, preserve a sanitized author-worktree diff and a manifest of raw inputs; do not claim the mirror alone regenerates Phase 13.

## Operational closeout (host decisions, read-only until approved)

- [ ] Retire or explicitly pause `asp-matrix-supervisor.service`, preserving state and event logs. Observed 26 September: service enabled and active, internal phase paused, two completions recorded, third scene blocked on an uncaptured traceback at 126.075 m.
- [ ] Investigate the 00853 pipeline-log traceback from existing logs before recording any corrected terminal status. Preserve the original log.
- [ ] Leave `CONTROL.json` unchanged until the supervisor decision is made; its `"paused": false` value does not itself authorize work.

## Submission preparation

- [ ] Confirm the course deliverable format (report file, page limit, required sections) and map each section to `FINAL_REPORT.md` and `docs/RESULTS_INDEX.md`.
- [ ] Decide whether the existing proposal files under `output/` stay as history or leave the submission package.
- [ ] Run the final local verification once (offline tests, JSON parsing, link check) and record the date and revision.
- [ ] Commit this documentation pass on a clean tree; pushing to `origin` is a separate publication decision.

## Explicit non-goals

No new ASP pipeline run, no simulator or ROS session, no provider-funded call, no recomputation of frozen numbers, no remote configuration change, and no credential handling.
