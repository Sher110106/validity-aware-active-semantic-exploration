# History, archive guide and removed docs

This file holds what the other docs no longer repeat.

- [Timeline](#timeline), project start to 12 Nov 2026
- [Archive guide](#archive-guide), what `docs/archive/` holds and why
- [Removed or merged docs](#removed-or-merged-docs), with the commit that still holds each
- [Dangling names](#dangling-names), old file names that frozen records still use
- [Paths that must not move](#paths-that-must-not-move)

Times are IST. Every number names the file it comes from. Where a fact cannot be checked from the repo, the text says so.

## Timeline

### Aug to Sep 2026: proposal, offline tools, supervisor

| Date | Event | Source |
|---|---|---|
| 31 Aug | Proposal revision (3 pages, A4). The research notes were last updated this day. Anything earlier is not verifiable from the repo. | `docs/archive/IMPLEMENTATION_RESEARCH.md` |
| 13 Sep | First commit: offline ASP extension tools. Session report written the same day. | commit 6e9c2ee; `docs/archive/SESSION_REPORT_2026-09-13.md` |
| 14 Sep | Offline validation hardened. 25 m ASP probe recorded. Support-threshold policy added. First real ablation run. Review written. | commits 4a08be0, 578c627, 9897047, 34cdfd8; `docs/archive/REVIEW_2026-09-14.md` |
| 16 Sep | Matrix supervisor module added (commit f86a650). Paper assessment written. | `docs/archive/MATRIX_SUPERVISOR_BUILD_2026-09-16.md`; `docs/archive/PAPER_ASSESSMENT_UPDATE_2026-09-17.md` (appendix) |
| 17-18 Sep | Phase 13 diagnostics. Offline implementation and v5 evidence frozen on 18 Sep (commits 4f0802e, 00c38bb). | `docs/archive/PHASE13_DIAGNOSTICS_2026-09-17.md` |
| 18 Sep | Prospective Gemini campaign code built: control plane, budget ledger, runtime overlay, motion and detour logging. | commits e08cd96 to 1598fec |
| 21 Sep | Scoring fixed for the real campaign graph format (commit 5c178e2). Engineering pilot: the byte-count reservation bug, the allocation ratchet, the seed overflow fix. | `docs/archive/SCIENTIFIC_CAMPAIGN_REPORT_2026-09-22.md` |
| 22 Sep | Overnight native-count fix and pilot re-run. Gemini response ids starting with a hyphen broke the ledger. Scientific campaign report and partial analysis written. | same; `docs/archive/GEMINI_PARTIAL_ANALYSIS_2026-09-22.md` |

### 26-27 Sep 2026: closeout

26 Sep (commit 573ab84, "Document closeout: architecture, corrected accounting, mirrored matrix replays"). It held:
- the rewritten `README.md` and a repository map;
- `docs/ARCHITECTURE.md`;
- the remote audit (now `docs/audit/2026-09-26-remote-audit.md`) and `docs/audit/2026-09-26-ledger-summary.json`;
- the three matrix static-replay JSON files in `tyrone_mirror/runs/matrix120m_scoring/`, with `STATIC_REPLAY_SHA256SUMS`;
- corrected accounting in the final report ($37.353274 settled; the v6 block as a subset);
- the results index pointed at the mirrored replays;
- `docs/REPRODUCE.md` split into inspect, fixture-test, local-replay and host-only tiers.

Also on 26 Sep:
- Paper drafted (4 pages, A4, Tables I-III) as `paper/Validity_Aware_Active_Semantic_Exploration.docx` and PDF.
- The host supervisor service was retired with the owner's approval. State, status, event log and the 00853 pipeline log were saved on the host first. The supervisor `CONTROL.json` was left byte-identical.
- The 00853 traceback was ruled a post-budget false positive. Scoring was intact. The original log is in the host snapshot.
- Three early ledger requests stayed `DISPATCHED` with unknown settled cost (`docs/audit/2026-09-26-dispatched-resolution.md`). They are not counted as zero.

27 Sep:
- GPT-6 Luna made the final documentation and paper corrections: citations, guardrail wording, full-graph retention qualifiers, heading pagination. All three result tables were kept.
- Test counts verified, with 9 subtests (source: `FINAL_REPORT.md`, Verification, at 675b2c0):

| Suite | Tests |
|---|---:|
| `tools/tests` | 186 |
| Gemini ledger | 21 |
| prospective campaign | 14 |
| prospective evaluation | 11 |
| matrix supervisor | 43 |
| evaluator fixtures | 11 |
| **Total** | **286** |

- The input manifest lists 1,702 files: 92 match local copies, 1,607 are host-only, three differ (`docs/audit/2026-09-27-closeout-verification.md`).
- Commit 675b2c0 recorded the closeout. Runtime source was unchanged from 79354e1.

### 27 Oct to 3 Nov 2026: live campaign (source: the 3 Nov handoff, §1)

| Date | Event | Where |
|---|---|---|
| 27 Oct, evening | Project reopened and read through. Errors found in the September closeout docs: a claim that 3 of 9 Gemini blocks never ran (not verifiable from the repo; `docs/RESULTS.md` Errata); "bit-identical at beta <= 1" is false. Just after midnight: the unanimity headline equals deleting all guesses. | `tools/live_policy/results_2026-10-31/WRITEUP.md` §9 errata |
| 28 Oct, 01:00-03:00 | DeepSeek V4.1 Flash 1017 chosen (fp8, $40 cap). Plan written and reviewed. Where the reviewer and planner disagreed, the placebo spec and pacing schedule of the planner were taken. Human-label reference graphs built for 00853 and 00871. E1 pre-registered and hashed. Wave 1 (six runs) started 02:55. | `tools/live_policy/OVERNIGHT_REPORT_2026-10-28.md`; `PREREGISTRATION_E1.md`, `_E2.md` |
| 28 Oct, 03:59-05:15 | Host ran out of memory. The kernel killed processes at 03:59 and 04:10. The runners misread the failed checks and lost all six runs. From 05:15 one pair ran at a time. | DEVIATIONS items 1-8 |
| 28 Oct, night | September stage-0 "noise" traced to maps carried over between launches. Gemini 3.8 Flash against DeepSeek on 8 saved inputs: $39.60 of Gemini credit. | `OVERNIGHT_REPORT_2026-10-28.md` |
| 28 Oct, 10:03-22:39 | All E1 and E2 runs queued: `campaign_chain.sh`, then the memory-aware `campaign_sched.py` from 22:39. | DEVIATIONS items 14-18 |
| 28 Oct, 17:40 | First check-in deck built. | `docs/checkin/` |
| 28 Oct, 19:30 | Fable review: continue with changes. | `docs/checkin/FABLE_REVIEW_2026-10-28.md` |
| 28 Oct, 22:31 to 29 Oct | Final plan v4: observed_only and E1 seed 45 dropped, E3 added. E3 pre-registered 23:48. All runs finished 20:58 on 29 Oct. Package built 22:02, then two rounds of independent review. | `FINAL_PLAN_2026-10-29.md`; `PREREGISTRATION_E3.md`; DEVIATIONS items 19-35 |
| 29 Oct, 15:43 | Two Opus reviews (mechanism; paper and field), merged into a 10-step plan. | `docs/checkin/review_2026-10-29/` |
| 29 Oct, 22:19 to 30 Oct | Steps 6-8 ran under three new pre-registrations. Steps 9-10 did not run, because step 6 found no rule worth taking live. An independent review gave 38 confirmed findings (about 30 distinct problems), all fixed. | `STEPS_6_TO_10_OUTCOMES.md`; WRITEUP §12; DEVIATIONS items 36-39 |
| 2-3 Nov | Questions answered in chat. 3 Nov handoff and end-sem plan written. | `docs/ENDSEM_PLAN_2026-11-03.md` |

Main result (WRITEUP §1-3): on two homes, DeepSeek guesses did not detectably beat random guesses of the same shape (E1 +0.013 [-0.012, +0.040], p 0.22). The validator did not detectably help (E2 +0.003). Neither beat plain frontier exploration in step 7.

### 6-12 Nov 2026: paper-scale work (sources: end-sem plan §B7, `docs/STATUS_2026-11-12.md`)

| Date | Event |
|---|---|
| 6 Nov | `PREREGISTRATION_PAPER.md` hashed 17:00, before any new run. Amendment 1 at 17:04. Hash taken again at 17:59 (sha256 fee16733...), before any new data. Scoring follows the author's scripts: his F1, and gmatch4py `GraphEditDistance(1, 1, 1, 1)`. The first run (e7 853/42) hit CUDA out of memory at 17:01 beside another user's GPU job and was stopped. A queue that waits for 12 GB free started about 17:40. |
| 9 Nov, about 09:23 | Host dropped off the network and restarted. The queue died before it launched anything. |
| 9 Nov, 16:20 | An agent on the host restarted the queue with all 15 jobs (brief v1). The dry run started at 16:25. |
| 9 Nov, 17:52 | Handover to the fixed queue by control script v2 (see below). |
| 9 Nov, 17:57 | Fixed queue started e7 871/42 with 13 jobs left. E7 853/42 had logged `Exploration complete` at 17:29, so it counts as finished. |
| 9-10 Nov | Runs went ahead with the GPU gate lowered to 5 GB. Brief v3 was never applied, so no DSG file was compressed. |
| 11 Nov | Host rebooted (STATUS §5). |
| 12 Nov | `zstd` installed in the container and every paper run compressed and tested (free disk 14 to 40 GB). Paper-scale scores finished (`tools/live_policy/results_paper_compare_1112/`). Check-in 2 deck built. Cleanup of the repo for the public push. |

9 Nov queue detail:
- **Why v2.** The explorer's output is block-buffered when written to a file, so `Exploration complete` never reached the log while it idled, and the queue ended every finished run as `stalled`, 20 minutes late. Review also found the queue applied its 250 m stop to tours, though pre-registration §2b gives tours only a 4 h cap. Both fixed in `paper_queue.sh` (sha256 6ffb5601...): `PYTHONUNBUFFERED=1`, and the 250 m stop for e7 jobs only.
- **Reviewed script hashes** (brief v1, step 5, and brief v2). First column is the start of the sha256:

| Script | sha256 starts |
|---|---|
| `paper_queue.sh`, first version | 46f4d0d3 |
| `paper_queue.sh`, fixed version | 6ffb5601 |
| `run_coverage_tour.sh` | 3e8d7af6 |
| `stop_coverage_tour.sh` | 5067d41e |
| `run_frontier_seed.sh` | 9c2c7034 |
| `coverage_tour.py` | d05b42f7 |
| `tour_waypoints.py` | 1b61cdcf |

- **Control script v2** did the 17:52 handover. sha256 `2b71ee2035eb10f755ff62f2aa8aa8bcca1efc1c1ce09bb7d7973f12439be83f`. The exact copy is `tools/live_policy/host/paper_queue_ctl_v2_2b71ee20.sh`. Its header line still names the brief of that day by its old file name (see [Dangling names](#dangling-names)).
- **Brief v3 was never applied.** It would have moved the queue into its own systemd scope, installed `zstd`, and made a tour that hits the 4 h cap count as a normal end. Its control script has hash 1fef22f7... and is kept as `tools/live_policy/host/paper_queue_ctl.sh`. The 5 GB-gate `paper_queue.sh` that later runs used is host-only: its hash is not verifiable from the repo.
- **Outcome of the runs** (STATUS §1-2, plan §B7): all five e7 853 runs and e7 871/46 finished; e7 871 seeds 42-45 crashed twice each (nvblox out of GPU memory); APR-a tours usable on both homes; APR-b tours unusable (Hydra's backend wrote no new graph after the first stop). Open at 12 Nov: reruns of APR-b and e7 871 seeds 42-45, about 8 GPU hours.

## Archive guide

`docs/archive/` holds dated records of the September work. They explain how the final evidence was reached. They are not current results. Use these for current facts:

- `docs/RESULTS.md`: results map and errata.
- `docs/REPRODUCE.md`: commands.
- `tyrone_mirror/DEVIATIONS.md`: engineering log.
- `docs/STATUS_2026-11-12.md`: current state.

Four groups, after the merges listed below:

| Group | Files |
|---|---|
| Proposal and implementation contract | `IMPLEMENTATION_PLAN.md`, `IMPLEMENTATION_RESEARCH.md` |
| Session records and reviews | `SESSION_REPORT_2026-09-13.md`, `REVIEW_2026-09-14.md`, `PAPER_ASSESSMENT_UPDATE_2026-09-17.md` (with the 16 Sep assessment as an appendix), `PHASE13_DIAGNOSTICS_2026-09-17.md` |
| Supervisor build set (16 Sep) | `MATRIX_SUPERVISOR_BUILD_2026-09-16.md`: the old SPEC, with GOAL, CONTROL, PLAN, NOTES and ATTEMPTS merged in as sections |
| Campaign reports (21-22 Sep) | `SCIENTIFIC_CAMPAIGN_REPORT_2026-09-22.md` (with the pilot report, morning report and addendum as dated sections), `GEMINI_PARTIAL_ANALYSIS_2026-09-22.md` |

Also `proposal_explainer/`: the original course-proposal web page. It is not the results presentation.

Corrections to the old archive README:
- It said three groups and listed four.
- It filed `PLAN.md` with the proposal contract. `PLAN.md` was the 16 Sep matrix supervisor plan.
- It said "the campaign is frozen". That means the September Gemini campaigns. The October and November live work is described in `docs/RESULTS.md`.

Nothing in the archive authorizes a paid run.

## Removed or merged docs

Git keeps every file. Recover one with:

```
git show <commit>:<path>
```

The commit is the last one that changed the file. Run `git log --oneline -- <path>` to see its history.

| Path | Last commit holding it | Content now in |
|---|---|---|
| `FINAL_REPORT.md` | 675b2c0 | `docs/RESULTS.md` (v3-vs-v5 caveat, Gemini accounting, the finding that calibration harms at some thresholds and the risk term is inactive or counterproductive); `docs/ARCHITECTURE.md` (safeguards); test counts in the Timeline above |
| `docs/REMAINING_WORK.md` | 675b2c0 | Timeline, 26-27 Sep |
| `docs/HANDOFF_2026-11-03.md` | 7b7e9db | Timeline (27 Oct-3 Nov); errata in `docs/RESULTS.md`; host traps in `tools/live_policy/README.md`; check commands in `docs/REPRODUCE.md` |
| `docs/STANDING_2026-11-06.md` | 7b7e9db | `tools/live_policy/results_paper_compare_1112/NOTES.md` and `tools/live_policy/results_paper_compare/NOTES.md` (11-06 reading); author email draft in the end-sem plan §B6 |
| `docs/TYRONE_AGENT_BRIEF_2026-11-09.md` (v1) | 7b7e9db | Timeline, 6-12 Nov |
| `docs/TYRONE_AGENT_BRIEF_2026-11-09_v2.md` | 7b7e9db | Timeline; control script kept as `tools/live_policy/host/paper_queue_ctl_v2_2b71ee20.sh` |
| `docs/TYRONE_AGENT_BRIEF_2026-11-09_v3.md` | 7b7e9db | Timeline; runbook in `tools/live_policy/README.md` |
| `docs/prospective_campaign/CONTROL.md` | e08cd96 | `tools/prospective_campaign/README.md` ("Controls") |
| `docs/prospective_campaign/GOAL.md` | c41cc31 | same (scorecard, seed 43/44 admission rule) |
| `docs/prospective_campaign/PLAN.md` | 886e351 | same (open item, scope decision) |
| `docs/prospective_campaign/STATUS.md` | c41cc31 | same (nothing new beyond the README) |
| `docs/prospective_campaign/WORKING_MEMORY.md` | e08cd96 | same (its one rule) |
| `docs/archive/README.md` | c41cc31 | Archive guide above; three-line pointer left in its place |
| `docs/archive/ATTEMPTS.md` | c41cc31 | `docs/archive/MATRIX_SUPERVISOR_BUILD_2026-09-16.md` ("Attempts log") |
| `docs/archive/CONTROL.md` | c41cc31 | same ("Governance") |
| `docs/archive/GOAL.md` | c41cc31 | same ("Build order and rules") |
| `docs/archive/PLAN.md` | c41cc31 | same ("Deployment state") |
| `docs/archive/NOTES.md` | c41cc31 | same ("Notes") |
| `docs/archive/ENGINEERING_PILOT_REPORT_2026-09-21.md` | c41cc31 | `docs/archive/SCIENTIFIC_CAMPAIGN_REPORT_2026-09-22.md` ("Night 1: engineering pilot") |
| `docs/archive/MORNING_REPORT_2026-09-22.md` | c41cc31 | same ("Night 2 morning") |
| `docs/archive/SCIENTIFIC_CAMPAIGN_ADDENDUM_2026-09-22.md` | c41cc31 | same ("Addendum") |
| `docs/archive/PAPER_ASSESSMENT_2026-09-16.md` | 20e250b | `docs/archive/PAPER_ASSESSMENT_UPDATE_2026-09-17.md` (appendix) |
| `docs/checkin/review_2026-10-29/AUDIT_objective_builder.md` | 7b7e9db | `AUDIT_objective_verified.md`, "Builder's method and caveats (first draft)" |
| `docs/checkin/review_2026-10-29/AUDIT_tables_builder.md` | 7b7e9db | `AUDIT_tables_verified.md`, same heading |
| `tyrone_mirror/ged.py` | 4f0802e | `tools/evaluator/ged.py` (byte-identical) |
| `tyrone_mirror/run_manifest.py` | 4f0802e | `tools/run_manifest.py` (byte-identical) |
| `tyrone_mirror/convert_frontier_reference.py` | 4f0802e | `tools/convert_frontier_reference.py` (byte-identical) |
| `docs/RESULTS_INDEX.md` (renamed) | 675b2c0 | `docs/RESULTS.md` |
| `docs/REMOTE_AUDIT_2026-09-26.md` (renamed) | 7b7e9db | `docs/audit/2026-09-26-remote-audit.md` |
| `docs/gemini_campaign/README.md` (renamed) | c41cc31 | `tools/gemini_campaign/README.md` |
| `docs/prospective_campaign/SPEC.md` (renamed) | c41cc31 | `tools/prospective_campaign/README.md` |
| `docs/archive/SPEC.md` (renamed) | c41cc31 | `docs/archive/MATRIX_SUPERVISOR_BUILD_2026-09-16.md` |

Notes:
- For the five renames, the old paths exist up to 7b7e9db, the parent of the rename commit 20a8437. `git log --follow` on the new path also finds the old history.
- Check the target file if a detail matters.
- No private copy of the briefs or handoff is kept. Git history is the only copy.

## Dangling names

Frozen or merged records still use these names. The files are gone or renamed. Read each as a pointer to the "now in" column above.

| Name used | Where | Read as |
|---|---|---|
| `SPEC.md`, `PLAN.md`, `ATTEMPTS.md`, `NOTES.md`, `CONTROL.md`, `GOAL.md` | inside the merged `MATRIX_SUPERVISOR_BUILD_2026-09-16.md` (old GOAL and CONTROL named each other) | sections of that file |
| `SPEC.md` | `tyrone_mirror/DEVIATIONS.md` item 86 ("per its own SPEC.md"); frozen | `docs/archive/MATRIX_SUPERVISOR_BUILD_2026-09-16.md` |
| `ENGINEERING_PILOT_REPORT_2026-09-21.md` | the morning-report section of the campaign report | "Night 1: engineering pilot" section of `SCIENTIFIC_CAMPAIGN_REPORT_2026-09-22.md` |
| `PAPER_ASSESSMENT_2026-09-16.md` | opening lines of `PAPER_ASSESSMENT_UPDATE_2026-09-17.md` | the appendix of `PAPER_ASSESSMENT_UPDATE_2026-09-17.md` |
| `FINAL_REPORT.md` | `docs/checkin/review_2026-10-29/CONTEXT_given_to_reviewers.md` (frozen record of what reviewers were given) | `docs/RESULTS.md` |
| `docs/TYRONE_AGENT_BRIEF_2026-11-09.md` | header of `tools/live_policy/host/paper_queue_ctl_v2_2b71ee20.sh` (hash-pinned copy) | brief v1 (the 16:20 restart); see Timeline |
| `docs/TYRONE_AGENT_BRIEF_2026-11-09_v3.md` | header of `tools/live_policy/host/paper_queue_ctl.sh` | brief v3; never applied; see Timeline |
| `docs/STATUS_2026-11-12.md` | `docs/checkin_2026-11/SOURCES.md` (cites "§3") | unchanged: the dated name stays |
| `PREREGISTRATION_SEMANTIC.md`, `PREREGISTRATION_E6_CLAUDE.md`, `NOT_A_GATE_PASS.md` | plans and logs | planned files that never existed (named in `PREREGISTRATION_PAPER.md`, the end-sem plan and `tyrone_mirror/DEVIATIONS.md`; not in the repo) |

Other links that stay dead for public readers: `output/`, `.firecrawl/`, and host-only files.

## Paths that must not move

Hashes, frozen citations or code lock these paths. Edit prose in them only where a plan item says so.

| Path | Locked by |
|---|---|
| `tools/live_policy/PREREGISTRATION_*.md`, `PREREGISTRATION_{BENCH,PAPER}.sha256` | their own hashes; E1-E3 hashes pinned in the copy manifest and WRITEUP §10 |
| `tools/live_policy/results_2026-10-31/**` (WRITEUP, DEVIATIONS 1-39, `numbers.csv`, manifests, `scripts/`, generated tables) | `POST_CAMPAIGN_MANIFEST.sha256` and the copy manifest |
| `tools/live_policy/oracle_sets.json` | copy manifest line 9657 names it; `live_policy.py` reads it |
| `tools/live_policy/{live_score,e1_analysis,stage_diagnostics,live_policy,live_runner}.py`, `host/campaign_sched.py`, `run_live_run.sh` | hashes recorded in WRITEUP §10, PREREGISTRATION_E3, PREREGISTRATION_DETERMINISM and the October DEVIATIONS |
| `tools/live_policy/host/{paper_queue,coverage_tour,run_coverage_tour,run_frontier_seed,stop_coverage_tour,tour_waypoints}` | hashes recorded in the control scripts |
| `tools/live_policy/review_2026-10-29/` beside `results_2026-10-31/` | `post_campaign_numbers.py` reads across them |
| `tools/live_policy/results_paper_compare/ged/` | the 12 Nov run reads it |
| `tools/asp_offline/*`, `extension_policy_replay.py`, `phase13_diagnostics.py`, `decision_replay.py`, `tools/evaluator/*` | input manifest and run_manifest JSONs |
| `tools/` layout, `tools/fixtures`, `tools/legacy`, top-level September scripts | host copy of `tools/`; manifest paths; REPRODUCE commands; tests |
| `tyrone_mirror/` (name and `runs/**`) | frozen run_manifest JSONs use `tyrone_mirror/runs/...` paths |
| `tyrone_mirror/DEVIATIONS.md`, `tyrone_mirror/run_llm_pipeline_scene.sh` and the other launch scripts | DEVIATIONS cites; `matrix_supervisor/host.py` calls the launch script |
| `docs/audit/2026-09-27-*`, `docs/audit/*` | cited by the closeout verification and paper provenance |
| `docs/ENDSEM_PLAN_2026-11-03.md` | `PREREGISTRATION_PAPER.md` names it |
| `docs/STATUS_2026-11-12.md` | `docs/checkin_2026-11/SOURCES.md` cites it |
| `docs/checkin/**` prose, `FABLE_REVIEW_2026-10-28.md`, `build_checkin_pptx.py` | hashed WRITEUP and `numbers.csv`; check-in 2 imports the builder |
| `tools/live_policy/{FINAL_PLAN_2026-10-29,OVERNIGHT_REPORT_2026-10-28}.md` | frozen citations; the hashed October DEVIATIONS item 5 repeats the report |
| `docs/prospective_overlay/README.md`, overlay `llm_completion.py` | overlay manifest hash |
| `docs/archive/PAPER_ASSESSMENT_UPDATE_2026-09-17.md` | `paper/README.md` links it |
| `docs/archive/{IMPLEMENTATION_RESEARCH,IMPLEMENTATION_PLAN,REVIEW_2026-09-14,SESSION_REPORT_2026-09-13}.md` | code docstrings and DEVIATIONS cite them |
| `docs/archive/{PHASE13_DIAGNOSTICS_2026-09-17,GEMINI_PARTIAL_ANALYSIS_2026-09-22}.md` | DEVIATIONS cites them |
| `paper/Validity_Aware_Active_Semantic_Exploration.{docx,pdf}` | the deliverable; errata go in `paper/README.md` |
