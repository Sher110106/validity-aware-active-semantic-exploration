# Rebuild of the offline bench (2026-11-13)

## Result

The bench runs again on this laptop and gives the registered output.

- 9,600 of 9,600 picks are identical (384 stages × 5 guess sets × rules R1–R5).
- The 19,200 R6 draws, `Uwall`, `Ucone`, `regret`, `n_cand` and `top10_match` are equal on all 384 stages. No row has an error or a drop.
- Decision numbers match: oracle/placebo-A regret ratios R1 0.9328, R2 0.9035, R3 0.8527, R4 0.8496 (bar 0.70), and `go_live = false`. See `results_2026-10-31/DEVIATIONS.md` item 37(a).
- `summary.json` is equal to the registered one except `descriptors.cpu_seconds_stage_sum` (a timing value: 19,793 s now, 10,927 s then).
- Time: 3,333 s for the bench on 6 cores (the October run took 26 min on 7 cores; this laptop is slower or busier). The whole script, with `summarize.py`, took 56 min.
- Disk: the copy and its outputs use 4.4 MB. The scratch YAMLs in `/tmp/cvp_review/work_A/tmp` stay empty.

The check ran `summarize.py` from the copy and compared its output with the registered `summary.json`. The comparison is in `rebuild_bench.sh`.

## Rebuild

    bash tools/live_policy/m2/rebuild_bench.sh            # farm, copy, run, compare (about 56 min)
    bash tools/live_policy/m2/rebuild_bench.sh --no-run   # farm and copy only (seconds)

The script wipes and recreates `/tmp/cvp_review` and `/tmp/cvp_bench`, and the copy in `/Users/sher/project/cvp/scratch_m2/bench_copy`. It uses 6 workers (`NPROC`). It writes nothing under `review_2026-10-29/` or `results_2026-10-31/`. It sets `PYTHONDONTWRITEBYTECODE=1`.

## What the farm holds

| Path the code reads | Points to |
|---|---|
| `/tmp/cvp_review/runs` | `/Users/sher/cvp_live_campaign_copy/runs/live_campaign` |
| `/tmp/cvp_review/work_A/*` | one link per file in `review_2026-10-29/A/`, plus a real `work_A/tmp` |
| `/tmp/cvp_review/audit/audit/*` | one link per file in `review_2026-10-29/audit/audit/` |
| `/tmp/cvp_review/refs/oracle_sets.json` | `results_2026-10-31/oracle_sets.json` |
| `/tmp/cvp_review/analysis_pre/runs.txt` | a file: first 24 lines of `results_2026-10-31/analysis/runs.txt` |
| `/tmp/cvp_review/pipeline_pinned_copy/scripts/calculate_uncertainty.py` | `tools/decision_replay_reference/calculate_uncertainty.py` |
| `/tmp/cvp_bench/refs/{00853,00871}_walls.npz` | `review_2026-10-29/bench/walls/` |

Two points differ from the plan's recipe:

- `work_A` is a real folder of links, not one folder link. The scorer writes scratch files to `work_A/tmp`, and a folder link would send them into the repo.
- The walls path is `/tmp/cvp_bench/refs`, not under `/tmp/cvp_review`. `bench.py:59` reads it.

`runs.txt` has 25 lines. Line 25 (`e3_00871_s44_oracle_visible_60m`) is not in the bench, so the script keeps 24. `run_idx` in the output is the 0-based line number.

`replay.py:43` also loads `/Users/sher/project/cvp/project/tools/live_policy/live_policy.py` by absolute path. It needs `placebo_calibration.json` beside it. The bench result depends on both files, so a change to either would show up in the picks.

Missing from the laptop: nothing.

## Map of the code

Line numbers are for the registered files, `bench/build/bench.py` (B), `A/fastig.py` (F), `A/replay2.py` (R2), `audit/audit/audit.py` (AU) and `tools/live_policy/live_policy.py` (LP).

**Where a stage's member completions enter**
- Member ids for a stage: `rp2.gids_for`, R2:30. Called at B:218. Stages hold 2 to 8 members; member `g` belongs to track `g // 4`, so a full stage is two tracks of 4. The plan's "sets of 4" is one track.
- Each member's completion is a file, `stages/<k>/habitat_scene_graph_new_graph_<g>.yaml` (B:221). These are the `actual` set.
- Each track's observed graph is `habitat_scene_graph_original_graph<t>.yaml` (B:262–264). Every other set is built from it.
- The other sets are built in a loop over `gids` at B:272–284. Each member gets `rng = default_rng([BENCH_SEED, run_idx, k, g, SALT])` (B:277), then `lp.oracle_graph` (LP:315) or `lp.placebo_graph` (LP:203), and `write_yaml` (B:146) writes it to `tmp/`.
- A new arm builds one graph per member in the same `gids` order, writes the files, and adds its name to `SETS` (B:41) and `SALT` (B:40).

**How the 300 candidates are scored**
- Candidates are drawn once per stage from the stage's `actual` files: `fastig.Scorer(act_files, seed)` then `first_stage(seed, nprior, cur)` (B:222–223; F:126 and F:203). They do not depend on the set being scored. The log's top 10 is re-checked at B:224–228.
- Any other set: `fastig.Scorer(files[s], seed).score(kept, cam1)` (B:294; F:195). It returns an (N, 2) array of object and room information gain, summed at B:295.
- Each member file is expanded to a group of 4 (original plus 3 perturbations) inside the pinned scorer (`_build_scene_graph_groups`, `calculate_uncertainty.py:325`). Entropy is computed in `Scorer._ig`, F:179.
- The author's R1 pick score is `ig − LAMBDA·d` (B:311, `LAMBDA = 0.2` at B:38), where `d` is the distance from the current pose (B:255). The pick is `argmax` (B:319).

**Outcomes**
- U_wall per candidate: `wall_visible` (B:66) gives the wall-aware mask, `Uw_set = wv & un` (B:239), `Uw` (B:241). `un` is the "not yet mapped" mask from `au.mapped_masks` (AU:74).
- `Ucone` in the bench is U_wall restricted to the camera cone (B:124 `cone_mask`, B:240–242). That is U_wall_cone. The audit's U_cone has no wall test. It is `(vis(geom, kept, cam1) & un).sum(1)` with `geom` from `au.ref_geom` (AU:92, 113, 171–173). Use the same one the pre-registration names.
- R1 regret: `mx − U[pick]` for U_wall and `Ucone` (B:320–324). Stored at `row["regret"][name][set][rule]`.
- True unseen objects at the top pick: `U[picks[s]["R1"]]`, with `U = Uw` or `Uc`. The bench stores the arrays (`row["Uwall"]`, `row["Ucone"]`) and the picks, not this number.
- Spearman rho: `au.rho(a, b)`, AU:129. The bench calls it only for `Uwall` vs `U360` and `total` vs `Uwall` (B:260). It does not compute rho with U_cone. The audit does: `rho(total, Uc)` at AU:181 and `rho(ig, Uc)` at AU:182. A new arm calls `au.rho(ig − LAMBDA·d, Uc)`, using the audit's `Uc` (see above).

**Functions a new arm must call**
`rp.lp.load_calibration` (B:37), `rp.load` (graph in), `write_yaml` (B:146), `fastig.Scorer(...).score(kept, fastig.cu.CameraConfig())`, `au.rho`, and `wall_visible` and `cone_mask` for the yardsticks. Reuse `kept`, `Uw`, `Uc`, `d` and `un` from `stage()` rather than recomputing them. `stage()` is B:213–354; `main()` is B:365.

## Notes for the next worker

- The Python is 3.14 with NumPy 2.5.3. The host ran NumPy 1.x. `pinned_harness.py` sets `np.set_printoptions(legacy="1.25")` for this, and the result still matches.
- `bench.py` writes `stages.jsonl` beside itself, so run it from a copy. A one-stage test (`bench.py <run>:<stage>`) writes `stages_test.jsonl` and takes about 6 s.
- `oracle_sets.json` in `results_2026-10-31/` has a 11-12 modification date, after the October run. It is byte-identical to `tools/live_policy/oracle_sets.json`, and the picks still match.
