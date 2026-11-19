# Pre-registration: scores on the paper's scale (end-sem plan, Section B, milestone P)

Written 2026-11-06 17:00 IST. At that time no tour has run, no frontier run has gone past 60 m since 10-30, and no run has been scored against a tour reference. The plan is `docs/ENDSEM_PLAN_2026-11-03.md` §B. This is a descriptive comparison with arXiv 2510.05430v2 Fig. 4 (left). It tests no hypothesis and no LLM content. The room test in Fig. 4 (right) compares LLM guesses with a chance rate, so it belongs to `PREREGISTRATION_SEMANTIC.md` and is not run under this file.

## 1. The author's rules, copied

Read on 11-06 from the host copies of `exploration/scripts/f1_score_plot.py` and `ged_score_plot.py` (commit f1ea141b).
- **Reference:** graph0 of the final stage of a run that visits the whole scene (`GT_<scene>/habitat_scene_graph_original_graph0.yaml`). The author drove that run by keyboard with `habitat_collect_hm3d.py`, through the same mapper.
- **Objects:** nodes with `node_type` object whose name is not `door`.
- **F1:** each mapped object, in file order, takes the nearest unmatched reference object with the same name. It counts as a match if that distance is below 0.5 m. Precision, recall and F1 are computed per graph, and the stage value is the mean over graph0 and graph1.
- **Plot rule:** the plotted F1 curve holds the running maximum over stages.
- **GED:** gmatch4py `GraphEditDistance(1, 1, 1, 1)` over object and room nodes, with doors dropped. Substitution costs 0 if type and name match and, for objects, the parent room names match and the centres lie within 0.5 m; for rooms, the centres lie within 4.0 m with height ignored. Any other substitution costs 1000. The stage value is the mean over graph0 and graph1.
- **Axis:** `total_navigation_time_seconds` in each stage's `navigation_stats.json`. It counts wall time spent moving, not scanning, planning or waiting on an LLM.

## 2. New runs (all $0, one at a time in container asp-noetic)

### 2a. Frontier to its natural end
- **Explorer:** the author's `frontier_baseline.py`, with the opt-in start jitter from `PREREGISTRATION_FRONTIER_SEEDS.md`.
- **Cells:** scenes 00853 and 00871, seeds 42-46. Run names are `frontier_seeds/e7_<scene>_s<seed>_frontier_end`.
- **Stop:** the explorer reports "Exploration complete", or the path reaches 250 m, or 4 h of wall clock pass.
- **Order:**
  1. 853/42 and 871/42;
  2. the four tours (2b);
  3. 853/43, 871/43, 853/44 and 871/44;
  4. 853/45, 871/45, 853/46 and 871/46.

  Seeds 45-46 run only if free disk stays above 10 GB.
- **Storage:** after the author's converter writes each stage's YAML, the stage's DSG JSON files are zstd-compressed. This is reversible.

### 2b. Coverage tours: the author-protocol reference (APR)
- **Script:** `coverage_tour.py` is the frontier explorer with its frontier planner replaced by a fixed waypoint list. Everything else is unchanged: the 360° scan at each stop, the MidPlanner A* path, the motion steps and the stage archive.
- **Waypoints:**
  - navmesh points on a 1.5 m grid on the floor that holds the author's start pose (853: (−0.5, 1.1, 4.5); 871: (−5.5, 1.1, −3.0));
  - each snapped to the navmesh, keeping only points reachable from the start;
  - a point within 0.75 m of a kept point is dropped.
- **Order:**
  - APR-a: greedy nearest by geodesic distance, from the start;
  - APR-b: the same rule, beginning at the waypoint farthest from the start. The robot still starts at the author's start pose.
- **Stop:** every waypoint has been tried. As in the frontier explorer, a waypoint the planner cannot reach within MID_PATH_TIMEOUT is skipped. The safety cap is 4 h.
- **Archive:** stage graphs are kept every 10 stops and at the end. Run names are `apr/apr_<scene>_<a|b>`.
- **Reference:** graph0 of the final stage, the author's rule.
- **Use rule:** a tour is used as a reference only if it reached at least 80% of its waypoints. APR-a is the reference. If APR-a fails the rule and APR-b passes, APR-b is used, and the swap is logged.

## 3. Checks, reported before any arm is scored against APR

None of these is a gate except the 80% use rule above.
- **C1.** Room nodes in APR-a and the navmesh area of the start floor, against the paper's figures: 853, 6 rooms and 207.63 m²; 871, 9 rooms and 235.03 m².
- **C2.** F1 of APR-b against APR-a. If it falls below 0.90, the slide says the reference moves by more than the paper's margins (2.7-7.9 points).
- **C3.** APR-a's recall against the HM3D human-label reference used by E1.
- **C4.** The classes present in APR-a, against the 52-label file `task_def/objects_habitat_apartment.yaml`.
- **C5.** APR-a's F1 against the frontier-made reference.

## 4. Scoring

- **Runs:**
  - every counted run in `results_2026-10-31/run_table.csv` (E1 official and placebo, E2 filter_only, E3 oracle_visible on 00871);
  - the six e4 frontier seeds;
  - the two frontier-made reference runs;
  - the e7 frontier-end runs.
- **References:**
  1. APR, for the paper's scale;
  2. the HM3D human-label references used by E1, for comparing arms;
  3. the frontier-made reference, for continuity only. It favours frontier, because frontier is scored against its own kind of map.
- **Budget B per scene:** the median end-of-run navigation time of the e7 runs in that scene, which is the frontier explorer's natural end.
  - If fewer than 2 e7 runs finish, B is the end of the frontier-made reference run: 853, 632 s; 871, 809 s.
  - If the author states his budget before 11-20, his figure replaces B, and the swap is logged.
- **Readouts:**
  - F1 and GED at 10%, 50% and 100% of B, each taken at the last stage whose navigation time is at most t.
  - The primary readout is the stage value. The running maximum (the author's plot rule) is reported beside it.
  - A run that ended before t has no value at t. ASP runs stopped at 60 m, so they have no 100% value.
- **Per cell:** mean, min, max and n, beside the paper's single value. No p-values.
- **Sensitivity:** B × 0.8 and B × 1.2.
- **GED method:** gmatch4py if it installs into a scratch directory (`pip --target`) in the container. Otherwise `tools/evaluator/ged.py` (NetworkX, 60 s timeout), labelled "not the author's GED".

## 5. Not changed

No registered E1-E3 or step 6-8 result changes.

## Amendment 1 (2026-11-06 17:04 IST, before any tour has run)

§2b said the tour moves along the MidPlanner A* path. Instead it moves along the simulator's navmesh shortest path between waypoints (`pathfinder.find_path`), with the explorer's own motion steps (1.5° turns and 0.075 m moves at 10 Hz) and its own 360° scan at each stop.

The reason: the author drove his reference by hand, so he could walk into rooms the map had not yet seen. MidPlanner plans on the partial occupancy map and cannot plan into unmapped space, so most far waypoints would time out. The camera poses are what shape the map; the planner only chooses them.

Waypoints the navmesh cannot reach from the start are dropped when the list is built, and the drop count is logged. The 80% use rule now counts waypoints reached against waypoints listed.

## Note (2026-11-06 17:59 IST)

The Amendment 1 heading said 17:10; the amendment was written and hashed at 17:04. The time was corrected and the hash retaken. No new run had produced any data: the queue was still waiting for GPU memory.

## Amendment 2 (2026-11-13 17:54 IST, before any third attempt of an e7 871 run has started)

**Why.** §2a has no rule for a run that crashes, and §2b's use rule counts waypoints, not maps. Both gaps opened on 11-09 and 11-10.
- E7 871 seeds 42-45 crashed in two attempts each. In every attempt nvblox ran out of GPU memory and the planner lost its map. Those attempts ran beside another user's GPU job, with the queue's free-GPU check lowered from the reviewed 12 GB to 5 GB.
- Both APR-b tours reached every waypoint, so they pass §2b's 80% rule, yet each final graph equals its stage-0 graph.

A third attempt of the four seeds and a rerun of both APR-b tours were announced on 11-12 (`docs/STATUS_2026-11-12.md` §5). They were queued on 11-13 at 17:02 IST under the reviewed 12 GB check, in this order: APR-b on 853, APR-b on 871, then e7 871 seeds 42 to 45. This amendment fixes how they are read.

**What had been seen when this was written (17:53 IST).**
- The 853 APR-b rerun was running, at waypoint 72 of 85. The sizes of its saved stage graphs had been read (they grow from stage 0), and its logs had been searched for the timeout line and the out-of-memory line (neither was present).
- The 871 APR-b rerun had not started. No third attempt of any e7 871 seed had started.
- No rerun had been scored against any reference.

**A2.1 A valid frontier-to-end run.** An e7 run counts only if all three hold:
1. it ended by a §2a stop: its explorer log holds "Exploration complete", or the queue stopped it at the 250 m or the 4 h cap;
2. its `logs/roslaunch.log` holds no "out of memory" line and no line saying that `nvblox_node` has died;
3. the graph0 of its final stage differs from the graph0 of its stage 0.

The test reads logs and files. It reads no score.

**A2.2 Which attempt counts.** For 871 seeds 42-45 the third attempt counts if it is valid. If it is not, that seed is missing: no earlier attempt takes its place, and there is no fourth attempt. Attempts 1 and 2 stay out of every paper cell and keep their own rows (`crashed_frontier_1st`, `crashed_frontier_rerun`). An invalid third attempt is reported as `crashed_frontier_3rd`.

**A2.3 Budget B, as §4 already says.** B for a scene is the median end-of-run navigation time of its valid e7 runs, once at least two exist. 871 seed 46 is valid (1,263.5 s), so one valid third attempt is enough to replace the 809.08 s fallback used on 11-12. Every 871 readout is then recomputed by script. The 11-12 values stay on file in `results_paper_compare_1112/` and are marked superseded. A run stopped by a cap enters B at its stop time and is flagged; B is also reported without such runs.

**A2.4 Frozen tours.** A tour is frozen if the graph0 of its final stage holds the same object nodes (name and centre) as the graph0 of its stage 0. A frozen tour is not used, as a reference or in check C2, whatever share of its waypoints it reached. The test is applied to every tour, APR-a and APR-b alike. For every tour the report also gives: whether nvblox died, the number of "Timeout! Did not find" lines in the tour log, and the last archived stop whose graph differs from the one before it.

**A2.5 The reference and C2.**
- APR-a stays the reference on both scenes. It is not frozen and it passes §2b's use rule, so the §2b swap does not arise.
- If an APR-b rerun is not frozen, C2 is computed for that scene and written to file before any run is rescored.
- In both APR-a tours nvblox died partway, and each final graph lacks about the last 60 s of its tour (`results_paper_compare_1112/NOTES.md`, items 3 and 4). A C2 below 0.90 therefore mixes that damage with real movement of the reference, and the slide says so.
- If an APR-b rerun is frozen again, C2 for that scene is reported as not computable. There is no further attempt.

**A2.6 Folders.** The queue moves an older attempt aside as `*_FAILED_ATTEMPT_HHMM` before a rerun. Before any rescoring, `tools/live_policy/DEVIATIONS_NOVEMBER.md` records which folder holds each attempt.

**Not changed.** §1, §3, and the readouts of §4. Like the rest of this file, the amendment tests no hypothesis.

## Note to Amendment 2 (2026-11-13 18:35 IST, before the 871 APR-b rerun or any third e7 871 attempt has started)

An independent review of Amendment 2 found one false statement and several cases the rules did not decide. This note corrects the first and settles the rest. At 18:34 IST the queue had run only the 853 APR-b rerun (17:07 to 18:04); since about 18:05 it has waited for GPU memory, because another user's job came back. No rerun has been scored.

**Correction of fact.** Amendment 2 says every crashed attempt ran with the free-GPU check lowered to 5 GB. That is wrong for one attempt. The first attempt of seed 42 launched on 11-09 at 17:57 under the 12 GB check, with 46.9 GB free, and ended at 19:01; the check was lowered at 19:46. In that attempt too nvblox ran out of GPU memory, after another user's job grew during the run. The 12 GB check acts only at launch. Also, the queue itself recorded two of the eight attempts as `host_memory_stop` and six as `stalled`; the out-of-memory cause comes from each run's `logs/roslaunch.log`.

**What had been seen, added.** When Amendment 2 was written we also knew: the 11-12 scores for 871, computed with B = 809.08 s; that any valid third attempt raises 871's B toward seed 46's 1,263.5 s; and that the 853 rerun's graph was growing past stage 0 when the frozen-tour test was written.

**A2.1, made exact.**
1. A run ended by a §2a stop if its explorer log holds "Exploration complete", or the queue logged `path_cap_250m` or `wall_clock_4h` for it. A run the queue ended for any other reason (`stalled`, `host_memory_stop`, `disk_stop`, explorer process gone) counts only if its explorer log holds "Exploration complete".
2. The search of `logs/roslaunch.log` ignores case. One "out of memory" line, or one line saying `nvblox_node` has died, disqualifies the run, wherever in the log it stands.
3. "Differs" means the test of A2.4: the two graphs do not hold the same object nodes, compared by name and by centre as written in the file.
4. The test is applied to every e7 run, including 853 seeds 42-46 and 871 seed 46, and the results are filed before any rescoring. A2.3 called 871 seed 46 valid on the strength of the 11-12 check (it logged "Exploration complete" and had no GPU error); condition 3 is still to be run on it.

A2.1 adds conditions 2 and 3 to §2a. It is a change, not a restatement.

**A2.2, one more case.** An attempt is used up when the queue logs `launch` for it. If the queue skips a job (memory, disk, or giving up on the GPU) or is stopped before launching it, that attempt has not happened and may be launched once later.

**A2.3 is a change to §4, and the primary B is now named.** §4 speaks of the runs that finish and of the explorer's natural end. So the primary B is the median end-of-run navigation time of the valid runs that logged "Exploration complete". With an even number of runs the median is the mean of the two middle values. A valid run stopped by a cap does not enter the primary B; B with such runs entered at their stop time is reported beside it.

**A2.4 and A2.5, two more cases.**
- C2 is computed for an APR-b rerun only if it is not frozen and also meets §2b's 80% rule. Whether nvblox died during it is reported with C2 and does not block it.
- The frozen-tour test is coarse by design: a tour with one new object passes. So the report also gives each tour's count of object nodes at stage 0 and at the end.

**Why an e7 run is thrown out when nvblox dies, but a tour is not.** The frontier explorer plans on the map nvblox builds. When nvblox dies it has no map to plan on, and the robot stops exploring: the run no longer shows where the explorer would have gone. A tour follows navmesh paths that do not depend on the map, and Hydra went on growing the graph after nvblox died (`results_paper_compare_1112/NOTES.md`, item 4), so the tour still visits what it was meant to visit. The damage to a tour's graph is disclosed, not ignored (A2.5).

## Amendment 3 (2026-11-13 21:20 IST, before any run below has started)

**Why.** §4 says "ASP runs stopped at 60 m, so they have no 100% value". So the paper's headline column (ASP at 100% of the budget) has no ASP value of ours beside it. Three new ASP runs on 00853 fill that cell. The student approved them on 11-13. They are descriptive, like the rest of this file.

**What had been seen when this was written.**
- Every October result, and the 853 readouts at 10% and 50% of B for ASP, the filter, the placebo and frontier, and frontier at 100% (`results_paper_compare_1112/` and the interim `results_paper_compare_1113/`, where 853 is final and equal to 11-12).
- C2 for 853: the two tours agree at F1 0.751.
- The semantic test and M2 (`results_semantic_1113/`, `results_m2_1113/`), finished the same evening. They use other data and decide nothing here.
- No run of this amendment had started. The GPU was held by another user's job, and the rerun queue of Amendment 2 was waiting before the 871 APR-b tour.

**A3.1 Runs.** `e8_00853_s<seed>_official_105m`, seeds 42, 43 and 44, one at a time in container asp-noetic, in that order.
- The arm is E1's official arm, with the same files as E1 ran: the author's pipeline at f1ea141b; `live_policy.py` (sha256 6e4710cf…), `run_live_run.sh` (25cfe606…) and `live_runner.py` (940be66b…) as they stand on the host; model `deepseek/deepseek-v4.1-flash-1017` on OpenRouter, pinned to DeepInfra fp8, no fallback, reasoning effort low, max_tokens 16,000. (On 11-13 that model was still listed with DeepInfra at fp8.) The quiet-wait option of the determinism step is left unset.
- Target path 105 m, so that navigation time passes B for 853 (632.18 s; October's official runs moved at 6.4 to 6.7 s per metre). The runner stops at the first checkpoint at or past 105 m.
- Limits: 12 h per run; $3 per run; the launcher's 3,000-call limit, unchanged (October's 60 m runs used 1,022 to 1,362 calls).
- October's scheduler is not used. The runner is started once the rerun queue has ended, the rescoring's work on the host is done, nothing else runs in the container, and at least 12 GB of GPU memory is free.

**A3.2 Which runs count.** A run counts at 100% of B if its navigation time reached B, its `logs/roslaunch.log` holds no "out of memory" line and no line saying `nvblox_node` has died (case ignored), and no E1 exclusion applies (a call not served by DeepInfra with the pinned model; more than half the members dropped). A run that ends before B, whatever the reason, has no 100% value and is reported with the values it has. There is no rerun of any kind.

**A3.3 Readouts.** §4's, at 10%, 50% and 100% of B = 632.18 s (fixed on 11-12 from the five e7 runs on 853; Amendment 2 does not change it): F1 as the stage value and as the running maximum, and GED with the author's code. One row, "ASP + DeepSeek, November", with mean, min, max and n. No p-value.

**A3.4 Not pooled.** The three runs are never pooled with October's official runs, whose rows at 10% and 50% stay as they are. The slide gives n beside every cell.

**A3.5 Dry run.** One run of 5 m (`dryrun_e8_00853_s42_official_5m`, cost limit $0.30) checks the stack after the reboot of 11-11. It is not scored. If it fails, the three runs are not started, and that is reported.

**A3.6 Not run.** 00871: its budget is not yet fixed, and its runs are longer.

**Not changed.** §1 to §3, the readouts of §4, and Amendments 1 and 2.

## Note to Amendment 3 (2026-11-13 21:37 IST, before any run of Amendment 3, the dry run included, has started)

An independent review of Amendment 3 found one false statement and several cases its rules did not decide. This note corrects the first and settles the rest. When it was written the GPU was still held by another user's job, the rerun queue of Amendment 2 was still waiting, and the campaign folder held no `e8_` folder and no dry run of this amendment.

**Correction of fact.** A3.1 says the arm runs "with the same files as E1 ran". It runs E1's official code path, not E1's files. The manifests of E1's counted official runs on 00853 give md5 9326c553… for `live_policy.py`, 2db5e73c… for `run_live_run.sh` and 6040198b… for `exploration_pipeline.py`. The host now holds eaf477c5…, 68aeef7e… and 223ed036…; the sha256 values A3.1 quotes are of these newer files. What changed between them:
- `live_policy.py`: the oracle arm, and a fresh random stream for reruns of the no-LLM arms. Both sit in the code of the no-LLM arms; the official arm does not pass through it.
- `run_live_run.sh`: one more line in the manifest.
- `exploration_pipeline.py`: the quiet-wait option, which acts only when its two variables are set. They stay unset.

`llm_completion.py` (md5 dc70801e…) and `calculate_uncertainty.py` (9cec96c6…) are the files E1 ran.

**A3.1, more.**
- Each seed is launched on its own, with its own queue file, in the order 42, 43, 44. The runner has no GPU check of its own, so before each launch these are checked by hand: the rerun queue has ended (waiting is not ended); the container holds no process but its first; at least 12 GB of GPU memory is free; at least 60 GB of host memory and 20 GB of disk are free; the four hashes above still match.
- A run is used up once the runner has started its launcher. If the runner skips it (`skipped_exists`, `skipped_campaign_cap`, `skipped_host_memory`) or the launcher fails to start (`launch_failed`), the run has not happened and may be launched once later; if a folder was left behind, the later launch adds `_relaunch1` to the name.
- A run stopped by hand, to protect the host or to end a run that is already void under A3.2, counts as a run that ended before B. We stop by hand when the run's `logs/roslaunch.log` shows a line of A3.2, or when free host memory falls under 20 GB.

**A3.2, made exact.**
- A run reached B if its last stage that holds `navigation_stats.json` and both graph files shows a total navigation time of at least 632.1751 s. Its 100% value is then read as §4 says, at the last stage whose navigation time is at most B.
- "No rerun of any kind" includes a run killed because another user's job took the GPU's memory, a run stopped by the runner (cost, calls, wall clock, stall, planning errors, host memory), and a run stopped by hand. In each case the next seed is still launched, once the checks of A3.1 pass again.
- §4's sensitivity readout at B × 1.2 needs 759 s of navigation time, about 110 to 121 m of path. A 105 m run will most likely not reach it; where it does not, that cell is empty.

**A3.5, changed and made exact.**
- The dry run's cost limit is $1.00, not $0.30. About 200 calls and the launcher's reserve for calls in flight come to about $0.27, which leaves $0.30 too little room: the cost check, not the stack, could end the dry run.
- The dry run passes if the runner launches it, it writes at least two stages, every call is served by DeepInfra with the pinned model, and its `logs/roslaunch.log` holds no line of A3.2. It is not repeated; only a dry run the runner skipped or failed to launch may be launched once more.
- No folder whose name starts with `dryrun_` is ever scored.

**Projection, on record before the runs.** From October's official runs on 00853, a 105 m run should take 31 to 39 stages, 2,030 to 2,640 calls, 5 to 10 hours, $1.5 to $2.2, and end at 660 to 723 s of navigation time. The reviewer's guess: one run in three ends before B. The likeliest cause is the shared GPU; after it, host memory on a slow night.

**Scoring.** The runs enter the tables as their own arm, `official_nov`, picked by the name pattern `e8_00853_s(42|43|44)_official_105m` (with `_relaunch1` where the rule above gave it), so that no code path can pool them with October's `official` arm.

## Amendment 4 (2026-11-19 11:35 IST, before any reply from the authors is known to us)

**Why.** §4 says: "If the author states his budget before 11-20, his figure replaces B, and the swap is logged." The mail to the authors went out on 11-18, two weeks later than the plan of 11-03 foresaw, so that date leaves them one day. An independent review of the whole project on 11-19 proposed moving the date to the day the talk's numbers freeze, before any reply comes. The student approved it the same day.

**What had been seen when this was written.**
- Every result in `results_paper_compare_1113/` as filed on 11-18, with B = 632.18 s on 00853 and 1,300.25 s on 00871.
- The review's reading that B for 00871 may be about twice the paper's. Its figures, which we have not recomputed: at 750 s our frontier reads 26.1, 43.6 and 62.4 against the paper's 29.2, 55.7 and 65.3. So a shorter budget from the authors would most likely move our 871 cells away from the paper's, not toward them.
- No reply. The student told us on 11-18 that the mail was sent, and had told us of no reply when they approved this change (11-19, about 11:25 IST). The writer of this amendment cannot see the mailbox.

**A4.1 The date.** In §4, "before 11-20" becomes "by 23:59 IST on 2026-11-24", the day the end-sem plan takes as the freeze of the talk's numbers.

**A4.2 If a reply had already come.** If a reply reached the students before the time in this amendment's heading, this amendment does not apply to what that reply holds: §4's own date governs it.

**A4.3 What counts as his budget.**
- A time in seconds for a scene replaces B for that scene. The tables are rebuilt at his B. The tables at our B are kept beside them and named as ours.
- One figure given for all scenes replaces B in both.
- A path length or a number of steps, with no time, does not replace B. A second table is then read at 10%, 50% and 100% of his path length, each at the last stage whose path is at most that length, and the slide shows both.
- If he says whether Fig. 4 shows the value at that time or the best so far, the rows beside the paper's values use the rule he names. The other rule stays in the tables.

**A4.4 Other files.** The end-sem plan says the authors' files "change part 2 only if they arrive by 11-20". That date moves with A4.1. Reference graphs or a tour path that arrive by 23:59 IST on 11-24 are scored as one more reference, named "author", in every table, and that reference becomes the paper-scale column; APR stays beside it. What arrives later is reported after the talk.

**Not changed.** The rest of §1 to §5, and Amendments 1 to 3 with their Notes.

## Amendment 5 (2026-11-19 11:55 IST, before any run below, the dry runs included, has started)

**Why.** On 00853, November's three ASP runs (`official_nov`) read above our frontier runs at equal time: by 4.8, 11.6 and 6.0 points at 10%, 50% and 100% of B, against APR. But frontier is another explorer with another clock, and at equal path the gap is 0.6 to 3.8 points against APR and has the other sign against the HM3D labels (deviation 66 and `equal_path/equal_path.md`). So that gap cannot say whether the LLM's guesses did anything. Two control arms run ASP's own pipeline, with its clock, its candidate views, its 360° scans and its travel cost, and differ from `official_nov` only in what stands in for the LLM's guesses. An independent review of the whole project asked for them on 11-19, and the student approved them the same day. They are descriptive, like the rest of this file.

**What had been seen when this was written.**
- Every result filed through 11-18: the three `official_nov` runs with all their readouts, at equal time and (deviation 66, exploratory) at equal path under all three references; the frontier runs; October's three placebo runs on 00853 to 60 m (against APR: 43.9 at 50% of B, and 42.7 at 50 m of path, where `official_nov` reads 51.1 and 48.2).
- No run of this amendment and no dry run has started. `observed_only` has never been run live on any scene.

**A5.1 Arms.**
- `placebo`: no LLM call. Each member gets the observed graph plus random rooms and objects, drawn with the measured shape statistics of the LLM's guesses (`live_policy.placebo_graph`; calibration file md5 e9af890b…).
- `observed_only`: no LLM call. Every member's completion is a copy of the observed graph of its track: no guesses at all. The members of a track are then identical, so the score sees only where the two tracks disagree, and unexplored space scores zero (the arm's own note in `live_policy.py`). It may explore little. That is the arm, not a fault.

**A5.2 Runs.** `e9_00853_s<seed>_placebo_115m` and `e9_00853_s<seed>_observed_only_115m`, seeds 42, 43 and 44: six runs, one at a time in container asp-noetic, in this order: s42 placebo, s42 observed_only, s43 observed_only, s43 placebo, s44 placebo, s44 observed_only. So a loss of the host part-way leaves the arms as even as it can.
- Files as they stand on the host, the same as for Amendment 3's runs (md5): `live_policy.py` eaf477c5…, `run_live_run.sh` 68aeef7e…, `live_runner.py` 35206d54…, `run_pipeline_with_policy.py` 215ad8ca…, `exploration_pipeline.py` 223ed036…, `calculate_uncertainty.py` 9cec96c6…. The quiet-wait option stays unset.
- Pacing. A no-LLM arm sleeps at each planning step, so that the mapping stack gets the catch-up time the LLM arm gets while it waits. The schedule is the per-stage median of `llm_wait_s` over the three `official_nov` runs (`host/pacing_update.py`, without the 500 s it adds at the end, so the last measured value repeats): `127,171,182,175,176,287,355,342,318,259,301,232,288,275,259,308,274,407,373,366,324,385,384,420,361,429,439`. It was computed on 11-19 from the three runs' `stages/*/live_policy.jsonl` files (md5 of each run's files joined in stage order: f3a44a92…, 75ae35d3…, 366d339f…).
- Target path 115 m, not 105 m. The reading of A5.6 needs 100 m. Seed 44 of `official_nov` went 112.7 m and still ended 28 s before B, and October's placebo runs moved at 5.6 to 6.1 s per metre, so 115 m should also fill most cells at 100% of B; those cells decide nothing. Every readout below is taken at a fixed time or a fixed path length, so a longer run changes no cell it shares with a shorter one.
- Limits: 12 h per run; no call is made, so the cost is $0 (the runner's cost check stays on).
- A queue script on the host starts the runs with no help from outside (`host/e9_queue.sh`, md5 7a669f0a…). Before each launch it waits until the checks of the Note to Amendment 3 pass twice, five minutes apart (`host/e8_prelaunch_check.sh`, md5 e4f8a0d6…): no runner or rerun queue of ours is live; the container holds no live process but its first; at least 12 GB of GPU memory, 60 GB of host memory and 20 GB of disk are free; the file hashes still match. If the checks have not passed after 48 hours of waiting in all, the queue ends and what is left is not run. After each run it compresses that run's raw graph files with the checked script of deviation 62 (`host/compress_old_dsg.sh`, md5 239c5a96…), so that disk does not run short.

**A5.3 Which runs count.** The rules of A3.2 and its Note, less the two about LLM calls.
- A run has a value at time t, or at path L, only if it reached it: the last stage that holds `navigation_stats.json` and both graph files shows at least that time, or that path.
- A run whose `logs/roslaunch.log` holds an "out of memory" line or a line saying `nvblox_node` has died (case ignored) has no value at 100% of B and none at 100 m; its other cells are reported and marked.
- There is no rerun of any kind: not for a run killed because another user's job took the GPU's memory, not for a run the runner stopped, not for a run stopped by hand. Only a run the runner skipped or failed to launch has not happened, and may be launched once later (with `_relaunch1` added if a folder was left).
- The queue script checks every 30 s and asks the runner to stop the run when its log shows one of the two lines above, or when two readings of free host memory 15 s apart are both under 20 GB (the rule deviation 64 set). No one decides by hand. A run stopped this way ends at its last full stage.

**A5.4 Dry runs.** One 5 m run per arm (`dryrun_e9_00853_s42_placebo_5m`, `dryrun_e9_00853_s42_observed_only_5m`) with the same schedule, through the same queue script. We read them by hand before the six runs are queued. A dry run passes if the runner launches it, it writes at least two stages, every line of its `live_policy.jsonl` names the arm's policy, no LLM call is logged, and its `roslaunch.log` holds neither line of A5.3. For `observed_only`, every member in those lines must also show zero predicted nodes. A dry run is never scored and never repeated (one the runner skipped or failed to launch may be launched once more). If an arm's dry run fails, that arm's three runs are not started, the other arm's go on, and this is reported.

**A5.5 Readouts.**
1. §4's, at 10%, 50% and 100% of B = 632.18 s: F1 as the stage value and as the running maximum, and GED with the author's code, against all three references. Two rows, `placebo_nov` and `observed_only_nov`, picked by the name patterns above, each with mean, min, max and n. They are never pooled with October's placebo runs.
2. F1 (stage value) at equal path: 50, 60, 80 and 100 m, each at the last stage whose path is at most L, against all three references, for `official_nov`, `placebo_nov`, `observed_only_nov` and `frontier_end`. For the two new arms this readout is registered here. For `official_nov` and `frontier_end` it was first made after their results were seen (deviation 66) and stays marked so.
3. Seconds of navigation time per metre, per arm.

**A5.6 The reading, fixed now.** The question: on 00853, do ASP's runs with the LLM's guesses read above the same pipeline with random guesses, or with none?
- For each run, S is the mean of its F1 at 50, 60, 80 and 100 m of path. It is taken twice: against APR, and against the HM3D labels. A run that did not reach 100 m has no S. Path, not time, because the three arms share one clock and the paper's own Fig. 3 is drawn against path. The equal-time cells of readout 1 are shown beside it and decide nothing.
- `official_nov` is the three runs as they ran, seed 43 included. The other readings of seed 43 (deviation 64) are shown beside it and decide nothing.
- A control arm is judged only if every `official_nov` run and at least 3 of its own runs have S. Otherwise that arm gets "no statement", and its S values are listed.
- For a judged arm, against each of the two references:
  - **separated above:** every `official_nov` run has a higher S than every run of the control. With three runs a side, chance alone gives this 1 time in 20 if the arms do not differ.
  - **not above:** the mean S of `official_nov` is not higher than the control's mean.
  - **above on average, not separated:** anything else.
- The statement for a judged arm:
  - "reads above" if separated above under both references;
  - "does not read above" if not above under both references;
  - "in between" otherwise, with what each reference gave.
- The slide sentence names only the arms that were judged:
  - reads above every judged arm: "With [random guesses / no guesses / random guesses, or none], the same pipeline reads lower on this home: here the LLM's guesses add to ASP's score."
  - does not read above any judged arm: "With [the same], the same pipeline reads as high: November's lead over frontier is not shown to come from the LLM's guesses."
  - anything else: the slide gives both S tables and the statements as they fall.
  - If no arm was judged, the slide shows the S tables only.
- What this cannot show. Three runs a side in one home. No p-value is reported. "Not shown to come from the guesses" is not "the guesses do nothing": a gain smaller than the spread between runs stays hidden. The controls differ from `official_nov` in more than the guesses: they run two days later, under whatever load other users put on the GPU then (during November's ASP runs another user's jobs held 24.5 to 31.5 GB of its memory); `official_nov` lost 7% to 10% of its members to dropped replies, and the controls lose none; the sleep stands in for the LLM's wait but is a median, not the wait itself. And the placebo's draws differ from the LLM's guesses in more than truth: in October its members agreed with each other far less often (4.4% against 29.4% of guesses).

**A5.7 Not run.** 00871 (its budget is twice as long, and no ASP run of ours reaches half of it). No new ASP run with the LLM. No new frontier run.

**Not changed.** §1 to §5, Amendments 1 to 4 and their Notes. `official_nov` stays as filed.

## Note to Amendment 5 (2026-11-19 13:26 IST, before any score of its runs has been computed)

When this was written both dry runs had passed (below), the queue of six had been running since 12:43:45, and its first run (seed 42, random guesses) had written 8 stage folders. No run of the six had ended. No score of any of them had been computed or seen by anyone: scoring needs the rescore, which has not been run.

**The scoring code.** `paper_compare.py` (sha256 daeab9be…), `equal_path_check.py` (8d9e85a1…) and `host/rescore_paper.py` (e77d3438…), as committed in 55d68bd. An independent review read the code against this amendment before this note and found three faults, all fixed: a run still in progress would have been copied and scored (the runner leaves no marker for a run that makes no LLM call); the reading would have accepted fewer than the three `official_nov` runs; and a missing log was read more gently for the controls than for `official_nov`.

**Cases the amendment left open, settled here.**
1. A control run with no `logs/roslaunch.log` is treated as one that holds a line of A5.3.
2. A run that holds such a line has no value at any time at or past B (1.2 B included) and none at 100 m. Its cells below B (0.8 B included) and at 50, 60 and 80 m stay.
3. Reach has no tolerance: path at least L, or time at least t, at the last complete stage. A value is read only from a complete stage, for `official_nov` and for the controls alike.
4. `official_nov` means the three runs `e8_00853_s42_official_105m`, `e8_00853_s43_official_105m` and `e8_00853_s44_official_105m`. Their S values are fixed by the files of 11-18: 53.55, 52.48 and 61.73 against the scripted reference, and 29.05, 28.47 and 30.40 against the human labels. If any of the three lacks S, or a rescore gives other values, the rescore stops and no arm is judged.
5. A folder with no stage whose launcher started is a run that happened, with no values. Only a run the runner recorded as skipped or as failed to launch may be launched again.
6. The judging condition and the comparison are read under each reference apart, and S is compared at full precision.
7. A run has ended when the queue's log says its runner ended, or when neither a runner nor the queue is alive on the host. The reading of A5.6 is the one the final rescore writes after the queue has ended. A rescore made before that is marked interim and gives no statement.

**The dry runs (A5.4), read by hand before the six were queued.**
- `dryrun_e9_00853_s42_placebo_5m`, 12:01 to 12:17 on 11-19: the runner launched it; 5 stage folders; 4 planning steps, each naming `placebo`; no LLM call logged; waits of 127, 171, 182 and 175 s, as scheduled; 6.15 m; no line of A5.3. Passed.
- `dryrun_e9_00853_s42_observed_only_5m`, 12:22 to 12:43: the runner launched it; 6 stage folders; 5 planning steps, each naming `observed_only`; zero predicted nodes in each of the 40 members logged; no LLM call logged; 7.35 m; no line of A5.3. Passed.
- The no-guess arm moved more slowly: 8.5 s of navigation time per metre against 5.7. Its runs will take longer than the 3 to 4 hours of the others.
