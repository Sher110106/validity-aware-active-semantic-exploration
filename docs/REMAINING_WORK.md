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

## Phase 1: write the IEEE paper (largest remaining item)

The template (`Report_Template (1).doc`) is an IEEE-style conference paper: A4, single column, Times, 10pt body, Roman-numeral section headings, abstract plus at least 5 keywords, tables and figures with fixed caption rules, no page numbers or hyperlinks. The deliverable is a fresh paper rendered into that format, not the markdown docs.

Section outline, each mapped to existing evidence:

1. Title, authors, abstract, keywords. Claim only what is supported: unanimity filtering improves static graph precision, F1, and normalized GED on three DeepSeek scenes; calibration and risk show no benefit; no live-navigation claim.
2. Introduction. The reproduced pipeline plus three tested extensions, and the deliberately narrower final conclusion (`FINAL_REPORT.md`, paper assessment update).
3. Background and reproduction scope. Substitute-backend disclosure (DeepSeek in place of the paper's Gemini backend, no paired comparison), self-generated frontier references, NetworkX GED reported as best-found upper bounds.
4. Method. Canonical adapter, structural validator, ensemble support with fixed denominator 4, LOSO calibration, and the three analysis tracks (static replay, decision replay, Phase 13). See `docs/ARCHITECTURE.md`.
5. Experimental setup. Three scenes (00069, 00573, 00853), seed 42, 120 m-capped path-normalized AUC with the canonical evaluator, plus the short-run baselines. Include the input-availability disclaimer.
6. Results. Static unanimity table with guardrails; mechanism plus validator-subsumed note; calibration negative (identical at tau 1.0, harmful at intermediate settings on 00573); risk-term negative; decision replay kept narrow and descriptive; Phase 13 guardrail disposition; Gemini v6 partial block in its own paragraph.
7. Limitations. One seed, three scenes, autocorrelated stages, backend property rather than environment generalization, modified author worktree, paused supervisor state.
8. Conclusion, acknowledgment, references. Cost note uses the corrected $37.353274 settled figure with three unresolved entries.

Hard claim boundaries (do not cross): no live-navigation, detour, collision, or path-length improvement; no calibration benefit; no risk-term benefit; no independent validator win on top of unanimity; no cross-scene generalization or significance claim at n=3; no predicted-only recall reading of the 99.7 percent full-graph retention; no reproduction of the authors' published numbers.

The `output/` proposal files stay as history only and do not ship. Do not carry proposal text forward except background sentences verified against current evidence.

## Phase 2: retire the supervisor (one approved host change)

Decision: retire, not leave paused-active. The 00853 pause is already analyzed in `DEVIATIONS.md` #73 as a conservative false positive on a post-budget traceback; the scored artifacts are intact. No new investigation is needed.

Approved sequence only:

1. Snapshot supervisor state, status, event log, and the 00853 pipeline log to a dated host directory. Preserve originals, never rewrite.
2. `systemctl --user stop` then `disable asp-matrix-supervisor.service`; verify inactive. Never raw-kill the PID (restart-on-failure resurrects it).
3. Leave `tools/matrix_supervisor/CONTROL.json` byte-identical as history.
4. Add a dated note reconciling `campaign_status.json` (earlier breadth snapshot, omits v3 through v6) against the ledger aggregates, without editing the original.

## Phase 3: resolve the three DISPATCHED entries (existing records only)

Two in the capability-probe ledger and one in the native-count verification ledger, $0.009147 reserved in total, each with a known request id. Read the ledgers with `mode=ro` plus `PRAGMA query_only=ON` through the existing container, then look up sibling response archives and count logs in the same run directories. No new model calls, no hand settlement, no retry. Record each entry as settled or unknown cost; never zero. Expected: the verification entry stays correctly unresolved and fail-closed.

## Phase 4: finish evidence packaging

- [ ] Confirm the input-availability matrix in `docs/RESULTS_INDEX.md` against the host-only export list (non-00069 calibration `stages/`, three matrix run directories, v6 stage corpus, ledger and response archives, supervisor snapshots).
- [ ] Quarantine stale probe, deploy, resume, and live-mode invitations as historical provenance; keep one frozen-campaign statement in canonical docs.
- [ ] If submission requires full replay, preserve a sanitized author-worktree diff (four modified files) plus a SHA-256 raw-input manifest. Do not claim the mirror alone regenerates Phase 13.

## Phase 5: final verification and commit

- [ ] Re-run the offline suite (`pytest`, 286 tests plus 9 subtests expected), `compileall`, JSON parsing of cited artifacts, and the canonical-doc link check. Record the date and revision.
- [ ] Verify every paper table cell traces to a cited artifact and that static-replay and Phase 13 digests match their checksum files.
- [ ] Commit on a clean tree. Pushing to `origin` stays a separate publication decision.

## Explicit non-goals

No new ASP pipeline run, no simulator or ROS session, no provider-funded call, no recomputation of frozen numbers, no remote configuration change beyond the approved supervisor retirement, and no credential handling.
