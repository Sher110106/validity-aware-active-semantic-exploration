# Closeout verification: 27 September 2026

The documentation, formatted paper, and file-level input inventory are complete. GPT-6 Luna made the paper and documentation corrections; the parent agent independently checked them and assembled the remote input manifest.

## Revision and scope

Base revision: `79354e1`. This record accompanies the documentation/paper cleanup commit. Runtime code under `tools/` and the frozen experiment results are unchanged from that revision. Verification used local tests, document inspection, existing-file hashes, and read-only SSH queries. No experiment, simulator, replay scoring, or provider request was launched.

## Checks

| Check | Result |
|---|---|
| Six offline test suites | 286 tests and 9 subtests passed on 27 September |
| `python -m compileall -q tools` | Passed |
| Current documentation links and result/audit JSON | Passed |
| Matrix static-result checksum list | All three files match |
| Phase 13 v5 checksum list | JSON and all three SVGs match |
| Paper Table I | Every value matches the four-decimal `official` and `support_threshold_tau_1.0` static JSON values |
| Paper Table II | Every value matches the four-decimal raw/calibrated 00573 static JSON values |
| Paper Table III | Matches the historical assessment's three novel-object totals and win/loss records; no new identity-level rescore performed |
| Paper references | All three bibliography entries cited in body text |
| Paper format | Four-page A4 PDF; Times New Roman body; template margins; heading VI kept with its following text |
| Host supervisor | `ActiveState=inactive`, `SubState=dead`, `UnitFileState=disabled` |
| Matching experiment processes | None observed in the read-only process check |
| Retired-supervisor snapshot | State, status, event log, and pipeline log present and hashed |
| Control-file preservation | Host hash matches local `tools/matrix_supervisor/CONTROL.json` |
| Gemini accounting | 2,282 settled requests, $37.353274 recorded settled cost, three `DISPATCHED` requests |

The offline suite command is in [REPRODUCE.md](../REPRODUCE.md). The current check did not change runtime code, so the passing source-tree test result also applies to this documentation-only cleanup.

## File-level input manifest

The [JSON manifest](2026-09-27-input-manifest.json) and [SHA-256 list](2026-09-27-input-SHA256SUMS) cover **1,702 files / 86,389,587 bytes** already present in the remote workspace:

- Four calibration runs, four frontier reference checkpoints, and three matrix runs.
- Frozen matrix static/decision results and Phase 13 outputs.
- Gemini v6 stage files and derived results.
- Retired-supervisor snapshot and analysis source files.

Every entry records its workspace-relative path, size, SHA-256, and role. Existing incomplete stages and absent completion slots are listed explicitly. The matrix inventory agrees with the frozen boundary: 94 completed stages, 752 intended completion slots, and 66 missing completions.

Local comparison found **92 matching copies, 1,607 host-only files, and three differing source files**:

- `tools/asp_offline/models.py`
- `tools/asp_offline/validator.py`
- `tools/decision_replay.py`

Both local and remote source hashes are retained. All 13 reference/static/decision hashes already recorded in frozen Phase 13 provenance match, as does the Phase 13 entrypoint hash. The new hashes of raw stage files establish their state at capture time; they cannot retroactively prove their full historical provenance.

Selected DeepSeek request archives were hashed in place because Phase 13 reads their count/timing metadata. Their bodies were not exported. Credentials, live SQLite ledgers/WALs, dataset assets, weights, images, and simulator binaries are excluded. A hash inventory is not a full raw-data export.

## Corrections completed

1. Updated current supervisor status; kept the earlier [26 September audit](../REMOTE_AUDIT_2026-09-26.md) explicitly historical.
2. Corrected the guardrail policy key and limits: absolute F1 loss at most 0.05, relative normalized-GED increase at most 10%. GED decreasing is a measured result, not the required threshold.
3. Added HM3D and NetworkX in-text citations, qualified full-graph retention, and clarified the separate normalization path in both paper formats.
4. Added [table provenance](../../paper/README.md) and file-level input hashes, replacing the earlier inventory-only completion claim.
5. Closed the checklist while retaining three unknown ledger costs and host-only reproduction requirements as evidence limits.

Financial settlement is still unresolved for three requests; their existing-record investigation is documented in [the ledger note](2026-09-26-dispatched-resolution.md). No new work or spending is needed to state the frozen research conclusions.
