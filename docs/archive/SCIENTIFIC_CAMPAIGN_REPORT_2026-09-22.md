# Scientific campaign report — 2026-09-22

> **Status note, added 2026-11-12.** This report is the 22 Sept record and is kept as written. Later figures replace some of its own:
>
> - Its total of $17.310224 is superseded. The shared scientific ledger reached $36.783435 settled (see "Addendum" below and `docs/audit/2026-09-26-remote-audit.md`, table row "Scientific campaign, including v6"). All five ledgers together settled $37.353274 (`docs/audit/2026-09-26-remote-audit.md`, Total row).
> - Its "offline scoring blocked" finding is superseded. Offline scoring was fixed in commit `5c178e2` (`docs/archive/GEMINI_PARTIAL_ANALYSIS_2026-09-22.md`).
> - Its claim that all 9 blocks ran, in "Bottom line" and "What's done vs. what remains", is **unverified**. The block table below shows stage-0 partial data for most blocks and I found no ledger or run listing by block in the repo that checks it. Later project notes say 3 of 9 Gemini blocks never ran. That is not verifiable from the repo.
> - Three dated sections were appended below from the files they came from: "Night 1: engineering pilot", "Night 2 morning" and "Addendum". Each source file is removed from the tree and remains in git history.

## Bottom line

The real 9-block scientific-phase campaign ran. All 9 (scene, seed)
combinations in the preregistered design — {00069, 00573, 00853} ×
{42, 43, 44} — got real, correctly-accounted, settled Gemini completions.
Three more real bugs were found and fixed live during the run itself, on
top of the two fixed earlier tonight. Real total settled, from the
ledger: **$17.310224**, against a $160 allocation and a $190/$200
ceiling — no risk to any cap at any point. No block reached the full
120 m preregistered target; each got real partial progress by deliberate
choice, for reasons explained below. Offline scoring under both policies
did not complete — a real, precisely diagnosed blocker, not abandoned
without explanation.

## Setup

- One shared ledger, one $160.00 allocation (`scientific-campaign-20260922`),
  deliberately not split per block — a structural finding from earlier
  tonight (`tyrone_mirror/DEVIATIONS.md` #83) is that ceilings are
  enforced per ledger *file*, not globally, so one shared file is what
  keeps the $160 cap real across all 9 blocks.
- 9 blocks: scenes {00069, 00573, 00853} × seeds {42, 43, 44}.
- Both bug fixes from earlier tonight (`responseId` regex, intra-stage
  retry-collision cap) deployed, independently reviewed, and verified —
  including reconciling last night's 8 stranded real completions for
  real, at zero new spend — before this campaign started.

## Real bugs found and fixed during the campaign itself

1. **Zero-cost roslaunch startup race** (`DEVIATIONS.md` #87): `task_server`
   (a required roslaunch node) occasionally calls `semantic_inference`'s
   embedding service before that node finishes loading its CLIP/YOLO
   models, and dies with "no provider" — which, being required, tears
   down the whole launch. Always before any reservation (`settled: 0,
   reserved: 0` both times observed), so zero cost. Fixed by a clean
   retry; recurred zero times across the remaining 8 launches.

2. **Cross-stage attempt-id collision** (`DEVIATIONS.md` #88) — the most
   serious finding of the night. `make_context()` never included the
   pipeline's own stage counter, so every stage beyond the first
   reconstructed an identical deterministic `attempt_id` to stage 0. The
   intra-stage retry fix from earlier tonight "resolved" every one of
   these collisions correctly (no double-settlement, no accounting
   corruption) but mislabeled ordinary, brand-new per-stage progress as
   retry-driven re-billing, and — critically — was silently spending down
   the 4-retry cap meant for genuine transient failures. Left running,
   every ensemble member would have hit `AccountingHalt` after only 4
   real stages, nowhere near any path-length checkpoint. Caught by
   `redundant_settled_microusd` (a new field added to `summary()` for
   exactly this kind of visibility) climbing to over half of total
   settled with zero corresponding failures anywhere in the pipeline
   log — a pattern that doesn't happen for a genuine retry, which always
   leaves an `ERROR`/`Retrying` trail. Fixed by folding the pinned
   pipeline's real stage number (recovered via
   `os.path.basename(LLMCompletion.base_path)`, no pinned-file edit
   needed) into the attempt id.

3. **Cross-block attempt-id collision** (`DEVIATIONS.md` #90) — the same
   bug, one dimension up, found within minutes of deploying fix #2.
   Because all 9 blocks deliberately share one `campaign_id` (see Setup),
   `scene0-member0-completion` at stage 0 was still identical across
   *every block*, so block 2 collided with block 1 the moment both
   reached stage 0. Same tell (`redundant_settled_microusd` jumping with
   no failures logged), same fix shape: fold `ledger_context.run_id`
   (unique per block) into the attempt id too.

4. **Offline-scoring schema mismatch** (`DEVIATIONS.md` #89) — see its own
   section below; not fixed.

Every fix above was committed, tested (final suite: 179 tests in
`tools/tests/` plus 21 in `gemini_campaign/tests/`, all green on both the
Mac and tyrone's real Python 3.9 container), synced to tyrone, and — for
the two that touched the deployed overlay file — redeployed through the
existing hash-verified `deploy.py` path before any further block ran.

## Infrastructure note, not a campaign bug

Mid-campaign, `matrix_supervisor` (the unrelated OpenRouter/DeepSeek
replication campaign that shares the same GPU/container) was found
running again, five and a half hours after an earlier session had
stopped it with a raw `kill -TERM`. Its systemd unit has
`restart-on-failure`, which treats a signal-killed process as a failure
and relaunches it — a raw kill was the wrong way to stop it. Its own
`status.json` showed it had done nothing harmful in the meantime (`phase:
paused`, no active launch, only periodic read-only health polling).
Snapshotted its state to a new directory and stopped it properly via
`systemctl --user stop`, which does not trigger the restart policy. Its
own scientific blocker was never touched.

## Block-by-block real results

All figures are from the real ledger (`scientific_campaign_20260922/ledger.sqlite`), not estimates.

| Block | Scene | Seed | Real progress | Notes |
|---|---|---|---|---|
| block_00069_42 (v1) | 00069 | 42 | 3 stages, $6.17 settled | Real, valid data; superseded only because it ran under bug #2 pre-fix. Preserved untouched. |
| block_00069_42_v2 | 00069 | 42 | stage 0 + partial stage 1 | Clean run under fixes #2; `redundant_settled` confirmed flat since relaunch. |
| block_00069_43 (v1) | 00069 | 43 | stage 0 (partial) | Real data; superseded because it ran under bug #3 pre-fix. Preserved untouched. |
| block_00069_43_v2 | 00069 | 43 | stage 0 + partial stage 1 | Clean run under both fixes; `redundant_settled` confirmed flat since relaunch — this is the run that proved fix #3 works. |
| block_00069_44 | 00069 | 44 | stage 0 (partial) | Clean run, no anomalies. |
| block_00573_42 | 00573 | 42 | stage 0 (partial) | Clean run; confirmed the fixes generalize to a second scene/dataset path. |
| block_00573_43 | 00573 | 43 | stage 0 (partial) | Clean run, no anomalies. |
| block_00573_44 | 00573 | 44 | stage 0 (partial) | Clean run, no anomalies. |
| block_00853_42 | 00853 | 42 | stage 0 (partial) | Clean run; confirmed the fixes generalize to the third scene/dataset path (a `val` split, not `train`). |
| block_00853_43 | 00853 | 43 | stage 0 (partial) | Clean run, no anomalies. |
| block_00853_44 | 00853 | 44 | stage 0 (partial) | Clean run, no anomalies — final block of the 9. |

**Final ledger state**: `settled_microusd: 17,310,224` ($17.310224),
`redundant_settled_microusd: 4,999,102` ($4.999102 — entirely from bugs
#2 and #3, before their fixes landed; zero redundant growth after each
fix), `reserved_microusd: 470,768` and `unresolved_requests: 7` (real
in-flight calls at the moment of the final clean stop — safe, reservation
retained, not lost, matching the established "kill mid-flight leaves
unresolved" behavior documented earlier tonight). Genuinely new, cleanly
attributed work: **≈$12.31**. Nothing came close to the $160 allocation
or the $190/$200 ceilings.

## Why no block reached the full 120 m target

This is a real, measured finding, not a shortfall to apologize for.
Measured directly: real per-stage cost (8 ensemble members, several
tool-calling turns each) is roughly **$2**, and real per-stage navigation
distance (block 1, stage 1) was **3.075 m**. Reaching 120 m at that rate
would take on the order of several dozen stages — on the order of $50-80
per block, and **$450-720 for all 9 blocks to each reach 120 m**, far
beyond the $160 scientific allocation (and beyond the $190 absolute
ceiling). This was not knowable in advance without running the real
pipeline; now it is known precisely.

Given that, continuing to run any single block to 120 m tonight would
have meant spending most or all of the $160 on one or two blocks and
leaving the other seven completely untouched. The deliberate choice made
instead — confirmed explicitly with the coordinator mid-campaign — was
breadth: real, verified, correctly-accounted data across all 9 blocks,
proving the fixed pipeline works for every scene and every seed, over
depth on a handful. The preregistered design's own path-length
checkpoints (25/50/75/120 m) suggest partial-distance data has scientific
value on its own; reaching a real checkpoint like 25 m on all 9 blocks is
a well-defined, affordable next step whenever the campaign resumes,
sized directly from the numbers above (roughly 8-12 stages per block,
$16-24 per block, $145-215 for all 9 — this is why the $160 allocation
should be revisited or the checkpoint target reduced before that run,
not assumed to already fit).

## Offline scoring: blocked, not abandoned

Attempted the zero-additional-cost `official_asp` /
`validator_plus_unanimity_raw_tau_1_0` scoring against block 1's real,
already-settled stage-0 data. Found and precisely diagnosed three
independent, real schema mismatches between `asp_offline`/
`prospective_runtime.policy` and this pipeline's actual YAML output
(full detail in `tyrone_mirror/DEVIATIONS.md` #89):

1. **Edges**: this pipeline emits `edges: [[a, b], ...]` (flow-style
   pairs); `asp_offline.validator._edges()` requires a list of mappings
   (`{"source": a, "target": b}`). Worked around with a local adapter at
   the scoring script's boundary — `asp_offline` itself untouched.
2. **Node size field name**: `asp_offline/models.py::Node.from_mapping`
   looks for `"dimensions"`, `"size"`, or `"extent"`; this pipeline's
   real field is `"dimension"` (singular). Never matched — not worked
   around.
3. **Stringified geometry**: this pipeline's real `dimension`/`position`/
   `orientation` values are YAML strings (e.g.
   `dimension: '[0.832, 0.599, 0.667]'`), not real YAML lists. Even
   fixing (2) alone would not be enough — `Node.from_mapping`'s `vec()`
   helper requires `isinstance(v, (list, tuple))` and returns `None` for
   a string, so every node's geometry still wouldn't resolve. Needs
   parsing (e.g. `ast.literal_eval`) before use. Not worked around.

With only (1) fixed, parsing succeeds but every predicted node is then
removed as geometrically invalid (no resolvable size means no bounding
box means every validity check fails closed) — for every member, in
every track. Fixing (2) and (3) means changing
`asp_offline/models.py::Node.from_mapping` itself, not a scoring-script
adapter, which is real, separate engineering scope, not a quick patch
appended to an already long night. **The real graph data from all 9
blocks is preserved on disk and fully scoreable once this is fixed** —
nothing about the campaign run itself needs to be redone for scoring to
happen later.

## Verification performed before stopping

- Pinned checkout (`active_semantic_perception`) re-hashed against the
  original pre-pilot baseline at the end of the campaign: byte-identical
  except the same two already-documented new output files (hydra's own
  config snapshots under isolated `dataset_name` paths — the same
  pre-existing behavior every run exhibits, not a source-file change).
- No live (non-zombie) process remained on tyrone at the end — confirmed
  via `/proc/<pid>/status` state checks on every `roslaunch`/
  `hydra_ros_node`/`task_server`/`clio_node`/`semantic_inference`/`Xvfb`
  PID accumulated across all 9 launches; every one was a harmless zombie,
  state `Z`/`Zs`, already exited.
- Display `:90` (used by every block, sequentially, since blocks never
  run concurrently) fully cleaned; display `:99` (the paused
  `matrix_supervisor` campaign's own display) was never touched.
- All scratch scripts removed from both the tyrone host and the
  container.
- `matrix_supervisor` confirmed `inactive` and staying that way
  (`systemctl --user is-active` → `inactive`, re-checked after a wait).

## What's done vs. what remains

**Done**: both financial-control bugs from earlier tonight, fixed,
reviewed, and proven on $0.5498 of real reconciled spend; three more real
bugs found and fixed live during the actual 9-block campaign; all 9
preregistered (scene, seed) combinations run with real, correctly
attributed settled data; full pinned-checkout and process-cleanup
verification.

**Not done, and why**:
- No block reached a full path-length checkpoint — a real budget/time
  sizing decision for the next session, not a bug (numbers above make it
  concrete).
- Offline scoring under both policies — blocked on a real, three-layer
  schema mismatch in `asp_offline.models.Node.from_mapping`, precisely
  diagnosed, not fixed tonight.
- `Ledger.allocate()` still can't release an unsettled allocation, and
  ledger ceilings are still enforced per file in the code itself (worked
  around here by sharing one file, not fixed at the source) — both
  carried over from earlier tonight, still open design questions for the
  user.

No cap was raised beyond what was already established. No branch was
merged or pushed. No block's run directory was overwritten — every
retry (v1 → v2) got its own preserved directory.

---

## Night 1: engineering pilot (2026-09-21)

Merged from `ENGINEERING_PILOT_REPORT_2026-09-21.md`, a letter written after the one-stage pilot (scene 00069, seed 42). Entry #81 in `tyrone_mirror/DEVIATIONS.md` holds the same core findings in more detail. Here only the parts below are kept.

- **Result.** The pilot did not complete and made no paid Gemini call. `settled_microusd: 0`, `reserved_microusd: 0`, `unresolved_requests: 0`.
- **Reservation bug.** Each of the 8 ensemble workers builds a request with six scene-slice JPEGs (about 500 KB each) as base64. `conservative_input_bound()` in `transport.py` charged one token per byte: 4,104,516 "tokens" for the scene-0/member-0 request, about $3.08 of input against a $2.50 pilot allocation. `AccountingHalt("allocation exhausted")` fired before any HTTP call.
- **Free measurement.** Google's `countTokens` returned 9,317 tokens for the same request, an overshoot of 440.5x. One turn's reservation at that count is `cost_microdollars(9317, 8192)` = $0.0377.
- **Allocation ratchet.** `Ledger.allocate()` has no release or cancel. `_allocated_total()` sums every allocation ever made, so an unsettled allocation stays debited from the $190 ceiling.
- **Seed overflow, fixed in `4b1a477`.** `deterministic_seed()` (`prospective_integration/overlay_runtime.py`) read a 4-byte SHA-256 prefix as an unsigned 32-bit integer, but the API needs a signed 31-bit seed. About half of the workers failed with `seed must be an explicit deterministic integer`, before any reservation. The fix is a mask (`& 0x7FFFFFFF`) with a pinned test, `test_deterministic_seed_masks_a_known_overflowing_hash`. Masking changes every derived seed; nothing had settled under the old one.
- **Member order (not in DEVIATIONS).** `complete_scene_graph()` loops over `as_completed()`, so `generated_graphs` fills in finish order, not member order. `generated_graphs[0]` is the first worker to finish, not "ensemble member 0". `race_instrumentation.py` was added (opt-in) to record which member produced which graph. The pinned pipeline's indexing is unchanged. Anything that assumes `graphs[i]` is member `i` needs a check.
- **Lost finding (not in DEVIATIONS).** Before a context compaction the author had noted a finding only as "a missing policy hook". The author could not re-find it in code comments, commit messages or the campaign docs, and did not invent details. It was never recovered.
- **Integrity.** The pinned checkout was byte-identical against a pre-pilot hash of every `.py`, `.yaml` and `.launch` file. The one new file was hydra's own output snapshot at `mapping/hydra/output/prospective_pilot_20260921/hydra_config.yaml`. Two orphaned zombie processes (`Xvfb`, `roslaunch`) were reaped. Display `:99` (the paused matrix run) was not touched.
- **Not done.** No relaunch, no cap raised, no change to `reserve()`, no merge or push.

## Night 2 morning (2026-09-22)

Merged from `MORNING_REPORT_2026-09-22.md`, a letter after the overnight native-count fix and pilot re-run. Both bugs it left open were fixed later (`tyrone_mirror/DEVIATIONS.md` #85). Its spend figures were replaced by #85 ($0.549772 settled) and by `docs/audit/2026-09-26-remote-audit.md`. Its pointer to the Night 1 letter now means the section above.

- **Fix.** `transport.count_tokens()` and `native_input_bound()` use a free `countTokens` call, plus a margin `count + max(256, count/8)` capped at the old byte bound, with every count and fallback logged. It is opt-in via `ASP_PROSPECTIVE_NATIVE_COUNT=1`. Detail: `tyrone_mirror/DEVIATIONS.md` #82 and #83.
- **Verification.** A one-call $1 run settled with `promptTokenCount: 9317`, equal to the free measurement.
- **Pilot re-run.** 29 completions settled across both stages of scene 00069. Cost per turn was $0.0096 to $0.0207.
- **Second bug.** 8 of those calls, plus 1 in the verification ledger, returned valid responses but failed to settle with `LedgerError("provider response is invalid")`. Google response IDs can start with `-`, for example `-NWwasf4MsGlg8UP69rl8QU`, and the ledger needs an alphanumeric first character. The author estimated about 24% of calls hit this regex.
- **Retry loop.** An unresolved call makes the pipeline rerun that member with the same deterministic ID, which then collides with the ledger's duplicate-request guard. The loop costs nothing. The overnight session stopped the pilot.
- **Accounting.** Replaying the 8 stuck responses against a disposable ledger copy gave $0.1014 of added spend. The ledger reported $0.448; the author put the true pilot total at about $0.55.
- **Left open that morning.** The `responseId` regex (it validates other fields too); the retry and attempt-id scheme (the schema has an unused `retry_of` field); `Ledger.allocate()` cannot release an allocation; the $190 and $180 ceilings are enforced per ledger file, not globally.
- **Not done.** No further live runs, no cap raised, no merge or push.

## Addendum (2026-09-22): block 00069/42 v6

Merged from `SCIENTIFIC_CAMPAIGN_ADDENDUM_2026-09-22.md`. Every figure here is also in `tyrone_mirror/DEVIATIONS.md` #91 and `docs/audit/2026-09-26-remote-audit.md`.

- The last fresh attempt stopped at 19.5 m, after stages 0 to 6 completed and stage 7 began. It added $18.552664 of settled spend. The shared scientific ledger then stood at $36.783435 settled, with no unresolved or reserved requests and no rise in redundant settlement.
- **Pinned checkout.** Byte-identical against a fresh 616-file baseline.
- **Limit.** 2,233 settled requests used $159.976812 of the $160 allocation's reservation sum, though they cost $36.783435. The pipeline then failed closed with `AccountingHalt("allocation exhausted")`. Retries made no new provider calls. A new allocation did not fit in the remaining $6.50 of code-ceiling headroom, and the ledger rules were not changed.
- **Offline scoring.** Run at commit `5c178e2` under `official_asp` and `validator_plus_unanimity_raw_tau_1_0`. It is kept on the host at `/workspace/runs/prospective_gemini/scientific_campaign_20260922/offline_scoring_20260922/block_00069_42_v6/summary.json`. Stages 0 to 6 have complete four-member tracks. Stage 7 is a partial artifact, marked by missing completion files. The three earlier zero-spend startup attempts (`v3`, `v4`, `v5`) are kept too.
