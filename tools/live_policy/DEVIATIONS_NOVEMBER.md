# Deviations, November 2026 (paper-scale runs and the end-sem plan)

This file continues `results_2026-10-31/DEVIATIONS.md`, which ends at item 39 and is pinned by hash. Items here start at 40. They record departures from `PREREGISTRATION_PAPER.md`, from `docs/ENDSEM_PLAN_2026-11-03.md`, and later from `PREREGISTRATION_SEMANTIC.md`. Times are IST.

40. **11-09 19:46: the queue's free-GPU check was lowered from 12 GB to 5 GB.** The student asked for the runs to go ahead beside another user's GPU job, which held about 41.5 of the card's 48 GB. Every paper run from then until 11-10 15:07 used the 5 GB check. The reviewed script (sha256 6ffb5601…) waits for 12 GB.
    - Effect on e7: 871 seeds 42-45 crashed (item 41). 853 seeds 43-46 and 871 seed 46 finished with no GPU error.
    - Effect on the tours: nvblox ran out of GPU memory partway through APR-a on 853, APR-a on 871 and APR-b on 871. Both APR-b tours ended with a final graph equal to their stage-0 graph.

41. **11-10 12:08: a second attempt of e7 871 seeds 42-45, which the pre-registration does not provide for.** The first attempts (11-09 17:57 to 11-10 05:20) ended at 85.4, 54.5, 80.2 and 80.7 m; the second (11-10 12:13 to 15:06) at 57.7, 27.7, 26.7 and 15.4 m. In all eight, nvblox ran out of GPU memory. None counts as a frontier-to-end run.

42. **11-12: checks C1-C5 were not reported first.** §3 says they are reported before any arm is scored against APR. They were computed in the same session as the first APR scoring.

43. **11-12: no outside time stamp before the first scores.** `PREREGISTRATION_PAPER.md` was hashed on 11-06 (17:59), but the hash lived only in a local file. The file was first committed and pushed on 11-12 at 16:39 (commit 666b53f), after the first paper-scale scoring that day. The end-sem plan's amendment 20 (an outside time stamp before any number) was therefore not met for this file.

44. **11-12: compression came late.** §2a says each stage's DSG files are compressed after conversion. The container had no `zstd` until 11-12, so no file was compressed before then. On 11-12 every finished paper run was compressed and tested (`scratch/compress_1112.log` on the host).

45. **11-13 17:02: a third attempt of e7 871 seeds 42-45 and a rerun of both APR-b tours,** under the reviewed 12 GB check, with no other GPU job running at launch. `PREREGISTRATION_PAPER.md` Amendment 2 (hashed 11-13 17:54) fixes how they are read. It was written while the 853 APR-b rerun was running (waypoint 72 of 85) and before the 871 APR-b rerun or any third e7 attempt had started. No rerun had been scored.

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
