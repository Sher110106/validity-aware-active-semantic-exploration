# Deviations, November 2026 (paper-scale runs and the end-sem plan)

This file continues `results_2026-10-31/DEVIATIONS.md`, which ends at item 39 and is pinned by hash. Items here start at 40. They record departures from `PREREGISTRATION_PAPER.md`, from `docs/ENDSEM_PLAN_2026-11-03.md`, and later from `PREREGISTRATION_SEMANTIC.md`. Times are IST.

40. **11-09 19:46: the queue's free-GPU check was lowered from 12 GB to 5 GB.** The student asked for the runs to go ahead beside another user's GPU job, which held about 41.5 of the card's 48 GB. Every paper run from then until 11-10 15:07 used the 5 GB check. The reviewed script (sha256 6ffb5601…) waits for 12 GB.
    - Effect on e7: seven of the eight crashed attempts of 871 seeds 42-45 ran under the 5 GB check (item 41). The eighth, the first attempt of seed 42, launched earlier (11-09 17:57) under the 12 GB check with 46.9 GB free, and still lost nvblox to GPU memory when another user's job grew during the run: the check acts only at launch. 853 seeds 43-46 and 871 seed 46 finished with no GPU error.
    - Correction to `results_paper_compare_1112/NOTES.md`, item 8: it says every 871 crash came from sharing the GPU at launch. The first attempt of seed 42 had the GPU to itself at launch.
    - Effect on the tours: nvblox ran out of GPU memory partway through APR-a on 853, APR-a on 871 and APR-b on 871. Both APR-b tours ended with a final graph equal to their stage-0 graph.

41. **11-10 12:08: a second attempt of e7 871 seeds 42-45, which the pre-registration does not provide for.** The first attempts (11-09 17:57 to 11-10 05:20) ended at 85.4, 54.5, 80.2 and 80.7 m; the second (11-10 12:13 to 15:06) at 57.7, 27.7, 26.7 and 15.4 m. In all eight, each run's `roslaunch.log` shows nvblox out of GPU memory; the queue itself recorded two as `host_memory_stop` and six as `stalled`. None counts as a frontier-to-end run.

42. **11-12: checks C1-C5 were not reported first.** §3 says they are reported before any arm is scored against APR. They were computed in the same session as the first APR scoring.

43. **11-12: no outside time stamp before the first scores.** `PREREGISTRATION_PAPER.md` was hashed on 11-06 (17:59), but the hash lived only in a local file. The file was first committed and pushed on 11-12 at 16:39 (commit 666b53f), after the first paper-scale scoring that day. The end-sem plan's amendment 20 (an outside time stamp before any number) was therefore not met for this file.

44. **11-12: compression came late.** §2a says each stage's DSG files are compressed after conversion. The container had no `zstd` until 11-12, so no file was compressed before then. On 11-12 every finished paper run was compressed and tested (`scratch/compress_1112.log` on the host).

45. **11-13 17:02: a third attempt of e7 871 seeds 42-45 and a rerun of both APR-b tours,** under the reviewed 12 GB check, with no other GPU job running at launch. `PREREGISTRATION_PAPER.md` Amendment 2 (hashed 11-13 17:54) sets, before the results exist, how they are read. A Note to it (hashed 11-13 18:35, after an independent review and before any 871 rerun started) corrects one statement and settles cases the amendment left open. It was written while the 853 APR-b rerun was running (waypoint 72 of 85) and before the 871 APR-b rerun or any third e7 attempt had started. No rerun had been scored.

46. **Folders (Amendment 2, A2.6), as known on 11-13 17:54.** The table is completed before any rescoring.

    | Run | Attempt 1 (11-09/10) | Attempt 2 (11-10) | Attempt 3 (11-13) |
    |---|---|---|---|
    | e7 871 s42 | `e7_00871_s42_frontier_end_FAILED_ATTEMPT_1213` | plain folder until the queue renames it | plain folder after the rerun |
    | e7 871 s43 | `…_s43_frontier_end_FAILED_ATTEMPT_1313` | as above | as above |
    | e7 871 s44 | `…_s44_frontier_end_FAILED_ATTEMPT_1358` | as above | as above |
    | e7 871 s45 | `…_s45_frontier_end_FAILED_ATTEMPT_1438` | as above | as above |
    | APR-b 853 | `apr_00853_b_FAILED_ATTEMPT_1707` (frozen) | `apr_00853_b` (rerun, 11-13 17:07) | none |
    | APR-b 871 | plain folder until the queue renames it (frozen) | plain folder after the rerun | none |

47. **11-13: changes to the end-sem plan,** made after five independent reviews of a draft (`docs/ENDSEM_FINAL_PLAN_2026-11-13.md`).
    - E6 (live Claude) is out, by the plan's own rule: M3 had not passed by 11-12 (§8, item 7).
    - M6 and H5 are cut. M2's verdict therefore stays provisional, as registered.
    - The Sonnet replay and the direct probe are cut, so the confirmatory family is 2 Claude models × 3 levels. This is fixed in `PREREGISTRATION_SEMANTIC.md` before its hash.
    - M4 runs after 11-15, the date at which §3 M3 would have stopped it.
    - The Claude backend is a direct port of the author's loop, not a patch of the genai client. Amendment 1 of the plan (the conversation store) no longer applies.
    - The one-pass driver computes F1, the room test and the validity views per stage. GED stays per run, computed on the host with the author's code.

48. **11-09: a dry run and a reversed decision, neither in §2a.** A 3-waypoint dry run of the tour ran on 11-09 at 16:25, before the registered runs. At 19:46 the queue was restarted without e7 871 seed 42 ("is not rerun"); that decision was reversed on 11-10 (item 41).

49. **11-09: two hand rulings on the queue's log.**
    - e7 853 seed 42 was logged `stalled` at 88.2 m by the older queue, which could not see the explorer's buffered output. It counts as finished because its log holds "Exploration complete" (end-sem plan §B7). The Note to Amendment 2 now states this rule.
    - APR-a on 871 was skipped at 20:56 for low host memory and requeued by hand at 21:01.

50. **11-12: scoring departures recorded in `results_paper_compare_1112/NOTES.md`,** listed here so that one log holds them.
    - End times leave out the final leg (NOTES item 5).
    - A stage without a graph takes the graph of the stage before it (item 7).
    - The 871 APR-a archive lacks stops 40-60, against "every 10 stops" in §2b, and both APR-a final graphs end about 60 s early (item 3).
    - The crashed attempts were scored in rows of their own, which §4 does not list.
    - gmatch4py was installed from its source with its package init trimmed to the GED modules, not by `pip --target` as §4 says.

51. **11-13 19:01: points the frozen semantic pre-registration left open,** settled before any score exists and before the scorer has run on any model output. `PREREGISTRATION_SEMANTIC.md` (sha256 59c97ad6…, hashed 18:59) is not edited.
    - **Thesis rows (§10).** A result can meet both "mixed" and "the claim fails": a model Supported at L1 that passes the wrong-house gate, with every model Rejected at L2 and L3. The rows apply in the table's order, so that result is "mixed".
    - **Dining at L3 (§7).** The marker table calls dining "reported only", and §7 leaves it out of L1 claims but does not say so for L3 items. A new room typed dining is left out of the L3 items too, and counted.
    - **Structure words (§6, rule 4).** The label table also maps names ending in beam, column or pillar to a structure class. Structure classes and "other" both take no part in L2 or L3, so no score changes.
    - **The head-noun step (§6, step 7)** gives a few names in other houses an odd class: "dog bed" answers to bed, although it marks no bedroom. Neither test house holds such a name; the only effect is on the other-house prior's counts.
    - **Items that reach two regions (§8).** The share is reported twice: over all regions, and over unobserved regions only.

52. **11-13 19:40: more points the frozen semantic pre-registration left open, and one disclosure,** all before the first scoring run and before the scorer's independent code review.
    - **Disclosure.** While wiring the scorer, a worker's own check script printed the wording of one secondary readout (kept against removed guesses, §11) for DeepSeek, the placebo and Gemini: whether each difference lay inside or beyond the ±5-point band. It printed no number, the scorer was not changed in response, and nothing in the repository prints a result in its dry mode.
    - **"Live stages with 8 members" (§11).** Stage 0 of a live run holds 4 members. The room test and the 2-of-8 view are reported twice: over all stages, and over the stages that hold all 8.
    - **The 2-of-8 view (§11).** The file names the paper's rule without defining it as a filter. The reading used is written in `semantic/README.md`.
    - **The prior that knows the house's size (§9).** The file does not say where the thirds are cut or how this form relates to the form with truly seen counts. Three sensitivity lines are reported: seen counts, size, and both.
    - **The room test on 4-member replays (§11).** "Before it is seen" needs later stages, which a replay of one stage does not have. The replay's count uses the states of the run the row came from.

53. **11-06 17:01: a first launch of e7 853 seed 42 that made no stage.** The earlier e7 queue launched it beside another user's GPU job; nvblox ran out of GPU memory at start, and the run was stopped by hand at 17:15 (`runs/frontier_seeds/e7_queue.log` on the host; end-sem plan §B7). Its folder, `e7_00853_s42_frontier_end_FAILED_ATTEMPT1_gpu_oom`, holds no stage graph and is in no row. Seed 42 of 853 is scored from its run of 11-09, which passes Amendment 2's test.

54. **11-13 20:25: readings where the frozen M2 pre-registration is silent,** fixed in code before its first pass ran and confirmed fair by an independent code review. `PREREGISTRATION_M2.md` (sha256 5b8a8400…) is not edited.
    - F0's "unmapped" objects are those of the yardstick's mask, taken over both tracks.
    - "The track's first F1 graph" is the first member id of that track, in the order the replay lists them.
    - n_T enters F-room's draw as a proportion and is not rounded.
    - A type with an empty label pool would get weight 0; this does not occur in either scene.
    - A member whose oracle graph fell back to placebo objects would take its count of placebo objects as F-room's N; no member fell back.
    - The secondary yardsticks leave out their own undefined stages, paired across arms.
    - The clustering by scene and seed has 6 clusters, so its interval comes from 64 sign patterns and is coarse.

55. **11-13 21:10: a check made after the confirmatory result was seen.** One verdict is close: Claude Opus at L3 is Rejected because the upper end of its interval against the region trade (D) is 0.0295, under the 0.03 margin. D is a randomised control with 200 draws per member (§9), so its draws move that end. The independent checker reran it with ten other seeds at 200 draws and five at 5,000 draws: the upper end ran from 0.0283 to 0.0298, below 0.03 in all fifteen runs, and settled near 0.029 (`results_semantic_1113/independent_recompute/margin_summary.json`). The registered result is unchanged and is the one reported; this check is reported beside it, as a check made after the fact. A seed that crossed 0.03 would have made Opus at L3 "Inconclusive" and the thesis line "Inconclusive".

56. **11-13 20:50: the no-hint replay (§11) was run after the confirmatory result was known.** Haiku on the 12 round-1 rows with the prompt's sentence about more than one bedroom and bathroom removed; 48 members, all parsed; $0.30. It is exploratory by registration.

57. **11-13 21:20: three ASP runs on 853 to the full budget, against the end-sem plan's §10** ("no new scenes, no 100 m runs"). The student approved them on 11-13, so that the paper's headline column has an ASP value of ours beside it. `PREREGISTRATION_PAPER.md` Amendment 3 (hashed 21:20, before any of the runs) sets the runs, which of them count, the readouts, and that they are never pooled with October's.

58. **11-13 21:37: a Note to Amendment 3, after an independent review and before any of its runs.** The review found one false statement: the three runs use E1's official code path, not E1's files (three files have changed since, none in the official arm). The Note corrects it, and settles what the amendment left open: when a run has reached B; that a run killed by another job's use of the GPU is not rerun; that each seed is launched on its own behind checks made by hand; what makes the dry run pass. It also changes one number: the dry run's cost limit is $1.00, not $0.30, so that the cost check cannot end it. The runs are scored as their own arm, `official_nov`.

59. **11-13 21:44: the C1 area table adds measures that §3 does not name.** C1 as registered compares the navmesh island of the start with the paper's area figure. After that gap was known (11-12), we added the labelled floor, the footprint of all labelled geometry and their convex hulls, from the HM3D semantic mesh (`results_paper_compare_1113/c1_area_table.md`, built by `c1_area.py`). The rows are descriptive; C1's own result is unchanged.
