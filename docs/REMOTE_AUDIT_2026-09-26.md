# Read-only closeout audit: 26 September 2026

**Historical snapshot:** the supervisor was subsequently stopped and disabled on 26 September. The [27 September verification](audit/2026-09-27-closeout-verification.md) confirms retirement, retained snapshots, and the final file-level manifest. The observations below describe the earlier audit.

The recorded research is frozen, but the remote operational state is not a clean shutdown. This audit inspected existing files, process state, Git metadata, and ledger aggregates. It launched no exploration, simulator, replay, or provider request and made no remote configuration changes.

## Scope and provenance

- Connection: the SSH endpoint supplied by the project owner, `sher@10.1.17.241`.
- Workspace: `~/active-semantic-perception-workspace`; mounted as `/workspace` in `asp-noetic`.
- Local source revision before this documentation pass: `c41cc31`.
- Author checkout HEAD: `f1ea141b1886d33ab8f4e4b791db4d3c92150b27`.
- Local verification: 286 tests and 9 subtests passed across all six offline suites.

This is a dated observation, not a live monitoring page. The JSON summary below contains aggregate accounting only; credentials, request bodies, and live databases remain on the host.

## Remote operational state

| Surface | Observed state | Meaning for closeout |
|---|---|---|
| ASP pipeline and ROS | No matching exploration pipeline, ROS launch, or ROS core processes found; supervisor also reported empty pipeline/ROS PID lists | No active experiment was observed |
| `asp-matrix-supervisor.service` | Enabled, active/running | The old supervisor still wakes up; it has not been retired |
| Supervisor `state.json` | `phase=paused`, two runs in `completed`, queue index 2 | Its bookkeeping does not say the whole matrix completed |
| Third matrix scene, 00853 | Path 126.075 m; blocker `completion validation failed: uncaptured traceback in pipeline log` | The saved 120 m analysis exists, but operational completion validation failed |
| Supervisor `CONTROL.json` | `paused=false`, `max_completed_runs=3` | The observed pause is internal state, not an explicit control-file freeze |
| Scientific `campaign_status.json` | Earlier breadth snapshot; omits v3 through v6 | It is not the final ledger or attempt inventory |
| v6 watchdog status | Seven path checkpoints through 19.5 m; reason still `watching` | The watchdog file is also a historical snapshot, not evidence of an active run |

The three DeepSeek runs reached the distance needed for the frozen static analysis. That statement is separate from the supervisor accepting three clean terminal runs. A future operational cleanup should preserve the current files and investigate the 00853 traceback before recording any corrected terminal status.

## Author-checkout provenance

The author Git HEAD matches the pin, but the working tree is modified. `git status --short` reported changes to:

- `exploration/config/frontier_config.yaml`
- `exploration/config/pipeline_config.yaml`
- `exploration/scripts/llm_completion.py`
- `mapping/clio/clio_ros/launch/realsense.launch`

It also reported untracked mapping dependencies/configuration. A pinned HEAD alone does not establish a byte-for-byte clean author checkout. The run-specific configuration snapshots and deviation log remain necessary provenance. No file in either author checkout was changed by this audit.

## Corrected Gemini accounting

Source: [sanitized ledger aggregates](audit/2026-09-26-ledger-summary.json), queried directly from the five existing databases. The SSH user could not read the root-owned ledgers directly, so the queries used the already-running container with SQLite `mode=ro` and `PRAGMA query_only=ON`.

| Ledger | Allocation | Settled requests | Recorded settled cost | Unresolved requests |
|---|---:|---:|---:|---:|
| Capability probe | $2.00 | 6 | $0.003775 | 2 |
| Native token-count verification | $1.00 | 1 | $0.016292 | 1 |
| Initial pilot ledger | $2.50 | 0 | $0.000000 | 0 |
| Native-count engineering pilot | $18.00 | 42 | $0.549772 | 0 |
| Scientific campaign, including v6 | $160.00 | 2,233 | $36.783435 | 0 |
| **Total** | **$183.50** | **2,282** | **$37.353274** | **3** |

The final v6 block is a **subset** of the scientific ledger: 898 settled requests, $18.552664 settled cost, and $65.749854 in summed historical reservations. The whole scientific ledger sums to $159.976812 in reservations, leaving only $0.023188 under that allocation's reservation accounting. This explains the allocation stop despite much lower settled spend.

The earlier approximately $18.80 project total omitted the v6 subset. It is superseded by this audit. These totals cover the recorded Gemini ledgers only; they are not a bill for the entire project or its earlier DeepSeek work. Three probe/verification requests remain `DISPATCHED`, with $0.009147 reserved and unknown settled cost. They must not be counted as zero-cost requests.

The allocations sum to $183.50 against the $190 code ceiling, an arithmetic difference of $6.50. This is not permission or a recommendation to allocate more money.

## Evidence copied without recomputation

The three existing `runs/matrix120m_scoring/scene*_extension_policy_replay.json` files were copied into the matching [local mirror directory](../tyrone_mirror/runs/matrix120m_scoring/). They supply the previously unlinked per-scene source tables for the headline DeepSeek result. Their SHA-256 digests matched the remote originals and are listed in [STATIC_REPLAY_SHA256SUMS](../tyrone_mirror/runs/matrix120m_scoring/STATIC_REPLAY_SHA256SUMS).

No scoring command was run to produce or refresh these files. Their embedded `/workspace/...` paths record the original environment, not paths that should exist in a fresh local clone.

## Actions still requiring a separate decision

1. Retire or explicitly pause the remote supervisor, preserving its state and event log. This changes host operation and was not performed during the read-only audit.
2. Reconcile the stale campaign and supervisor status files from existing evidence, including the 00853 traceback and v3/v4/v5/v6 attempts. Preserve the original records.
3. Resolve the three outstanding ledger entries from existing response archives or provider billing records, if available, without issuing new model calls.
4. Preserve a sanitized author-worktree diff and a manifest of raw inputs if independent full replay is a submission requirement.

See [remaining work](REMAINING_WORK.md) for the broader submission checklist.
