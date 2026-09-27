# Completed closeout plan (no new runs)

Reviewed by two independent read-only passes on 26 September 2026. Final documentation and paper corrections were completed with GPT-6 Luna on 27 September. This checklist records completed closeout work; the [verification record](audit/2026-09-27-closeout-verification.md) states the evidence limits.

Work used existing files, local checks, and the approved supervisor retirement. No new simulation, replay computation, or provider call was launched.

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
- [x] Corrected citations, guardrail wording, full-graph retention qualifiers, and heading pagination on 27 September; preserved all three result tables. See [paper provenance](../paper/README.md).
- [x] `output/` proposal files stay as history only and do not ship.

## Host closeout (Phase 2, done 26 September 2026)

- [x] Retired `asp-matrix-supervisor.service` with owner approval: snapshotted state, status, event log, and the 00853 pipeline log to `runs/matrix_supervisor/snapshot_20260926_retire/` on the host, then stopped and disabled the service (verified inactive, disabled, no supervisor process). `CONTROL.json` left byte-identical.
- [x] The 00853 traceback needed no new investigation: already analyzed as a post-budget false positive with scoring intact. Original log preserved in the snapshot.
- [x] Added `docs/audit/2026-09-26-campaign-status-note.md` reconciling the stale status file against ledger aggregates; the host original untouched.

## Ledger investigation (Phase 3, done 26 September 2026)

- [x] Investigated the existing records in [the ledger note](audit/2026-09-26-dispatched-resolution.md): the verification entry has an archived provider response and was left fail-closed; the two probe entries have no archive in their run directory. All three remain `DISPATCHED` with unknown settled cost. Investigation is complete; financial settlement remains unresolved. No ledger writes or model calls were made.

## Evidence packaging (Phase 4, completed 27 September 2026)

- [x] Input-availability matrix confirmed in `docs/RESULTS_INDEX.md` against the host-only export list.
- [x] Stale probe, deploy, resume, and live-mode invitations quarantined as historical provenance in `docs/prospective_overlay/README.md`; one frozen-campaign statement kept in canonical docs.
- [x] Sanitized author-worktree diff preserved at `docs/audit/2026-09-26-author-worktree-diff.txt`.
- [x] Added the [file-level input manifest](audit/2026-09-27-input-manifest.json) and [SHA-256 list](audit/2026-09-27-input-SHA256SUMS): 1,702 files, 92 matching local copies, 1,607 host-only files, and three differing source files. All 13 recorded frozen Phase 13 input hashes match. This inventories existing bytes; it does not export the full raw corpus.

### Availability summary (detailed paths and hashes in the manifest)

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
| Host analysis source | Three files differ from the repository; both hashes recorded |

## Final verification (Phase 5, completed 27 September 2026)

- [x] Verified 286 tests plus 9 subtests, bytecode compilation, JSON parsing, and canonical-document links. Runtime source is unchanged from `79354e1`; details are in the [verification record](audit/2026-09-27-closeout-verification.md).
- [x] Matched Tables I and II to exact rounded static-result JSON values and Table III to the saved historical assessment. Verified static-replay and Phase 13 checksums, all paper citations, A4 format, and four-page PDF rendering.
- [x] Committed the cleanup with its verification record. Publication to `origin` remains a separate decision.

## Preserved evidence limits

The raw dataset is partly host-only, three ledger costs are unresolved, and the research does not establish live-navigation improvement. These limitations remain explicit in the completed package.

## Explicit non-goals

No new ASP pipeline run, no simulator or ROS session, no provider-funded call, no recomputation of frozen numbers, no remote configuration change beyond the approved supervisor retirement, and no credential handling.
