# Notes on the 12 Nov paper-scale scores

**Command.** `paper_compare.py` with the e7 runs as `frontier_end` (853 seeds 42-46, 871 seed 46), the 871 seeds 42-45 as `crashed_frontier_1st` (first attempts) and `crashed_frontier_rerun`, `--apr` set to `apr_00853_a` and `apr_00871_a`, `--budget 00853=632.1750566959381`, and the four GED files in `ged/` and `../results_paper_compare/ged/`. The exact `--add-run` list is in `paper_compare.json` `meta.argv`.

**Budgets (PREREGISTRATION_PAPER.md §4).** 853: 632.1751 s is the median end time of the five finished e7 runs (611.83, 629.18, 632.18, 739.21, 867.58 s); it is passed with `--budget`. 871: only seed 46 finished, so B is the registered fallback, 809.0840 s.

**Checked.** An independent Opus recompute with its own code matched every F1 and GED cell named in the brief (frontier_end, both crashed arms, 853 official and filter_only, all three budget variants), the budgets and C1-C5. It found no mismatch.

**Disclosures.**
1. **Order of the checks.** §3 says C1-C5 are reported before any arm is scored against APR. They were computed in the same session as the first APR scoring (both at about 14:54 IST on 11-12), not reported first.
2. **C2 is not valid.** Both APR-b tours saved the same graph at every stop: Hydra's backend never wrote an update after stop 0. Their summaries still say complete with 100% of waypoints reached, so the 80% use rule passed them. C2 waits for the APR-b reruns.
3. **APR-a final graphs end about 60 s early.** The last graph copy predates the last scan: on 853 the final leg (5.2 m) and waypoint 85's scan are missing; on 871, the scans at waypoints 65-66. 871's archive also lacks graphs at stops 40-60. The reference is the final graph, so only the last stop is affected.
4. **nvblox died partway through three tours** (853 a, 871 a, 871 b) with GPU out of memory. The tours move on navmesh paths, and Hydra kept growing the graph afterwards, so APR-a is used.
5. **End times leave out the final leg.** The explorer's last stage folder holds only `executed_path.json`, so the end time comes from the stage before it. The missing legs are 0-7.4 m on 853 and 14.0 m on 871 seed 46. B uses the same rule for every run.
6. **The 853 100% cell covers 3 of 5 runs.** With B at the median end time, seeds 42 and 46 end before B and have no 100% value.
7. **Stages without a graph.** In a crashed first attempt (`e7_00871_s44_frontier_end_FAILED_ATTEMPT_1358`), the last stage before t at 50% of B has stats but no graph, and the scorer takes the stage before it. Under the strict reading the run has no value there, and that cell becomes 39.4 [34.8-46.7] n=3. It changes no cell compared with the paper.
8. **GPU sharing.** From 11-09 19:46 the queue launched jobs with about 5.3 GB of GPU free, beside another user's vLLM server. Only e7 853 seed 42 ran with the GPU to itself. Speed per metre was the same (about 7.1 s per metre either way), but every 871 crash came from this.
9. **C1 floor area is far off.** The start floor's navmesh covers 77.0 m² on 853 and 59.3 m² on 871, against the paper's 207.63 and 235.03 m². The waypoint grid spans about 191 and 149 m² (waypoints × 2.25 m²). Rooms: 13 and 14, against 6 and 9.
