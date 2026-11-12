<!-- Written by the Fable planner after an Opus review (/tmp/cvp_final/review_findings.md); adopted by the main session on 2026-10-28 23:48 IST. Where the frozen PREREGISTRATION_E3.md differs, the pre-registration wins: (1) the E3 gate uses permutation p-values only, with gap sizes reported beside them, because drawn and undrawn candidates sit side by side and an absolute gap bar would mislabel a working arm; (2) windows and curtains stay in the oracle set, and a candidate counts as mapped if a same-label structure node lies within 0.5 m; (3) base rates and the P2 replacement result are filled in from measurements. -->

# Final plan v4, 2026-10-29 00:30 IST

## What changed from v3 (review-driven; "CORRECTED FIX" versions)

1. **E3 is an "exact-object control", not a ceiling** (claims B1, M1 design). The planner rewards disagreement between members (`calculate_uncertainty.py:501-522`), so the oracle tests one kind of content: true objects split at random across members at the placebo's count, with the placebo's room process. Every "ceiling", "brackets every guesser", "model quality is moot" sentence is gone.
2. **E3 gate replaced by the drawn-vs-undrawn randomized contrast** (design B2, code B1/M3-M6). Stage alignment fixed from the pinned code: stage-k draws pair with `stages/(k+1)/executed_path.json` and stage k+1's observed graphs. D1, D5 and the routing bound are dropped; D4 is descriptive; frame rests on the scorer match and P1.
3. **P2 recorded as failed as written and replaced** by the distance-profile rule (claims B3, GATE-1); z filter not applied, logged as a declared deviation (M9).
4. **Scope cut now, not at a checkpoint** (OPS-1): observed_only dropped; E1 seed 45 dropped, so the registered 3-seed E1 is untouched (M6); E3 runs seeds 42 and 43 first, seed 44 only if the replay finishes by 10-31 02:00; the two s42 oracle jobs go ahead of the paid jobs.
5. **Scheduler and runner fixes adopted** (OPS-2 to OPS-8, code B3/B4/M6): time-based memory peak, oracle reruns keep the copied schedule, PAUSE/STOP, lost-job and orphan handling, 00871/44 rerun decided now.
6. **Analysis fixes** (A1/B2/B4, ANA-1): rerun names parsed, unparsed runs listed, `--seeds`, exclusions from `EXCLUDED_` markers, one counted run per cell, logged with old and new sha256; 50 m sensitivity (M4); E2 latency rule (M5); null wording and intervals (claims M1).
7. **Premise and wording corrected** (B5, B6, M2, M4, M7, M8, M11): pooled precision with per-scene and per-run ranges, "the placebo's rate" not "chance", the validator removes about a quarter with a mixed precision effect, budget cuts the Gemini live test, routing stated from the pinned code, frontier descriptive under HM3D only, new title.
8. **"Done" is a checklist with pass conditions** (M10).

---

## 1. The question, and why this is the strongest use of the time left

**Central question.** DeepSeek 1017's scene-graph guesses land near a same-label unseen annotation object about four times as often as random hypotheses of the same shape, though about 97% still miss by more than 0.5 m. Do they help a live ASP robot map more per metre of path? If not, is the limit in the guesses or in the rest of the system (planner, detector, 60 m budget)? Nested: does our structural validator, which removes about a quarter of the guessed objects and some guessed rooms, change live map gain?

**Working title (M11):** "Do LLM scene-graph guesses help a live robot map? A placebo-controlled pilot with an exact-object control arm."

**The finished result:** one four-arm live comparison on two human-annotated homes (00853, 00871), 60 m, scored against the human annotation (frontier-made reference secondary for E1/E2, descriptive for E3), everything labelled pilot with its deviation list.

| Arm | What the planner sees | New-object precision at 0.5 / 1 / 2 m, pooled instances (runs are the unit; all finished runs incl. two excluded; counted-only recomputed in O4) | Status 00:30 |
|---|---|---|---|
| placebo | random hypotheses with DeepSeek's measured shape, no scene content | 0.61 / 2.4 / 7.0% (per run 0.43–0.84% at 0.5 m) | 4 of 6 done; 00871/43 rerun queued; 00871/44 running |
| official | DeepSeek 1017, author pipeline unchanged | 2.6 / 9.1 / 21.5% (per run 1.37–4.80%; 00853 1.69%, 00871 3.92%) | 4 of 6 done (00853/43 held at 54.3 m); 00853/44 rerun queued; 00871/44 running (7.5 h limit at about 04:20) |
| filter_only | official completions after the validator | kept 3.8 / 12.3 / 24.5%; removed 2.8 / 7.5 / 18.1% (750 of 2,849 removed: 32% on 00853, 22% on 00871) | 2 of 6 done; 4 queued |
| oracle_visible (E3) | the placebo's room process; each member names 6–16 unmapped annotation objects drawn at random from those within 5 m of a mapped room centre | 100% at 0.5 m by construction (P1) | built, P1 passed, P2 amended; 4 runs (s42, s43), s44 conditional |

Part of the LLM's edge comes from choosing labels in the pipeline vocabulary (61–70% vs 50% for the placebo), which may itself reflect the observed scene. Few guesses were later mapped where they said (one cell, 00871/42: 0.36% official, 0.09% placebo). Counts in every precision table are (stage, member) instances; runs are the independent units.

**Why this and not something else.**
- *Evidence:* E1 and E2 are registered, hashed and about 60% run. E1 so far: official − placebo +0.0014 (p 0.94; floor 0.11). E2 so far: +0.0197 (00853/42), +0.0046 (00871/42). Both open.
- *Inference:* an E1 null has several readings: the LLM's content is not precise or complete enough; the detector does not map what it points at; or this planner does not turn the difference between LLM and random content into map gain at 60 m. E3 tests one of them: exact objects, drawn at random per member, with the placebo's rooms. If E3 does not help, exact object content delivered this way does not help this loop. That does not show no model could help, because the planner rewards disagreement between members, and a better model could disagree, or place rooms, differently.
- *Budget, not evidence, cuts a live test of a better LLM:* Gemini has $0 left. On 8 matched early-stage inputs Gemini placed 7% of new objects within 0.5 m of a same-label unseen object, DeepSeek 2%, the placebo 1.5% (25, 8 and 5 hits; Gemini returned 29 completions to DeepSeek's 40; hits cluster in a few inputs). That hints that models differ but is too small to rank them.
- With observed_only cut, the design cannot tell whether hypotheses of any kind change map gain; it compares content sources only. Say so.

## 2. Arms, runs, queue

### 2.1 Current queue (keep) and decisions logged now
Queue: placebo rerun 00871/43 → official rerun 00853/44 → E2 00853/43, 00871/43, 00853/44, 00871/44 (7.5 h, `pacing: auto` on the placebo rerun, `rerun_of` on both reruns). Two s42 oracle jobs go ahead of the paid jobs (2.4).

DEVIATIONS 20 (one dated entry, before any counted oracle run): (a) 00871/44 official's 7.5 h limit falls at about 04:20 (adopt mode takes t0 from the config mtime, `live_runner.py:295`); an ending below 50 m gets one paid rerun, queued now as `e1_00871_s44_official_60m_rerun1` with `rerun_of`, placed after the 00853/44 rerun so the original has finished (OPS-7); (b) E1 reruns do not run at the same time as their partners, and wave-2 containers were not rotated (m5); (c) E2 latency rule (5.2); (d) 50 m sensitivity (5.2); (e) `e1_analysis.py` change with old and new sha256 (4); (f) P2 amendment and z decision (3.2); (g) scheduler replacement (2.4).

### 2.2 E3 arm `oracle_visible` (spec as coded; the addendum carries it word for word)
- Candidate set: every object node of the primary HM3D reference (annotation labels that map into the pipeline vocabulary), pipeline frame; 180 on 00853, 232 on 00871; `oracle_sets.json` sha256 a7b35313…; labels typed as structure by the pipeline (door by name, `calculate_uncertainty.py:259-260, 365-370`; window, curtain, blind, wall if present) removed per the root's decision 6, count logged. It is the answer key: the oracle names only objects the arms are scored on. No run of any kind chooses it.
- Per stage, per track, per member: rooms from the placebo's process with the same seed key (`placebo_graph` with the object count forced to zero on the same RNG stream; rooms match the placebo partner's only while the observed graphs match, in practice near stage 0, and not at all for the salted 00871/43 rerun partner); then an object count drawn from the placebo's distribution (Poisson(10) clipped 6–16; a second draw, not the placebo member's own) taken without replacement from reference objects more than 0.5 m (xy) from every mapped object and within 5.0 m (xy) of a mapped room centre (any mapped node if no room); exact label, position, dimension; `is_predicted: true`; linked to the nearest room, observed or hypothesised, so the room-IG term carries placebo room names; fallback to the placebo's objects if none eligible, flagged (a fallback member's rooms differ from the placebo's). Eight members together name about 60 distinct objects per stage, about 30% of the unmapped pool; the reach covers a median 60% of unmapped objects; over a run the draws cover most of the in-reach pool. Because the detector matches few annotation objects, much of this pool may lie in space the robot has already viewed (measured, not assumed: 3.4).
- Pacing: the exact `no_llm_delay_schedule` string of the cell's placebo run, read from its `run_manifest.txt`; an oracle rerun (`<run>_rerun1`) keeps that string and draws a salted stream. Pacing matches per decision, not per metre; stages per run and sleep seconds per metre are E3 covariates (OPS-9).
- `max_hours` 7.5, `max_cost_usd` 0. Seed key as the placebo's.

**Routing, from the pinned code.** `exploration_pipeline.py:859-860` passes completion 0 to `global_planner.plan`; `graph_planning.py:146-160` runs A* over completion 0's rooms and returns `[start, room centres…, target]`; but `MidPlanner.plan_path` reads only `high_level_path[-1]` (`mid_planning.py:120-122`) and `find_mid_planner_target` (`mid_planning.py:408`) has no caller in any pinned script. The room path never steers the robot. Hypothesised rooms reach behaviour three ways: the room term of information gain through the parent-room names of visible objects (`calculate_uncertainty.py:480-488, 536-541`, weight `UNCERTAINTY_ROOM_WEIGHT`); the sampling box (`:315-333`); and `nearest_room_node` raising on an empty room list (`graph_planning.py:93-99`), which sends the pipeline to its retry path (`exploration_pipeline.py:873-875`). Oracle and placebo draw rooms with the same code and seed key, so their rooms follow the same distribution; the contrast is object content, including which room each object links to. Measured on three 00871/42 runs: the selected viewpoint was never nearer a hypothesised room than an observed one (0 of 38 stages); whether A* routed through one was not measured and does not matter for motion. `oracle_rooms` is not a next step that would "pull the route"; it would change room names in the room-IG term and the box.

**What the planner does with hypotheses.** Candidate poses must lie within max_range + 0.5 = 3.5 m (3D) of a completion-0 object, observed or predicted (`calculate_uncertainty.py:430, 451`); object IG is H(Y) minus the mean within-member entropy (`:501-522`) and perturbations use the same seeds for every member (`:311`), so positive IG needs some member's predicted objects in the 3 m, 90-degree frustum; the target is drawn at random among the top ties (`exploration_pipeline.py:833`); the only anti-revisit rule is `MINIMUM_DISTANCE_DIFFERENCE` from past scan positions (`calculate_uncertainty.py:136-142`); there is no explored-space term.

### 2.3 Cuts made now (OPS-1)
observed_only: dropped. E1 seed 45: dropped; the registered 3-seed E1 stays primary in all cases. E3: seeds 42 and 43 on both scenes (4 runs); seed 44 (2 runs) only if the replay, run after the scheduler rewrite with measured memory figures, finishes the whole queue by 10-31 02:00.

### 2.4 Scheduler (root is rewriting; the plan fixes what it must do)
- Time-based memory peak: for t from now to the end of the last active run, sum each active run's current memory + measured rate × min(t, remaining) plus the new run's measured base + rate × t; launch only if the lowest projected free memory stays at or above `RESERVE_GB`. Paid runs expected 6.5 h, $0 runs 4 h; `hydra_gb` reuses the last good reading on failure (OPS-3).
- Eligibility: the first paid and the first $0 job in list order; a waiting `pacing_from` job falls through to the next $0 job; refuse and log if `schedule_of` returns None (OPS-6).
- Reruns: `rerun_job` keeps `no_llm_delay_schedule` for `oracle_visible` and sets `pacing: auto` only for placebo (OPS-2, B4); paid reruns only while metered spend is under $25 (OPS-8).
- Global PAUSE/STOP treated like SCHED_PAUSE; a launched job with no record, or an outcome without `finished`, after 10 minutes is requeued once (host-memory, launch or adopt failures) or flagged (skipped_exists, campaign cap); the below-50 m rerun rule applies only to monitored outcomes; `docker inspect` before counting a container idle (OPS-4).
- Orphans: runner dead and pipeline alive on two polls → start an adopting runner; a run that must be stopped without a runner gets the full stop sequence (Escape, TERM/KILL, `pkill -9 -f multiprocessing.spawn`, `clean_container.sh`) and is recorded in `sched_state` (OPS-5). Watchdog waits if the older run ends within about 20 minutes and free memory stays above 6 GB plus a margin.
- A scheduled `touch SCHED_PAUSE` at 10-31 02:00 (OPS-8).
- Deploy the repo copy to the host, check its sha256, restart during a quiet poll; after the first oracle launch, check the manifest's schedule equals its placebo partner's and that the "pacing copied from" line is in DEVIATIONS (B3 code).

Queue order after the rewrite:
```
e3_00871_s42_oracle_visible_60m     pacing_from e1_00871_s42_placebo_60m
e3_00853_s42_oracle_visible_60m     pacing_from e1_00853_s42_placebo_60m
e1_00871_s43_placebo_60m_rerun1     (queued; pacing auto)
e1_00853_s44_official_60m_rerun1    (queued)
e1_00871_s44_official_60m_rerun1    rerun_of e1_00871_s44_official_60m  (skips itself if ≥ 50 m)
e2_00853_s43 / e2_00871_s43 / e2_00853_s44 / e2_00871_s44 filter_only
e3_00871_s43_oracle_visible_60m     pacing_from the 00871/43 placebo rerun
e3_00853_s43_oracle_visible_60m     pacing_from e1_00853_s43_placebo_60m
[e3_00871_s44, e3_00853_s44 only if the replay passes]
```

### 2.5 Timeline (replay decides; these are my estimates)
Paid pole: 00871/44 ends by about 04:20; then 5 paid runs at 6–7 h → 10-30 10:00–15:00, plus 6.5 h if 00871/44 needs its rerun. $0 pole, now allowed beside paid runs by the peak projection: s42 oracles from about 04:30 (two $0 runs may overlap), placebo rerun, s43 oracles → about 10-30 02:00–06:00 with one incident rerun. "Host behind" = replay finish later than 10-31 02:00; the replay is rerun at 10-29 18:00 and 10-30 06:00. Analysis runs from 10-30 afternoon on finished cells and closes 10-31 by 20:00.

### 2.6 Cost
Paid queue with two reserve reruns about $7–11; E3 $0; offline $0; Gemini $0. End state about $18–22 metered of $40; runner cap 30, key limit 40 unchanged.

## 3. Code and gates before any counted oracle run

### 3.1 Done
`live_policy.py` (oracle policy; md5 be28db61… before the structure-label change), `live_runner.py`, `build_oracle_sets.py`, `stage_precision.py`, `stage_diagnostics.py` (to be realigned), `oracle_positive_control.py`, 25 tests. Pending from the root: structure-label exclusion with its count, docstring and spec wording on the count and the room linking.

### 3.2 Gates
- **P1 (passed, code check):** 39 saved observed graphs, 8 members each: new precision 1.0 at 0.5 m (3,297 of 3,297), no relabels, no fallback, median 116 in reach. Rerun after the structure-label change. The `llm` column of `oracle_positive_control.py` is wrong (both tracks score all files; 8 members at a fixed seed) and is not quoted (m3 code).
- **P2 (dry run, 00871/42, 10 m):** box clause failed as written: y edges 2.20 and 2.45 m off; widths 10.33 × 10.55 vs 10.76 × 10.80 m; the shifts point opposite ways. By construction both arms place objects at most 5 m from a mapped room centre, so the box test could not detect a longer reach. Logged in DEVIATIONS, dated, not recorded as passed. Replacement rule fixed now: the distribution (median, 90th percentile) of xy distance from each hypothesis to the nearest mapped room centre, oracle vs placebo, on the 39 P1 graphs and the dry run; pass if the oracle's 90th percentile is within 1 m of the placebo's; else 3.5 m reach and rerun P1 and P2. The root is computing it; the result goes into the addendum before hashing. Also report each arm's largest hypothesis distance from the nearest mapped node and the offset split into observed nodes vs hypotheses.
- **z:** 00853 spans 0.00–2.52 m, 00871 −0.02–3.02 m, above v3's 3 m trigger on 00871. One floor each; applying |z − floor| < 2 m would remove same-floor objects the arms are scored on. Not applied; declared deviation from the trigger; the gap and the labels of objects above 2 m go in the addendum.
- **Frame:** established by the scorer matching (observed graphs score 0.11–0.17 AUC against the same reference the oracle copies positions from; wrong transforms score 0.00–0.03) and P1. No in-run test claims to catch a frame error.

### 3.3 Base-rate step (before hashing; $0; finished official and placebo runs)
Stage alignment from the pinned code: `WORKING_DIRECTORY = BASE/k` (`exploration_pipeline.py:654`); the walk driven after stage k's plan is written to `BASE/(k+1)/executed_path.json` (`:881-889`) before `stage += 1` (`:913`); stage 0 has none. For stage-k hypotheses: reached viewpoint = last point of `stages/(k+1)/executed_path.json` (`world_frame_path`); map = stage k+1's observed graphs (k+2 as lag check); drop the last stage. Measure the base mapping rate: among unmapped reference objects within 3.5 m (xy) of the reached viewpoint at stage k, the share matched (same label, < 0.5 m, either track) at stage k+1, per run and per scene, on the counted official and placebo runs. Thresholds in 3.4 are set from it; the addendum states "thresholds were set from non-oracle runs before any counted oracle run".

### 3.4 E3 gate: drawn-vs-undrawn randomized contrast
At each stage and track, the eligible set is known from the policy's own rule, and the union of member draws is a random subset of it (about half). Compare drawn with undrawn eligible candidates on:
- (i) **approach:** within 3.5 m (xy) of the reached viewpoint (last point of `stages/(k+1)/executed_path.json`);
- (ii) **mapping:** same label < 0.5 m in stage k+1's observed graphs (k+2 as lag check; final map descriptive).
Statistic: pooled difference in rates (drawn − undrawn) over all stages of a run; p from a within-run, within-stage, within-track permutation of the drawn labels (2,000 permutations; one-sided, drawn > undrawn, because the direction is fixed in advance; this is a gate, not a claim). Pre-registered split: candidates ever within 3 m of an earlier executed-path point vs not (aligned as above), and the share of draws in scanned space per stage for oracle and placebo (M3). Verdict per scene from the first finished oracle run on that scene; later runs reported:
- **broken** (the loop is not steering toward drawn objects): no approach gap (p ≥ 0.05 or gap < 0.10). Archive oracle runs as `FAILED_ATTEMPT`, fix once, rerun inside the cut ladder; a second broken verdict ends E3 and the gate results are reported.
- **detector-limited:** approach gap, no mapping gap (p ≥ 0.05 or gap < 0.5 × the scene's base rate from 3.3).
- **working:** both gaps.
D4 (mean displacement vector, with median |d| and the 2 m vs 0.5 m hit ratio) is descriptive. D3 "later found" is reported per arm with one unit: reference id for the oracle, label plus 0.5 m cluster for the others, last stage left out (m7).

## 4. Offline work ($0)

| # | Task |
|---|---|
| O1 | `live_score.py` on every finished counted run, both references, no `*_FAILED_ATTEMPT*` dirs → `all_scores.json` |
| O2 | `e1_analysis.py` after the fix: regex accepts `(?:_rerun(?P<rerun>\d+))?$`; unparsed names go to `dropped`; `--seeds 42,43,44`; `--exclude exclusions.json` built from `EXCLUDED_*.json`; exit non-zero if two counted runs share a cell; test with real rerun names asserting 400 relabelings; DEVIATIONS entry with old and new sha256 saying only name parsing changed. Run E1, E2 (Holm), E3 at 60 m and the 50 m sensitivity, both references |
| O3 | Covariates: per-run dropped-member rate, mean `llm_wait_s`, mean stage duration; pacing flag per E1 pair; stages and sleep seconds per metre per $0 run |
| O4 | `stage_precision.py` restricted to counted runs (excluded runs listed separately; stale member files skipped; `isdigit` stage filter), per run and per scene with instance counts and in-vocabulary shares; `stage_diagnostics.py` realigned (3.3) with the gate (3.4), D3, D4 and the scanned-space split for every arm; the base rate |
| O5 | Static three-way table at 60 m under HM3D on the counted official and filter_only runs |
| O6 | Gemini 8-input re-report, duplicate row removed, three radii, labelled "compare only within the same 8 inputs"; kept out of the live precision table |
| O7 | Copy the host DEVIATIONS into `tools/live_policy/`; resolve 19 of 8,842 vs 8,943 |
| O8 | One team member reads the ablation sections of LFG, SEEK, LGR, EPoG |
| O9 | `numbers.csv`: every number in the write-up with its file:key |

## 5. Analysis and decision rules

### 5.1 Registered tests, unchanged
E1: official − placebo, author-faithful object F1 AUC to 60 m, HM3D primary, frontier-made secondary, same sign under both for a claim; scene-blocked exact permutation (400 relabelings), two-sided, alpha 0.05; sign-flip secondary; CI; MDE; 50 m exclusion with one rerun. E2: official − filter_only, Holm over E1 and E2. E3 (addendum): oracle − placebo, same test; E3 rests on HM3D, frontier reference descriptive, because the oracle holds the HM3D answer key (m4). E1 and E3 share placebo runs, so their errors are correlated; E3 was registered after 4 of its 6 placebo comparator AUCs were known (m2 claims). Holm over all three reported as a sensitivity line.

### 5.2 Rules fixed now
- **Intervals and nulls (M1):** beside the bootstrap CI (which shrinks at n = 3), a permutation-inverted CI or a t-interval on the scene-blocked difference; "effects up to b are not ruled out" uses the wider. Null form for every contrast: "No detectable difference: d = … (95% CI a to b). The design had 80% power only for differences of about x (about y% of the arms' AUC; normal approximation, understated by about 14% at 8 degrees of freedom). Effects up to b are not ruled out."
- **50 m sensitivity (M4):** the same test on `hm3d_auc_af_f1_to_50m` (and the frontier version) for E1 and E2; claim an effect only if 60 m and 50 m agree in sign; report both.
- **E2 latency (M5):** per run, mean `llm_wait_s`, mean stage duration and dropped-member rate beside E2; if a cell's mean `llm_wait_s` differs between arms by more than 20%, report E2 with and without that cell, and call a filter advantage "confounded by latency" unless it survives without it. Only the seed-43 officials ran at the earlier latency.
- **E1 positive:** "the official arm's F1 AUC exceeded the placebo's by d (95% CI a to b)". E1 null: "The LLM's guesses landed within 0.5 m of a same-label unseen object about 4 times as often as the placebo's (2.6% vs 0.6% pooled; 2.7× on 00853, 6.9× on 00871). The official arm's F1 AUC differed from the placebo's by d (95% CI a to b)" + the null form.
- **E2 positive:** "filter_only's F1 AUC exceeded official's by d [CI]. The validator removed about a quarter of new objects (32% on 00853, 22% on 00871) and some rooms. The kept-vs-removed precision split is small and mixed across scenes (21 removed hits pooled; precision at 0.5 m rose on 00871, 4.35 to 4.93%, and fell on 00853, 2.56 to 2.27%), so the design cannot name precision as the cause; the validator also removes rooms." E2 null: the null form plus "the validator removed 750 of 2,849 new objects and moved pooled 0.5 m precision from 3.6% to 3.8%: up on 00871, down on 00853."
- **E3**, read only after the gate verdict (3.4): working and p < 0.05 → "exact objects drawn at random per member raised F1 AUC over the placebo by d [CI]"; working and null → the null form; detector-limited → report the AUC with the gate table and claim only "exact objects delivered this way did not raise map gain through this detector"; oracle behind placebo at p < 0.05 → report with the scanned-space split before any sentence.

Matrix (E1 × E3), each cell with its CI:

| | E3 positive | E3 null (working) |
|---|---|---|
| E1 null | "Exact object hypotheses help and the LLM's do not. The design cannot say which difference matters: precision, coverage per stage, labels, sizes, room linking, or how members disagree. Oracle − official = d [CI]." Any "converts exact but not LLM hypotheses" sentence needs oracle − official at p < 0.05 (M2). | "Neither the LLM's content nor exact objects drawn at random per member raised map gain detectably at 60 m on these two homes with this planner and detector (CI a to b)." Inference, scoped: object guesses delivered as independent random subsets per member are unlikely to help this loop at this budget; better rooms and better-placed disagreement were not tested. Applies only once the gate passes and the scanned-space split is reported. |
| E1 positive | "Both beat the placebo. The official-to-oracle gap is what exact random-subset objects add over the LLM's; it is not an upper bound for better models." | Odd; report the gate table before any sentence. |

- **Frontier (M8):** HM3D reference only; caption "Frontier explorer: one deterministic run per scene, inside the spread of the live arms on both scenes (0.1716 equals the top live run on 00853); no comparison tested." Inflation text: "The frontier-made reference is the frontier run's own final map. It raises that run's AUC 2.9× (00853) and 4.5× (00871), and the live runs' 1.9–3.8×." No ASP-vs-frontier sentence in the results.

## 6. Stop and cut rules
- Host behind (replay finish after 10-31 02:00): cut E3 seed 44 (already conditional); then cut E3 00853/43 (E3 becomes 2 v 3 on 00871 and 1 v 3 on 00853, descriptive); never cut the E1 reruns or the four E2 runs; a paid rerun that fails twice is a missing cell.
- Gate broken → fix once, rerun inside the ladder; second broken verdict ends E3.
- Spend: metered $25 → no paid rerun without a decision; $30 → no more paid launches. Another OOM or tenant complaint → SCHED_PAUSE, one run at a time. SCHED_PAUSE at 10-31 02:00 by schedule; nothing after 08:00.
- Analysis behind (10-31 12:00): drop O5, then O8; never O1–O4.

## 7. "Done" (M10): by 10-31 20:00 IST, all of
1. Every planned cell (E1 6+6, E2 6, E3 4 or 6) listed as counted, excluded (reason) or missing (reason); the dropped list names every run in `all_scores.json` the analysis did not use.
2. Raw run directories copied off the host to a stated path with a sha256 manifest.
3. `reproduce.sh` regenerates `all_scores.json` and the E1/E2/E3 analysis JSONs from that copy; diff against the committed files empty (bootstrap seed 0).
4. Every number in the write-up and figures traces to a file:key in `numbers.csv`.
5. sha256 files for the three pre-registrations and `oracle_sets.json` verify.
6. The write-up has the evidence and inference lists, each inference citing its evidence items; limits include instance-level counting, the MDE approximation, random member disagreement, frontier self-reference, two scenes, one mapper, wall-clock censoring, the 8-input static test, E2 and E3 arms not concurrent, and that the design cannot tell whether hypotheses of any kind change map gain.
Stretch: a second team member re-runs `reproduce.sh` and checks each decision rule was applied as written.

Package: run table; analysis outputs; mechanism tables (precision by arm with per-run ranges and instance counts, kept vs removed by scene with hit counts, gate table and D3/D4 by arm, static three-way table); figures (F1 vs path per scene, AUC per cell by arm with the frontier line under HM3D, precision bars, gate dot plot); write-up with errata (the "at chance at 0.5 m" sentence corrected; calibration and the risk term retired in one line: offline Brier equal to the base rate, beta ≤ 1 moved 2/0/3 stages; the agreement vote named apart from the validator); provenance.
