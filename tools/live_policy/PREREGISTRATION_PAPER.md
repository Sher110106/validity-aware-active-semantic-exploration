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
