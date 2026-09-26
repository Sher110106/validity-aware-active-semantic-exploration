# Final plan (no new runs)

Reviewed by two independent read-only passes on 26 September 2026: one on the paper deliverable, one on evidence and host closeout. Both agreed with the direction and sharpened it. This file is the merged final plan.

All items use existing files, local checks, or read-only host inspection. None requires a new simulation, replay computation, or provider call.

## Already done (26 September pass, committed as `573ab84`)

- [x] Rewrote `README.md` around the supported conclusion and added a repository map.
- [x] Added `docs/ARCHITECTURE.md` with the dataflow, module roles, metric glossary, and status labels.
- [x] Added `docs/REMOTE_AUDIT_2026-09-26.md` with the read-only SSH observation and corrected Gemini accounting.
- [x] Added `docs/audit/2026-09-26-ledger-summary.json` with sanitized aggregate ledger rows.
- [x] Copied the three existing matrix static-replay JSON files into `tyrone_mirror/runs/matrix120m_scoring/` with `STATIC_REPLAY_SHA256SUMS`.
- [x] Propagated the corrected accounting into `FINAL_REPORT.md` ($37.353274 settled, v6 as a subset).
- [x] Pointed `docs/RESULTS_INDEX.md` at the mirrored static replays with evaluator labels and an input-availability note.
- [x] Split `docs/REPRODUCE.md` into inspect, fixture-test, local-replay, and host-only tiers with one consistent interpreter.

## Final paper (Phase 1, done 26 September 2026)

- [x] Drafted the IEEE paper and rendered `paper/Validity_Aware_Active_Semantic_Exploration.docx` plus the PDF conversion (4 pages, A4, template margins and caption rules, Tables I-III, claim boundaries kept).
- [x] `output/` proposal files stay as history only and do not ship.

## Host closeout (Phase 2, done 26 September 2026)

- [x] Retired `asp-matrix-supervisor.service` with owner approval: snapshotted state, status, event log, and the 00853 pipeline log to `runs/matrix_supervisor/snapshot_20260926_retire/` on the host, then stopped and disabled the service (verified inactive, disabled, no supervisor process). `CONTROL.json` left byte-identical.
- [x] The 00853 traceback needed no new investigation: already analyzed as a post-budget false positive with scoring intact. Original log preserved in the snapshot.
- [x] Added `docs/audit/2026-09-26-campaign-status-note.md` reconciling the stale status file against ledger aggregates; the host original untouched.

## Ledger entries (Phase 3, done 26 September 2026)

- [x] Resolved from existing records in `docs/audit/2026-09-26-dispatched-resolution.md`: the verification entry has an archived provider response and was correctly left fail-closed; the two probe entries have no archive either way. All three stay `DISPATCHED` with unknown cost, never zero. No ledger writes, no model calls.

## Evidence packaging (Phase 4, done 26 September 2026)

- [x] Input-availability matrix confirmed in `docs/RESULTS_INDEX.md` against the host-only export list.
- [x] Stale probe, deploy, resume, and live-mode invitations quarantined as historical provenance in `docs/prospective_overlay/README.md`; one frozen-campaign statement kept in canonical docs.
- [x] Sanitized author-worktree diff preserved at `docs/audit/2026-09-26-author-worktree-diff.txt` (four modified files, no secrets). Raw-input manifest below.

### Raw-input manifest (host-only exports needed for full Phase 13 regeneration)

| Input | Status |
|---|---|
| 00069 calibration `stages/` | Mirrored (partial) |
| 00573, 00853, 00871 calibration `stages/` | Host-only |
| Four frontier reference graphs | Mirrored |
| Three matrix run directories (full `stages/`, logs, config) | Host-only |
| Three matrix static replays + checksums | Mirrored |
| Three matrix null decision replays | Mirrored |
| Phase 13 v5 diagnostics + checksums | Mirrored |
| v6 stage graph corpus | Host-only (derived JSON mirrored) |
| Ledger SQLite files and response archives | Host-only |
| Supervisor state snapshot | Host-only (`snapshot_20260926_retire/`) |

## Final verification (Phase 5)

- [ ] Re-run the offline suite (`pytest`, 286 tests plus 9 subtests expected), `compileall`, JSON parsing of cited artifacts, and the canonical-doc link check. Record the date and revision.
- [ ] Verify every paper table cell traces to a cited artifact and that static-replay and Phase 13 digests match their checksum files.
- [ ] Commit on a clean tree. Pushing to `origin` stays a separate publication decision.

## Explicit non-goals

No new ASP pipeline run, no simulator or ROS session, no provider-funded call, no recomputation of frozen numbers, no remote configuration change beyond the approved supervisor retirement, and no credential handling.
