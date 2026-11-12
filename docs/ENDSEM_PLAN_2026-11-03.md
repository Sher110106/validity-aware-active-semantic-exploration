# End-sem plan: "Right in meaning, wrong in place?" (2026-11-03)

How this plan was made:
- Three independent planners each took one angle: test the author's claim, build a fix, or secure the deliverable.
- Two judges scored the plans. Both picked "test the claim", which scored 60 against 57.5 and 43.
- A synthesizer merged the winner with useful pieces from the other two.
- A red team then checked the merged plan against the repo. It found 1 fatal problem, 16 major ones and 8 minor ones.

Section A below lists the red-team changes. Section B adds the student's second request: scores on the paper's scale, and the validity layer in the same pass. Both sections override anything below them that conflicts. The merged plan follows as written, and Appendix R gives the red team's findings in full. Nothing here has run yet, and no money has been spent.

## A. Changes after the red team (these override the sections below)

1. **Fatal: the Claude conversation store.**
   - The problem: a key of (pid, sha256 of the first user message) collides in the threaded static harness. All 4 members of a stage share the process and the first message, so they would read and overwrite each other's histories.
   - The fix: attach the raw Claude content blocks to the `_FakeContent` object the shim returns. genai keeps that object in its history and passes it back on the next call.
   - The test: a fake-client case with 4 threads sending the same first message at once.
2. **A fourth outcome, "Inconclusive".**
   - Under a true null, the current rules fall into "Mixed", which makes a positive claim. Pre-write an "Inconclusive" one-liner.
   - "Mixed" then requires Supported at L1 or L2 (and beating B4) while not Supported at L3.
   - Name the rejection comparator in advance.
3. **The prompt plants room types.**
   - The author's `pipeline_config.yaml:101` says "Scene may contain more than one bedroom and more than one bathroom".
   - In the October official runs, 69% of the new rooms the LLM guessed were bedrooms and 21% bathrooms (checked 11-03, 724 rooms).
   - Put this on the base-rate slide. Read L1 room claims as an echo of the prompt unless they beat B3 given the same hint.
   - Add an exploratory Haiku replay (about $5) with that sentence removed.
4. **L3 must score unobserved regions only.**
   - Pre-register a stratum of regions with no mapped vocabulary object and no observed room node within 0.5 m at stage k. Gate L3 on that stratum.
   - Report the partly seen stratum apart, so that completing a half-seen room does not count as "predicting the unexplored part".
5. **One frozen label normaliser for every model.**
   - The rule: lower case, `_` to space, strip plurals, take the head noun, then apply an explicit synonym table.
   - Report each model's unmapped share.
   - Score L2 and L3 two ways: over the detector vocabulary (primary for any link to ASP's map) and over all classes (for "semantics"). 29.5% of DeepSeek's labels, such as bed, plant and bookshelf, lie outside the 52-word detector vocabulary.
6. **Oracle factorial anchor F0.**
   - In F0 every member holds the full truth. ASP's score then gives the unexplored space zero (`live_policy.py:20-22`), so the pick falls to the nearest candidate.
   - This is the clearest mechanism slide: "semantics that are right and agreed are invisible to ASP's score."
   - Repeat F1-F3 at 25%, 50% and 100% subset sizes.
7. **Revive the bench first.**
   - Build the `/tmp/cvp_*` symlink farm from a grep of every hard-coded path in `review_2026-10-29/{A,audit,bench}`.
   - Write `analysis_pre/runs.txt` from the first 24 lines, and point the walls path at `bench/walls/*.npz`.
   - Reproduce 9,600 of 9,600 picks before writing any new code. Budget a day.
8. **Move the rendered yardstick to week 2,** with a memory floor of about 20 GB, so the gate uses it.
   - Weight each class by its detection yield in the October runs.
   - It fixes occlusion but not circularity; keep the registered bias statement.
9. **Replace gate G-sci (b).** In practice it asks Claude to match the oracle.
   - Use the prediction from the M2 error curve instead.
   - In H5, compare against Claude's own content shuffled across positions (B5 or D), so member diversity stays fixed.
   - Treat E6 as rule-out mode by default.
10. **Placebo v3 must match Claude's members, not only their shape.**
    - Fit it to Claude's measured within-stage agreement rate and drop rate, and pre-register both as balance checks.
    - ASP's score is driven by disagreement: in October, LLM members agreed within 1 m 29.4% of the time against 4.4% for placebo.
11. **Yoked pacing.** Placebo stage k sleeps its partner's measured stage-k wait. Record the pacing flag as a covariate. The October rule flagged all five pairs.
12. **A time-and-memory feasibility check (G-feas item 5).**
    - Simulate the live wait as the slowest of 8 members per stage, from M4.
    - Require the p90 projection to finish before the freeze. Two runs fit only while T ≤ 5.6 h at 7 GB per hour.
    - Patch the scheduler's `NEW_HOURS` and `NEW_RATE` from measured values, and give each container a docker memory limit.
13. **Call cap and output length.**
    - Set `MAX_CALLS` from the M4 p99 calls per member × 150 × 1.2. If Claude loops like Gemini, about 26 calls per member, the current 3,000 cap ends runs near stage 14.
    - Make a cap stop end the run cleanly.
    - Use streaming (`messages.stream(...).get_final_message()`) with `max_tokens` 64,000, log `stop_reason`, and pre-register a drop-balance check.
14. **Account checks before M3.**
    - Read the Console: usage tier, RPM/ITPM/OTPM per model, spend limits and the account's creation date.
    - Send the thinking block-binding control set to "error", so the preserved-thinking check means the same on any account.
15. **Transport details.**
    - Timeout about 300 s, `max_retries` 3, and IPv4 forced through the httpx transport.
    - Store the raw response JSON and resend it.
    - Pre-warm the cache with one `max_tokens` 0 call per graph.
    - Clear the ROS logs and size the image before `docker commit`.
16. **Smoke test on non-frame inputs.**
    - Run the smoke on the 00069 dry-run stages and score no semantics in it.
    - Gate relevance on the L3 lift over each model's own derangement (D), not on the raw L3 rate.
17. **Statistics.**
    - The confirmatory family is 3 Claude models × 3 levels on a common input set. DeepSeek and Gemini are descriptive.
    - Get CIs by inverting the sign-flip test.
    - State that inference holds only for these two houses.
18. **Region footprints.** Rasterise floor triangles from the semantic mesh instead of using AABBs, which overlap on 15-26% of the area. Report the chance rate for each type.
19. **Drift canaries.** Flag drift only beyond 2.5 October SDs, and never pool October and November arms.
20. **An outside timestamp for each pre-registration hash.** With the student's OK, commit and push it, or email the sha256 to the course staff before any number exists.
21. **The paper's room test with 4 members.** Report it as 1-of-4 and 2-of-4 with a chance rate, not against the paper's 9 of 28 with 8 members.

## B. Second request (11-03): scores on the paper's scale, and the validity layer in the same pass

The student asked for two things: scene graphs and scores that line up with the author's published numbers, even though the author has not sent his reference graphs; and the validity layer run inside the semantic test, so one pass gives both results. Both are possible. Section B adds $0 of API spend and about 10-17 host hours, plus 10-15 more if the optional scenes run. Where it conflicts with §3-§11, Section B wins.

### B1. What the paper did, and where we differ

Source: arXiv 2510.05430v2 §IV-A and Fig. 4, read on 11-03 from `.firecrawl/arxiv-2510.05430-html.md`.

| Item | Paper | Ours now | Gap |
|---|---|---|---|
| Scenes | 853, 69, 871, 573 | 853 and 871 live; all four have September runs and frontier references on the host (`phase13_diagnostics.py:36-79`) | 69 and 573 have no human labels |
| Reference | "we manually navigate the camera viewpoint through each environment, ensuring that all accessible regions are visited and all objects are detected", with the same pipeline; never released | the frontier-made reference (one frontier run's final map) and the HM3D human labels | nothing built the paper's way |
| F1 | 61 categories; same category and centroids within 0.5 m; objects only | `tools/evaluator`, `af_f1`, the same rule | none for 853 and 871 (checked 11-06): the author's `task_def/` has a 52-label file, loaded by default, and a 61-label file for 573 only (the 52 plus 9). The paper's "61" is the union. |
| F1 plot | the plotted curve keeps the running maximum over stages (`f1_score_plot.py`) | the stage value | report both (checked 11-06) |
| GED | unit insert and delete costs; rooms substitute if same name within 4.0 m, objects if same name and parent within 0.5 m | since 11-06, the author's own `ged_score_plot.py` code (gmatch4py `GraphEditDistance(1, 1, 1, 1)`) run on the host from a scratch install; `tools/evaluator/ged.py` (NetworkX, 60 s timeout) is a different method and is not used for paper-scale numbers | none |
| Budget | F1 and GED at 10%, 50% and 100% of a fixed navigation-time budget whose value is not given | a 60 m path budget; every stage also logs `total_navigation_time_seconds` | see B2 |
| Room test | at least 2 of 8 samples within 2.5 m before the room is found; 9 of 28 rooms; Fig. 4 (right) gives time and distance to predict and to find five target rooms | not yet run under the paper's rule | |
| LLM | Gemini 2.5 Pro | DeepSeek; Claude planned | |
| Runs per scene | one, on the reviewers' reading | 3 seeds in October, 5 planned for E6 | |

### B2. A finding from this check: the handoff's paper table reads the wrong column

- Navigation time tracks path length and leaves out LLM waits. ASP run `e1_00853_s42_official_60m` logged 35.6 m in 235 s at stage 10 (6.6 s per metre); frontier run `e4_00853_s44_frontier_60m` logged 68.9 m in 472 s at stage 20 (6.9 s per metre).
- The handoff estimates the paper's ASP runs at 94-112 m. If that holds, the paper's 10% column sits near 9-11 m and its 50% column near 47-56 m, and our 60 m endpoint is 54-64% of the paper's budget.
- The handoff table set our 60 m numbers beside the paper's 100% column. The nearer match is the 50% column. No 60 m run can reach the 100% column.
- **Change to M0a:** the paper table gives F1 and GED at 10% and 50% of the estimated budget on the navigation-time axis, with the 94 m and 112 m ends as a band, beside the paper's 10% and 50% columns. The 100% column stays only for frontier (P3). $0, laptop, 2 h.

### B3. Milestone P: paper-comparable scoring

**P0. Ask the author (the student sends it; 15 min; by Wed 11-04).** The draft is in B6. If files arrive by Fri 11-20, rescore everything against them ($0, about 2 h) and make that the paper column. If not, the rebuilt reference (P2) stands, and the slide says so.

**P1. More host checks (read-only, with M0b on Wed 11-04, +30 min).**
- Read the author's `exploration/scripts/f1_score_plot.py` and `ged_score_plot.py` for the category list, any budget constant, the 10/50/100% code and any GED timeout.
- Count the classes in the pipeline's YOLOE prompt list, against the paper's 61 and the 52 in `label_mapping.json`.
- Find how `total_navigation_time_seconds` is computed.
- Check whether `semantic.txt` exists for 00069 and 00573, and whether their September runs and frontier references are still on disk.

**P2. Rebuild the paper's reference (APR, the author-protocol reference).**
- **Method.**
  - A scripted camera tour through the same pipeline and mapper, with no LLM.
  - Waypoints lie on a 1.5 m navmesh grid and are visited in shortest-tour order along navmesh paths, with a 360° turn at each, as the pipeline does after every step.
  - New code: `tools/live_policy/coverage_tour.py`, a waypoint policy for `run_pipeline_with_policy.py`. It reuses the frontier explorer's navmesh snapping. Each stage is converted with `convert_frontier_reference.py`, which uses the author's own `convert_dsg_to_yaml`. Tests come with it.
- **Two tours per scene** on 853 and 871, with different start points and orders. APR-a is the reference; APR-b measures how far the reference itself moves.
- **Pre-registration.** `PREREGISTRATION_PAPER.md` is hashed before the first tour. It fixes the spacing, the turn, the stop rule (every waypoint visited), the checks below, the budget rule (P4) and the room-target rule (P4).
- **Checks, run before any arm is scored against APR:**
  - **C1.** Room count and floor area against the paper's figures: 853, 6 rooms and 207.63 m²; 871, 9 rooms and 235.03 m². For P+, 69 has 7 rooms and 206.42 m², and 573 has 11 rooms and 537.81 m².
  - **C2.** APR-a against APR-b, on F1 and GED. If F1 falls below 0.90, the reference moves by more than the paper's margins (2.7-7.9 points). Report that as a result, not a defect.
  - **C3.** APR's recall against the HM3D human labels. For scale, the frontier explorer that ran out of frontiers reached 0.26 on 853 and 0.17 on 871.
  - **C4.** The category set. Score F1 on the classes the pipeline can detect, and report the overlap with the paper's 61.
  - **C5.** APR against the frontier-made reference.
- **Host:** about 1-1.75 h per tour, so 4-7 h for four tours. $0.

**P3. Frontier to the paper's full budget.**
- Run H1's frontier canaries to a 112 m budget instead of 60 m, and add seeds 44-46, for 5 seeds × 2 scenes.
- One run gives both results: the 60 m readout still serves as the drift check, and the 112 m end fills the frontier row of the paper's 100% column.
- **Host:** 10 runs × 40-70 min = 7-12 h, replacing the 4 canaries (2-3 h). $0.

**P4. The paper tables, built in one pass by `tools/live_policy/paper_compare.py`.**
- **Fig. 4 (left) layout.** F1 × 100 and GED at 10%, 50% and 100% of the budget, per scene and arm:
  - frontier (5 seeds);
  - ASP + DeepSeek (October, 3 seeds);
  - ASP + random (October placebo, 3 seeds);
  - ASP + exact objects (E3, 871, 3 seeds);
  - ASP + Claude and placebo v3 (E6, 5 seeds each).

  ASP arms stop at 60 m, so they have no 100% value.
- **Three references:**
  - APR, to compare with the paper;
  - the HM3D human labels, to compare arms, as before;
  - the frontier-made reference, kept for continuity and labelled unfair to ASP.
- **Each cell** gives the mean, range and n beside the paper's single number. The paper's ASP − frontier margin is drawn against our seed spread.
- **Budget rule.** Use the author's budget if it arrives by 11-20. Otherwise use the estimate, 94-112 m, as navigation time (about 620-770 s at the measured 6.6-6.9 s per metre), reported as a band.
- **Fig. 4 (right) layout.** Time and distance to predict and to find the paper's targets in our scenes: on 853 the second bedroom, and on 871 the kitchen. The rows come from 8-member live stages under the paper's rule. "Second bedroom" means the bedroom farther from the start by navmesh path, fixed in advance.
- **The room rate.** Count the rooms predicted before they are found, over the rooms not seen at stage 0, by the paper's rule: at least 2 of 8 samples, within 2.5 m, and of the same type. Do this for each live arm, with placebo as the chance rate and the paper's 9 of 28 beside it.
  - This uses live runs only, because only they have 8 members. The static replays have 4 and keep amendment 21's 1-of-4 and 2-of-4.
- **When it runs:**
  - every October run, on Sat 11-14, after APR is hashed;
  - E6, in the same pass as its analysis, on Sat 11-21.

**P+. Optional, cut first: scenes 69 and 573.**
- Two APR tours each.
- 5 frontier seeds at 112 m.
- The September 120 m DeepSeek runs rescored as "ASP + older DeepSeek, n = 1", which is the paper's own n.

This gives the four-scene average that the paper's Fig. 3 uses. It costs $0 and 10-15 host h. Human labels come only if P1 finds `semantic.txt`.

**Not planned: Claude runs to the paper's full budget.** One run per scene would prove nothing, because step 8 showed that seeds do not pair runs. Two runs would also cost $180-460 on Sonnet.

### B4. Milestone V: the validity layer in the same pass

**Why it is possible.** The layer is a fixed function of files every stage already saves: the observed graph and the member completions. E2 ran it live through `track_keep_sets` (`live_policy.py:94-122`), which calls `validate_completion` and then `support_filtered_graph`. So any stage, static or live, can be scored with and without the layer after the fact, with no new LLM call.

**What runs.** One driver, `semantic/score_stage.py`, loads each stage once and scores five views of its guesses with the frozen M1 code. It also computes P4's F1, GED and room test for that stage, so one pass yields the semantic test, the layer and the paper metrics.

| View | What it keeps |
|---|---|
| raw | every guess; the confirmatory test uses this view only |
| V | guesses that pass the validator (E2's filter_only) |
| V + vote at 0.5, 0.75 and 1.0 | guesses that also have support at or above tau over the 4 intended members (1.0 is unanimity) |
| paper rule | guesses that appear in at least 2 of 8 samples (live stages only) |

**What it reports,** for each of DeepSeek, Gemini, Haiku, Sonnet, Opus and placebo:
1. **Validity:** the share of guesses the validator removes, by reason. The midsem deck said 81% of DeepSeek's added nodes broke these rules. Now we get the same figure for five models on the same inputs.
2. **Does valid mean right?** The L2 and L3 hit rates of kept guesses against removed ones. If they match, the validator filters physics, not meaning.
3. **Does agreement mean right?** Support against L3 truth, as a reliability curve with Brier score and ECE. The isotonic calibrator is fit on one scene and tested on the other.
4. **Yield:** hits kept against guesses kept, at each tau.
5. **Decisions:** in H5, rescore the bench candidates with each model's V and unanimity views as well as raw, to see whether the layer moves the pick or the regret.

**Live.**
- The E6 Claude arm runs the original design, so the robot never sees the layer.
- The same pass scores E6's saved stages under every view, in shadow mode. That gives the layer's results on live Claude data at $0.
- It does not give the layer's live effect. That needs an acting arm in E2's design, which this plan does not run: 10 more runs, $550-1,380 on Sonnet.

**Pre-registration.** The layer's settings go into `PREREGISTRATION_SEMANTIC.md` before its hash:
- the validator config E2 used (`ValidationConfig(allow_parsed_mapping=True)`);
- the tau set;
- the calibrator;
- the five readouts.

The readouts are secondary and sit outside the 3 × 3 confirmatory family.

**The line it gives the talk.** The vote keeps what the members agree on, and ASP's score gives agreed content zero (F0). So the layer can pick out the guesses worth trusting, but ASP's score has nowhere to use them. The calibrated support becomes q(l) in M6's S_j sketch, the one objective in this plan that can use it.

**Cost:** $0; about 1 laptop day added to M1, and half a day to H5.

### B5. Changes to the schedule, money, hours, cuts and slides

- **Week 1.**
  - The email to the author (the student, 11-04).
  - The P1 host checks (11-04).
  - The matched-budget paper table in M0a (11-05).
  - `PREREGISTRATION_PAPER.md` hashed with M0b (11-05).
  - V built inside M1 (to 11-08).
- **Week 2.**
  - Tour code (L, Mon 11-09 to Tue 11-10).
  - The tours and the 112 m frontier runs (H, Wed 11-11 to Fri 11-13, beside H1 and M4, using the second container once H1 builds it).
  - C1-C5 and the APR hash (Fri 11-13).
  - October runs rescored against APR (Sat 11-14).
- **Week 3:** no change. The same driver scores E6's stages.
- **Week 4:** P4 and V run on E6 in the same pass as the E6 analysis (Sat 11-21 to Sun 11-22).
- **Money:** nothing added.
- **Host hours:**
  - +0.5 for the checks;
  - +4-7 for the tours;
  - +5-9 for frontier, net of the canaries it replaces;
  - so about +10-17 h, or about 135-142 slot-hours with the live arm and 34-41 without it;
  - optional P+ adds 10-15 h.
- **Cut order.** Three new items come first:
  1. P+ (scenes 69 and 573);
  2. frontier seeds 44-46 (seeds 42-43 stay at 112 m);
  3. APR-b, the second tour (C2 is then lost).

  Then the old list follows. APR-a on 853 and 871 is cut only after E6 is cut entirely. Its fallback is the matched-budget reading against the two existing references.
- **Never cut:**
  - the email;
  - the matched-budget re-read;
  - V's raw-against-V view (the validity rate and the kept-against-removed hit rate).
- **§10.** "No new scenes, no 100 m runs" now means no new ASP runs on new scenes or at 100 m. Frontier and tour runs to 112 m are allowed.
- **Slides:**
  - After slide 3, a new slide, "Same rules as the paper": the Fig. 4 (left) numbers beside ours at 10% and 50%, the APR column, and our seed spread against the paper's margin.
  - Slide 8 becomes the paper's room test under its own 2-of-8 rule on live runs, plus Fig. 4 (right) for 853 and 871.
  - After slide 13, a new slide, "The validity layer across five models": the validity rate, kept-against-removed hits, support reliability, and the line from B4.

### B7. Update, 11-06 (the extra work, approved by the student)

- **Pre-registration.** `tools/live_policy/PREREGISTRATION_PAPER.md` was hashed at 17:00 IST, before any new run. Amendment 1 was added at 17:04, before any tour, and the hash was redone. At 17:59 the hash was taken again (sha256 fee16733…), after a fix to the amendment's time stamp and before any new data. The amendment moves the tour onto navmesh paths, because a hand-driven tour is not limited to mapped space.
- **The author's scoring, read from his scripts on the host:**
  - F1 as in B1;
  - the plotted F1 curve holds a running maximum;
  - GED is gmatch4py's `GraphEditDistance(1, 1, 1, 1)`;
  - no budget value appears in either script.
- **gmatch4py.** It is installed from its GitHub source into `/workspace/scratch/gm`, with its package init trimmed to the GED modules. Run it with `SETUPTOOLS_USE_DISTUTILS=stdlib PYTHONPATH=/workspace/scratch/gm`.
- **Built and checked:**
  - `paper_compare.py`, 30 tests. An independent Opus recompute matched every readout to within 5e-4.
  - `paper_ged.py`, the author's GED on the host.
  - `host/coverage_tour.py` and `host/tour_waypoints.py`, 51 tests. An Opus review found one blocker: the floor snap from camera height can land on a bed top. It is fixed, and a test fails on the old code.
  - `host/run_coverage_tour.sh`, `host/stop_coverage_tour.sh` and `host/paper_queue.sh`.
- **Results so far:** `results_paper_compare/paper_compare.md`, summarised in `docs/STANDING_2026-11-06.md`.
- **The two old frontier-to-end runs.** Their stages were converted with the author's converter on the host. This added YAML files beside the old DSG files and changed nothing else.
- **Blocker.** Another user's vLLM server holds about 46 of the GPU's 48 GB. The first run (e7 853/42) failed with nvblox CUDA out of memory and was stopped.
  - `runs/apr/paper_queue.sh` waits for 12 GB of free GPU memory before each job.
  - Its order: a 3-waypoint dry run, e7 853/42 and 871/42, the four tours (APR-a and APR-b on each scene), then e7 seeds 43-46.
- **11-09: outage, restart and two queue fixes.**
  - Tyrone dropped off the network at about 09:23 IST and restarted. The queue died having launched nothing: until then it had waited for the GPU. An agent on tyrone restarted it at 16:20 with all 15 jobs (`docs/TYRONE_AGENT_BRIEF_2026-11-09.md`). The reboot had stopped the vLLM server, so the dry run started at 16:25.
  - That agent found that the explorer's stdout is block-buffered when written to a file, so `Exploration complete` never reaches the log while the explorer idles. The queue then ends a finished run as `stalled` 20 minutes later. The data is not affected.
  - Review found that the queue applied its 250 m stop to the tours, but §2b gives tours only the 4 h cap.
  - Both are fixed in `paper_queue.sh` (sha256 6ffb5601…): jobs launch with `PYTHONUNBUFFERED=1`, and only e7 jobs stop at 250 m. `host/paper_queue_ctl.sh` (48 tests) swaps the running queue for the fixed one after its current job (`docs/TYRONE_AGENT_BRIEF_2026-11-09_v2.md`). The old queue ran only the dry run and possibly e7 853/42, so no tour used the old rule. A `stalled` ending under the old queue counts as finished if the explorer's log holds `Exploration complete` or, for a tour, its summary says complete.
  - The handover worked at 17:52. E7 853/42 had logged `Exploration complete` at 17:29, so it counts as finished. The fixed queue started e7 871/42 at 17:57, with 13 jobs left. The tyrone agent then found two more traps, and both were confirmed from the laptop:
    - The queue ran inside the agent's T3 Code systemd scope. `setsid` and `nohup` don't take a process out of its cgroup, so closing that thread would have killed the queue without a log line.
    - The container had no `zstd`, so no DSG file had ever been compressed, though the queue logs `compressed their DSG` after each job. At about 3.4 GB per 871 run, the 10 GB disk rule would have skipped seeds 44-46.
  - Brief v3 (`docs/TYRONE_AGENT_BRIEF_2026-11-09_v3.md`) moves the queue into its own scope, installs `zstd` in the container and compresses the finished runs. Control script v3 changes:
    - a tour that hits the 4 h cap counts as a normal end (§2b);
    - `status` reports skips and a GPU give-up;
    - `restart` starts the queue under `systemd-run --user --scope` and refuses to start it without `zstd`.
- **11-09 to 11-10: the runs, and what they are worth (checked 11-12).** The queue ran with the GPU gate lowered to 5 GB beside another user's vLLM server (41.5 GB). Brief v3 was never applied, so no DSG file was compressed (14 GB free on 11-12). Fixed on 11-12: `zstd` is installed in the container, and every paper run is compressed and tested (40 GB free).
  - **Good:** all five e7 853 runs and e7 871/46 reached `Exploration complete`, with no GPU error. B for 853 is their median end time, 632.18 s. Only one 871 run finished, so B for 871 is the fallback, 809.08 s (§4).
  - **Crashed:** e7 871 seeds 42-45 failed twice each (first attempts in `*_FAILED_ATTEMPT_HHMM`, reruns in the plain folders). In every one, nvblox ran out of GPU memory, after which the planner had no map and the robot stood still. None counts as a frontier-end run. They are scored only as `crashed_frontier_1st` and `crashed_frontier_rerun`, apart from every paper cell.
  - **APR-a tours (the references):** 853 and 871 each reached every waypoint. nvblox died partway through both, but the tours move on navmesh paths and Hydra kept building the graph, so the final graphs (264 and 253 nodes) cover the whole tour.
  - **APR-b tours:** unusable. Hydra's backend never wrote a new graph after the first stop, so each final graph equals its stage-0 graph (2 and 4 objects). Their summaries still say complete, 100% reached. Check C2 cannot be computed; a rerun needs a free GPU.
  - **Checks (§3):** C1, rooms 13 (853) and 14 (871) against the paper's 6 and 9; start-floor navmesh 77.0 and 59.3 m² against 207.63 and 235.03 m². C3, APR-a's recall against HM3D is 0.32 and 0.21. C4, every class in APR-a is in the 52-label file. C5, APR-a's F1 against the frontier-made reference is 0.64 and 0.67. Details: `tools/live_policy/results_paper_compare_1112/c_checks.json`. Deviation: the checks were computed in the same session as the first APR scoring, not reported first.
  - **Checked:** an independent Opus recompute matched every cell, and an adversarial check confirmed the run-validity claims. Nine disclosures, including the APR-a final graphs missing about the last 60 s of each tour, are in `results_paper_compare_1112/NOTES.md`.
  - **Scores:** `tools/live_policy/results_paper_compare_1112/paper_compare.md`, with GED from the author's code on the host for every run against APR. Against APR, frontier-to-end F1 ×100 at 10/50/100% of B: 853, 12.4 / 39.5 / 55.6 (paper 18.6 / 46.5 / 58.8); 871 (n=1), 26.4 / 43.2 / 62.8 (paper 29.2 / 55.7 / 65.3).

### B6. Draft email to the author (the student edits and sends it)

Superseded on 11-06. The current draft is §6 of `docs/STANDING_2026-11-06.md`. It drops the category question, now answered by the author's `task_def/` files. It adds questions on how Fig. 4 reads its time axis: the stage value or the running best, whether the scan counts, and the frontier clock.

---

# Merged plan (as synthesized)

**Talk title:** *Right in meaning, wrong in place? A pre-registered test of ASP's semantic defense, with Claude replayed on the robot's own inputs.*

**Base:** P1, which both judges scored highest. §2 lists every flaw the judges raised and how this plan fixes it. Everything costs $0 until the smoke test on Sun 11-08. Every paid step has a hard cap and needs the student's OK first.

---

## 0. Aim

The author says ASP's LLM guesses sit in the wrong places but name the right things, and that this is enough. The student believes it. We treat it as a hypothesis and test it in three steps, cheapest first.

1. **Is the meaning right, beyond base rates?** Score the saved guesses against comparators that see the same map. That means DeepSeek V4.1 Flash, Gemini 3.8 Flash, and then Claude Haiku, Sonnet and Opus 5.5 replayed on the same inputs. The saved data costs $0; the Claude replays cost about $320.
2. **Would right meaning be enough for ASP's score?** Run an offline oracle factorial: true labels with the placement error LLMs really make, plus true room types alone. $0.
3. **Does it reach the map?** Run Claude on the original ASP design live, against a placebo that runs at the same time and is paced to Claude's waits. Every live route needs the hashed feasibility gate on Fri 11-13. Its framing comes from the science gate: confirmatory if that gate passes, a registered rule-out test if it fails and the student opted in.

Every week ends with slides that stand alone (§7).

## 1. The theses (pre-written; M7 picks the one the registered rules allow)

| Outcome | One-line answer to the author |
|---|---|
| **Works** | On the robot's own saved inputs, Claude names which rooms and objects lie in which unexplored region better than a house-statistics prior that sees the same map, the same model asked about the wrong house, and its own guesses shuffled. So the author is right that the semantics are good. The oracle factorial shows how much of that ASP's disagreement score can turn into better views once real placement error is added, and E6 shows whether it reaches the map. |
| **Mixed** | Right at house level, wrong in place. Claude knows a house like this has another bathroom, beyond the prior, but cannot say which unexplored region holds it. ASP's score runs on positions, and the factorial shows how much of the oracle's view-ranking power the region-level error throws away. |
| **Fails** | Even Claude Opus 5.5 on identical inputs does no better than a house-statistics prior that knows only what the robot has mapped. The "right semantics" in the demo is mostly base rate: an unseen bathroom remains in 88% of our stages and an unseen bedroom in 82%. Even perfect labels with real placement error keep only X% of the oracle's view-ranking power, so a stronger LLM cannot rescue *ASP's score*. The claim is about ASP's score only, not LLM-guided exploration in general. |

## 2. What the merge changed

| Flaw the judges raised | Fix in this plan |
|---|---|
| B3a, the "strong" prior, learns from one house | Three more base-rate controls: B3b (HM3D counts from other houses, if the host has them), B4 (the same LLM's claims from the wrong house) and D (a derangement inside each stage, from P2). "Supported" must beat **every** comparator at that level (an intersection-union test). |
| One-sided cluster bootstrap over about 12 runs is anti-conservative | An exact sign-flip test over 12 run clusters (4,096 flips). CIs come from a wild cluster bootstrap (Rademacher weights, 9,999 draws). |
| Many tests, with Holm only across models | One Holm family: 4 models × 3 levels = 12 hypotheses. L3 is the gate level. L4, the paper's room test, the probe and the vote test are secondary. |
| The frame said "12 counted runs", but only 11 count | The frame uses the 11 counted runs plus a 12th, named: the excluded attempt `e1_00853_s44_official_60m`. Its inputs are valid; only its outcome was excluded. That gives 6 runs per scene. FA1 runs join the cluster of their same-seed run. |
| M2 yardstick is circular (oracle sets come from the objects U_wall counts) | The bias direction is registered (toward "rejected"). A room-type-only oracle (F-room) is added. M6's rendered yardstick decides if it runs. |
| Live arm reused the DeepSeek-paced October placebo | A concurrent **placebo v3**: calibrated on the chosen Claude model's completions on non-test scene 00069, paced to Claude's own waits, and launched in registered pairs. No October arm enters the primary test (P3 E6). |
| Container venv is Python 3.9; anthropic 1.x needs 3.10 or later | Route (a): pin the newest 0.x that installs on 3.9, passing thinking and effort through `extra_body` if the types lack them. Route (b): a Python 3.10+ sidecar over a Unix socket. The M0b host check picks one; the smoke test proves it. |
| Disk not budgeted (23 GB free; about 1.5 GB per run) | Disk gate: free ≥ 1.5 GB (or the measured compressed size) × runs left + 5 GB. October DSG dumps are compressed with zstd and checked against HOST_MANIFEST. A post-run hook compresses each new run's dumps. |
| Week 1 too full | Work runs in two lanes (laptop and host). M2 moves to 11-09 to 11-12. Static replays take about 3 h of wall time, so the gate can move up to 11-13. |
| The strict gate likely says no-go, so no live Claude run at all | The gate is split. The feasibility gate (G-feas) decides whether a live run can happen. The science gate (G-sci) decides the framing: confirmatory or rule-out. The student chooses in advance whether to run the rule-out version. |
| No talk until week 4 | M0a builds a corrected "controlled negative result" block by Thu 11-05 (P3 M0). |
| Peek | Disclosed in the pre-registration. DeepSeek's October content metrics were partly seen, so its verdicts are exploratory. The Claude replays and the November live completions are the blind tests (P3). |
| Rate limits unknown | The smoke test runs 8 members at once with prompts of about 36k tokens and logs every 429. |
| Grafts from P2 | Derangement control; predicted-mass-per-region ρ; pilot base rates for the base-rate slide; the S_j objective for the M6 sketch, ceiling first, with its circularity stated. |

---

## 3. Milestones

### M0a: Talk insurance (Tue 11-03 to Thu 11-05; $0; laptop)
- **Method.**
  - `tools/live_policy/paper_table.py` takes F1 at the last stage at or below 60 m, key **`af_f1`** (`object_f1` does not reproduce the table), from `results_2026-10-31/frontier_seeds/all_scores_with_frontier.json`. It uses `stages` for the frontier-made reference and `hm3d_stages` for human labels, counted runs only. The frontier-made column is labelled unfair to ASP.
  - A new deck at `/Users/sher/project/open-slide/slides/asp-endsem/index.tsx` with a 6-slide block: ASP in one picture; E1-E3; frontier; mechanism; paper table; limits.
  - Fix the check-in errata: use 3.0% against 0.5% (not 1.7/1.5% or 2.6%); use 24.1% at 2 m on matched inputs (not 24.7%); drop the slide 3 frontier claim and the slide 4 plan; name the two filters apart.
  - An errata note listing the September claims never to repeat: the unanimity gain, "bit-identical at beta ≤ 1", "removes about 27%", Gemini breadth.
- **Control.** `numbers.csv` (1,074 rows) is the only source. An Opus reviewer gets the slides and the files, not our conclusions.
- **Rule.** Each slide number maps to a numbers.csv key or a named script output; any that does not is cut, not fixed by hand.
- **Deliverable.** A talk-ready block by Thu 11-05, even if nothing else runs. **$0, 0 host h.**

### M0b: Pre-registration and frozen definitions (Tue 11-03 to Thu 11-05; $0; 0.5 host h)
`tools/live_policy/PREREGISTRATION_SEMANTIC.md` and its `.sha256` are hashed before any LLM-versus-baseline number exists. They fix the following.

1. **Truth.**
   - **Region types.** Region types come from raw HM3D names (`<scene>_raw_objects.json`, field `category`). The match is a lower-case whole-token match against a frozen marker list:
     - bathroom: toilet, bathtub, shower;
     - bedroom: bed;
     - kitchen: oven, stove, stovetop;
     - laundry: washing machine;
     - living: couch, sofa;
     - dining: dining table (reported only, since the prompt says the scene has no dining room).
   - **Multi-label regions.** A region carries every type it has markers for. On 11-03, 00871 region 7 had both kitchen and laundry markers. A region with no markers is "other".
   - **Seen.** A region counts as seen at stage k if any of these holds: a robot stop up to k lies inside its floor or ceiling footprint; an observed room node lies inside it; or at least 2 of its reference objects are mapped within 0.5 m.
   - **Primary and secondary truth.** Primary truth is "in an unseen region". "Not yet mapped" is secondary.
2. **Levels.**
   - **L1:** room type T has an unseen region. Claims are limited to the 5 typable types, and the share excluded is reported.
   - **L2:** canonical class c has an instance in an unseen region.
   - **L3:** a predicted room or object centre lies inside, or within 0.5 m of, the footprint of an unseen region of type T, or of one holding c.
   - **L4:** a same-class unseen instance lies within 0.5 / 1 / 2 / 3 m.
   - **Paper's room test:** at least 2 of 8 members within 2.5 m of a not-yet-found region centre, scored with and without a type match.
3. **Canonical label map (about 30 classes).** Build it from strings only: the 52-word detector vocabulary, `label_mapping.json` synonym_primary, every distinct label in DeepSeek, Gemini and placebo outputs, and the raw HM3D names, with suffixes such as `bed_bedroom21` stripped. Hash it before any score. Claude labels not in the map count as "other".
4. **Sample frame (`sample_frame.txt`, 44 rows).**
   - **36 rows:** stages 3, 8 and 13 of 12 DeepSeek runs:
     - e1 official, 00853 s42, s43 and s44 (s44 is the excluded attempt, named) and 00871 s42, s43 and s44;
     - e2 filter_only, all 6 runs.
   - **8 rows:** the Gemini inputs, all from FA1 runs:
     - 00871 s42, stages 2, 3, 5 and 6;
     - 00853 s42, stage 4;
     - 00853 s43, stages 1, 2 and 5.
   - **Clusters:** 12 (scene × seed × arm). Each FA1 run joins its same-seed official run.
5. **Comparators, statistics and rules.** As in §4, plus the Claude settings (M3) and the caps.
6. **Peek disclosure.** These were seen before the hash:
   - base rates (truth only);
   - P2's pilot DeepSeek lifts against shuffled and placebo guesses;
   - P3's crude room-test counts (official 34/46, filter_only 17/38, placebo 18/40).

   So DeepSeek and October-placebo verdicts are exploratory. The Claude replays and the November completions are blind.
7. **Review.** An Opus reviewer signs that the hash predates every LLM-versus-baseline number.
8. **Host check (read-only, 30 min).**
   - which `*.semantic.txt` files exist (for B3b);
   - the container's Python versions, and whether a Python 3.10+ can be installed (uv standalone);
   - `du` of one October run directory and the zstd ratio of one DSG dump, piped (no new file);
   - `docker ps -s`;
   - whether the host pipeline calls `generate_refinement_response`. The pinned copy never does (lines 507-541).
- **Deliverables:** the pre-registration and its hash; `semantic/canon_labels.json` and `region_types.json` with their hashes; `sample_frame.txt`; the host-check note.

### M1: The $0 semantic test on saved data (Wed 11-04 to Sun 11-08; laptop)
- **Code.** `tools/live_policy/semantic/`: `region_truth.py`, `extract_preds.py`, `baselines.py`, `score_levels.py`, `paper_room_test.py`, `stats.py`. Tests go in `tools/tests/test_semantic.py`: synthetic houses with known answers; the derangement leaves base rates unchanged; the sign-flip test is exact on toy data.
- **Extraction.**
  - A new room is an id missing from the observed graph (rooms carry no `is_predicted` flag).
  - A new object has `is_predicted` set and lies more than 0.5 m from every observed object.
  - filter_only stages use the raw completions in `live_policy_raw`.
- **Scope.**
  - DeepSeek: all 259 stages (official 150 including failed and aborted attempts; filter_only 109), using track-0 members.
  - Gemini: its 8 inputs.
  - Placebo: draws on the same inputs, with recorded seeds.
- **Also measured.**
  - DeepSeek's placement-error histogram (distance to the nearest same-class unseen instance), which M2 uses.
  - P2's content metric: per-stage Spearman ρ of predicted objects per unseen region against the true unmapped count.
- **Comparators.**

  | Comparator | What it is |
  |---|---|
  | B0 | uniform over classes |
  | B1 | placebo v2 (the LLM's own mix, fit on 00069) |
  | B2 | copy the observed map |
  | B3a | logistic prior, leave-one-scene-out, fit on non-LLM stages (placebo, oracle, frontier), given the same prompt hint |
  | B3b | if the host has other houses' `semantic.txt`: P(N_c > n_obs,c), or the same for type T, given the house-size bin |
  | B4 | the same LLM's claims from the other scene at the nearest path fraction, size-matched |
  | B5 | the label-position swap within a member (1,000 draws) |
  | D | derangement: each stage's predicted content shuffled across its unseen regions (200 draws) |

  Choose B3a or B3b by each prior's own log-loss against truth, never by comparison with an LLM.
- **Rule.** §4. DeepSeek is labelled exploratory.
- **Deliverables (Sun 11-08):** `results_existing.json`; a forest plot per level; the base-rate table; the paper's room test with a chance rate (it answers the lecture follow-up); the error histogram.
- **Fallback.** If B3a's log-loss is worse than B2's, B2 is the prior. If B3b is missing, say that B3a learns from one house, and let D and B4 carry the base-rate control.

### M2: Oracle factorial, would perfect semantics be enough? (Mon 11-09 to Thu 11-12; $0; laptop)
- **Setup.**
  - Make `/tmp/cvp_review` a symlink farm into the repo copies (`review_2026-10-29/A` as `work_A`, `decision_replay_reference/calculate_uncertainty.py`, `results_2026-10-31/oracle_sets.json`, `analysis/runs.txt`) and the off-host copy. Do not edit the registered bench code.
  - First reproduce the step 6 picks: 9,600 of 9,600 must match.
- **Method.** `semantic/oracle_factorial.py` runs on the 384 bench stages (24 runs). It uses member sets of 4, the same shape as a Claude replay:

  | Arm | Member sets |
  |---|---|
  | F1 | true unseen objects at true positions |
  | F2 | true labels at a random point in the true region |
  | **F-room** | true types of unseen regions at their footprints, with object counts from a per-type prior fit on the other scene. This is the direct test of "room semantics should be enough". |
  | F3 | true labels moved by DeepSeek's measured error, plus a sweep of 0, 0.5, 1, 2 and 4 m |
  | F4 | placebo labels at true positions |
  | F5 | placebo, two seeds (the redraw floor) |
  | F6 | no guesses |

  Score the 300 candidates with fastig. Outcomes:
  - ρ with U_cone;
  - R1 regret (the author's pick, IG − 0.2/m) under U_wall and U_cone;
  - the true unseen count at the top pick.
- **Rule.**
  - Sufficiency holds if (F3 − F5) ≥ 0.5 × (F1 − F5) on ρ and the wild-cluster-bootstrap CI (by run) lies wholly above that line.
  - It is rejected if the CI upper bound falls below the line; otherwise it is inconclusive.
  - The same rule is applied, as secondary readouts, to F2 and F-room.
  - (F1 − F4) is reported as the effect of labels alone.
  - **Registered bias:** F1 is inflated by construction, so the verdict leans toward "rejected" and stays provisional until M6. If M6's rendered yardstick runs, it decides.
- **Deliverable (Thu 11-12).** `oracle_factorial.json` and one figure: the share of the oracle's ranking power kept against placement error. DeepSeek's median error is marked, and each Claude model's is added on 11-13.
- **Fallback.** If the bench will not revive by Wed 11-11, run on the 121 official stages with `audit/counterfactual.py`, which needs only fastig.

### M3: Claude backend and smoke test (code Wed 11-04 to Sat 11-07 on the laptop, $0; smoke Sun 11-08 to Mon 11-09 on the host)

**Request settings** (`tools/llm_anthropic/claude_backend.py`, official `anthropic` SDK)
- **Content, in order:** the author's prompt text, then the YAML, then the 6 slice JPEGs as base64 image blocks in sorted filename order. The author's `iterdir` order is not fixed; a minor logged deviation. Images go in the first message only, as in the author's loop.
- **Tool:** `check_collision`, with the author's 7 argument names and `strict: true`, under `tool_choice: auto`. Forced tool use returns 400.
- **Thinking and effort:** adaptive thinking, at each model's API default effort (Opus medium, Sonnet high, Haiku medium). Step down one level only if the smoke cost breaks the cap.
- **No temperature.** The author's 0.2 returns 400: Sonnet and Haiku 5.5 reject non-default values, Opus 5.5 removed sampling parameters, and API version 2026-10-21 rejects any value. No seed. Both are logged deviations.
- **Caching:** a breakpoint after the images, plus top-level automatic caching for the growing tail.
- **Transport:** `max_tokens` 16000; `max_retries` 8 with backoff; IPv4 forced.
- **History:** a conversation store keyed by (pid, sha256 of the first user message). It keeps the raw assistant blocks (thinking, text, tool_use) and resends them unchanged, append-only. `tool_result` ids come from the stored `tool_use` blocks, in order. Any length mismatch drops the member loudly; the store never edits history.
- **Meter:** reserves money before each call, then settles from usage (input, cache write, cache read, output). Caps apply per member, per run and per campaign. It writes `usage.jsonl` with the served model id, and the runner checks that id equals the pinned one.
- **Refusals:** no server-side fallback. Anthropic's default advice is to turn fallbacks on; this plan turns them off so every arm stays one model. A refusal drops the member and logs `stop_details.category`.
- **Turn limit:** 50 turns, as the author's loop. A member that hits the limit returns no text and is dropped.
- **No refinement call,** because the pinned driver never makes one. If the host check finds the live pipeline does, match it and log the change.

**Other files**
- `tools/llm_anthropic/asp_anthropic_shim.py` patches genai `generate_content` under `ASP_LLM_PROVIDER=anthropic`, dispatched from the existing LLM-logger patch point. Update **both** host copies: venv site-packages and `/workspace/tools`.
- `tools/live_policy/claude_static.py`, in the shape of `gemini_static.py`, runs inside asp-noetic. It re-renders slices with `create_scene_slices`, runs the author's loop, calls the author's `parse_response`, and enforces a hard USD cap.
- `tools/tests/test_claude_backend.py` uses a fake client to test: block mapping; image blocks; tool-id pairing; that each request body extends the last byte for byte; unchanged thinking blocks; the cap stop; the refusal drop; the 50-turn drop.
- **Python 3.9.** Use route (a) or (b) from §2, picked by the M0b host check.

**Smoke test (host)**
- One `count_tokens` call per model on a real first turn with 6 slices.
- 2 Gemini-matched inputs (00853 s43 FA1 stage 5; 00871 s42 FA1 stage 6) × 4 members × 5 settings (Opus medium, Opus high, Sonnet high, Sonnet medium, Haiku medium) = 40 members, run 8 at a time to probe rate limits.
- Score the output with the M1 code beside DeepSeek and Gemini. This checks the plumbing only.

**Go to M4 if, for each setting:**
- at least 3 of 4 members parse;
- zero history-edit 400s across at least 20 multi-turn conversations;
- every request body extends the last;
- the served id matches;
- from turn 2 on, cache reads are at least 70% of prompt tokens;
- cost per member is at most $1.60 on Opus, $1.00 on Sonnet and $0.06 on Haiku.

Otherwise fix and rerun once. Record the measured costs, image tokens, effort and 429 count in a hashed cost addendum before M4.

**Budget and fallbacks**
- **Cap $40** (expected about $27). **3 host h.**
- **Fallback:** the sidecar. If the SDK cannot run in the container at all, render the slices on the host, run the harness from the laptop, and run `parse_response` on the host.
- If M3 has not passed by Thu 11-12, the live arm is dropped. M4 may still run until Sun 11-15.

### M4: Claude replays on 44 identical inputs, plus a direct probe (Tue 11-10 to Thu 11-12)
- **Replays.**
  - Opus 5.5 and Haiku 5.5 on all 44 inputs, 4 track-0 members each (176 members per model).
  - Sonnet 5.5 on 20 inputs: the 8 Gemini inputs plus stage 8 of each run.
  - Score with the frozen M1 code.
- **Probe.** One structured-output call (`output_config.format`) per stage, with the same YAML and images. It asks for:
  - P(another unseen room) for each of 10 types;
  - P(class present in the unexplored part) for each of about 30 classes;
  - a rough x, y for each predicted room.

  Each model is asked about its own house and about the wrong house, K = 3, through the Batch API: 264 calls per model. The probe is scored apart, as a ceiling on what the model knows.
- **H5.** On the 36 bench stages, rescore the 300 candidates with each model's 4 members, against DeepSeek track 0, placebo and oracle (4 members each), and compare R1 regret. Place each model's measured error on the M2 curve, and compare the pick gain it predicts with the gain observed.
- **Cost.** Per member, from a DeepSeek-like loop (8.6 calls) to a Gemini-like one (27 calls), with Claude image tokens counted (about 28.7k per first prompt):

  | Model | Per member | Members | Range | Cap |
  |---|---|---|---|---|
  | Opus | $0.67-1.52 | 176 | $118-268 | $280 |
  | Sonnet | $0.37-0.92 | 80 | $30-74 | $80 |
  | Haiku | $0.018-0.046 | 176 | $3-8 | $10 |
  | Probe (Batch) | | | about $46 | $50 |

  Expected total about $300.
- **Power (assumed design effect 4).** About 2,100 placed items per model.

  | Level | Smallest detectable difference (80% power, Holm worst case) |
  |---|---|
  | L3 | about 5 pp |
  | L2 | 9-12 pp |
  | L1 | about 20 pp; likely inconclusive, so the probe's log-loss is the better house-level readout |
- **Deliverables (scored Thu 11-12; slides Fri 11-13):** `semantic/results_claude.json`; forest plots by model and level; probe calibration (own house against wrong house); the H5 table; all completions and ledgers.
- **Fallback.** If a cap binds, stop at whole stages and score what finished. Drop Sonnet first. If the probe fails on a model, the tool-loop result stays primary.
- **Optional, cut first:** Haiku on all 259 saved DeepSeek inputs (cap $50, about 14 host h). That gives a fully powered paired test of DeepSeek against Haiku, with an L1 detectable difference of about 8 pp.

### H1: Host readiness (Tue 11-10 to Thu 11-12; host lane; $0; 6 host h; the student approves each step)
- **Patch `host/campaign_sched.py`:**
  - FREEZE_END from the CLI or an env variable, set to 2026-11-21 06:00 (lines 49, 354);
  - POOL built from `docker ps` (line 37);
  - MAX_ACTIVE set to 2 (line 39);
  - CAP split per provider, with an Anthropic meter path for `runs/e6` only, so October spend does not count (line 38);
  - max_hours = max(9, 2 × projected T) (lines 133, 136);
  - a watchdog that kills **every process in the container except PID 1**, reads a failed `docker exec` as "unknown" (line 310), and uses anchored pgrep;
  - a post-run hook that zstd-compresses the finished run's `*_dsg.json` after a round-trip hash check.
- **Free disk.** Compress the October DSG dumps, check each against `HOST_MANIFEST.sha256` by decompress-and-hash, then remove the originals. This is reversible.
- **Second container.** `docker commit asp-noetic asp-noetic:live-2026-11`, then start `asp-noetic-b` and run a 10 m placebo dry run in it.
- **Self-check.** FREEZE_END is in the future; every POOL container is up; the watchdog kills a dummy worker.
- **Drift probe.** 4 frontier canaries: 00853 and 00871 × seeds 42 and 43, 22-38 min each.
- **Pass if:**
  - projected free disk at campaign end is at least 5 GB, using the measured compressed size per run;
  - the self-check passes;
  - the second container reaches 10 m. If it does not, use one slot.

### G: The gate (Fri 11-13; latest Mon 11-16), hashed in `PREREGISTRATION_E6_CLAUDE.md` before any launch
**G-feas: all four must hold for any live run**
1. **Backend.** The M3 criteria held through M4: zero history-edit 400s, and a drop rate of at most 25%.
2. **Host.** H1 passes.
3. **Money.** Let B = confirmed credit − Claude spend so far − $75. Let c = measured cost per member × 150 members per run (8 members × 18.7 mean stages). Pick the first row that fits:

   | Order | Choice | Fits if |
   |---|---|---|
   | 1 | Opus, 5 per cell | 10 × 1.2 × c_Opus ≤ B |
   | 2 | Sonnet, 5 per cell | 10 × 1.2 × c_Sonnet ≤ B |
   | 3 | Sonnet, 4 per cell | 8 × 1.2 × c_Sonnet ≤ B |
   | 4 | Haiku, 5 per cell | 10 × 1.2 × c_Haiku ≤ B |
   | 5 | none | |

   Opus never runs at 4 per cell.
4. **Relevance.** The chosen model's L3 hit rate beats DeepSeek's on the same 44 inputs (paired sign-flip, one-sided p < 0.10). If it does not, step down the table to the next model that does. If none does, there is no live run, because it would not answer the weak-LLM objection.

**G-sci: sets the framing and the registered prediction**
- (a) The chosen model is Supported at L3.
- (b) In H5, its offline pick gain over placebo is at least 0.6 of the oracle's, with the CI lower bound above 0. Why 0.6: 0.6 × +0.034 = 0.020, which is about the 0.019 detectable at 5 runs per cell.
- The predicted live gain, (H5 ratio) × 0.034, goes into the E6 pre-registration.

**Outcomes**

| G-feas | G-sci | What happens |
|---|---|---|
| pass | pass | confirmatory E6 |
| pass | fail | rule-out E6, only if the student opted in before 11-13; the registered prediction is "no gain" |
| fail | any | no live run; a DEVIATIONS entry; week 3 goes to M6 |

### M5 = E6: Claude on the original ASP design, live (Sat 11-14 to Sat 11-21 06:00)
- **Fri 11-13.**
  - Fit placebo v3. Run the chosen model on `dryrun_00069_s42_filter_only_10m` stages 0-2 × 8 members (24 members, cap $40).
  - A new `fit_placebo_calibration.py` writes `placebo_calibration_v3_<model>.json`.
  - Add an `ASP_PLACEBO_CALIBRATION` override to `live_policy.load_calibration`.
- **Sat 11-14, morning.** One Claude run and one placebo-v3 run, each to 10 m.
- **Launch from Sat 11-14 18:00.**
  - **Pipeline and scope:** the author's pipeline (f1ea141b), official policy, 60 m, scenes 00853 and 00871, seeds 42-46.
  - **Model and pairing:** the gate's model at its default effort. Placebo v3 runs in the second container. Each pair (Claude seed s, placebo seed s) launches together, in a registered random order across scene × seed.
  - **Pacing:** each placebo stage sleeps the per-stage median Claude wait over Claude runs finished so far (DEVIATIONS item 13 rule). Before any Claude run finishes, use the M4-measured stage wait.
  - **Names:** `e6_<scene>_s<seed>_claude_60m` and `e6_<scene>_s<seed>_placebo3_60m`. E4 and e5 are taken.
- **Primary test.** Claude minus placebo v3 on F1 AUC over 0-60 m against the HM3D human labels. Use `e1_analysis.py` through a new `e6_analysis.sh`: a scene-blocked exact permutation test (252² = 63,504 relabelings at 5 v 5), two-sided, α 0.05.
- **Readings.**
  - "Positive" if p < 0.05 and d > 0. Reaching at least +0.019 counts as the predicted size.
  - "Rules out an oracle-size gain" if the 95% CI upper end is below +0.034.
  - Otherwise "inconclusive", with the detectable effect stated.
- **Power (P3 simulation, pooled SD 0.0215, 5 per cell):**

  | True gain | Power |
  |---|---|
  | +0.034 | 0.93 |
  | +0.025 | 0.71 |
  | +0.013 | 0.28 |

  With the E1-arm SD of 0.0144, the 80% detectable effect is about 0.018. The odds of a clean rule-out are about even if the true gain is DeepSeek-sized.
- **Secondaries (Holm).**
  - Claude minus frontier. October's 3 runs per scene plus the canaries form the frontier arm, unless the drift flag fires: both canaries on a scene fall outside October's frontier range on that scene.
  - A **blind rerun of the frozen M1 scorer** on the November Claude completions.
  - Precision at 0.5, 1 and 2 m.
- **Stops and exclusions.**
  - A run ending below 50 m gets one rerun (the October rule).
  - Pause after 2 Claude runs if spend exceeds 1.3 × projection.
  - The shim caps each run at 1.5 × projection.
  - The watchdog stops the youngest run if MemAvailable falls below 12 GB.
  - Nothing launches after FREEZE_END. A run that ends after the freeze is reported as late and kept out of the test.
- **Host arithmetic.** T = 0.55 h + 18 × W, where W is the per-stage wait (the slowest of the 8 members).

  | W | T per run | Slot-hours (23 runs incl. 3 reruns, + 0.25 h cleanup each) | Wall time on 2 slots |
  |---|---|---|---|
  | 400 s | 2.55 h | 64 | 32 h |
  | 700 s | 4.05 h | 99 | 50 h |
  | 1,000 s | 5.55 h | 133 | 67 h |

  The window is 156 h. Memory is 8 + 7T GB per run, so two runs fit under 97 GB while T ≤ 5.8 h. Above that, stagger starts or use one slot.
- **Residual confounds (stated on the slide).** The LLM arm anchors candidates on the first member to finish, while placebo anchors on member 0. Drop rates may differ. Temperature is gone.
- **Deliverables:** the pre-registration and its hash; the shim; the scheduler patch; the run table; the permutation result; the ledger; DEVIATIONS items 40 onward.

### M6: Rendered "seen", rendered yardstick and an objective sketch (Mon 11-16 to Fri 11-20; $0; 6 host h)
- **Rendered "seen."** In asp-noetic with habitat-sim 0.3.3, render 4 semantic views of 90° at each stop of the 12 sample runs, plus frames every 0.5 m along `executed_path.json`, and record the visible region and object ids. Rebuild the truth, rescore M1 and M4, and report every verdict that flips. Renders run only while MemAvailable is above 40 GB; otherwise they wait for the freeze.
- **Rendered yardstick.** Count the unseen reference objects visible through the robot camera at the bench candidate poses. Rescore M2 and H5; this decides M2.
- **Objective sketch (exploratory, laptop, from P2).**
  - Score each frontier opening j by S_j = (κ·A_j + β·V_j) / (d_j + 1 m), where V_j = Σ_l q(l) · mean_m n_{m,j}(l).
  - Ceiling first: oracle content against F-geo (β = 0) against nearest frontier on the bench. Only then Claude's member votes.
  - State the circularity: when one detector model both scores and decides mapping, the oracle wins by construction.
- **Fallback.** Drop the sketch and keep the sensitivity table.

### M7: Freeze, independent check, talk (Sat 11-21 to Fri 11-27)
- **Sat 11-21 to Sun 11-22.** The E6 analysis and the blind semantic rerun. `build_results.py` and `post_campaign_numbers.py` gain E6 and M1-M4 rows.
- **Tue 11-24.** Numbers freeze. An Opus reviewer recomputes the headline numbers from the raw files with its own scorer and permutation test: AUC within 5e-4, rates within 0.5 pp. Otherwise the slide says "unverified" or the number is cut.
- **Wed 11-25.** The deck, WRITEUP §13 and DEVIATIONS 40 onward.
- **Thu 11-26 to Fri 11-27.** Two rehearsals, plus buffer.

---

## 4. Decision rules (each hashed before the data it judges exists)

**Semantic tests (M1, M4)**
- **Unit and test.** The unit is the run cluster (12 clusters). The statistic is the mean over clusters of (LLM − comparator). The test is an exact sign-flip over 4,096 flips, one-sided. CIs come from a wild cluster bootstrap.
- **Holm family.** {DeepSeek, Haiku, Sonnet, Opus} × {L1, L2, L3} on the 44 inputs: 12 hypotheses. Each hypothesis's p is the largest p over its comparators (an intersection-union test).
- **Comparators.**
  - L1 and L2: the chosen B3 (its top-k against the LLM's k claims per member), B4 and B1.
  - L3: B5, D, and B3's labels at the LLM's own positions.
- **Verdicts.**
  - **Supported:** Holm-adjusted p < 0.05.
  - **Rejected:** the CI upper bound of (LLM − strongest comparator) lies below δ, with δ = 5 pp at L1 and L2 and 3 pp at L3. A model as far ahead as Gemini was over DeepSeek at 1 m (9 pp) could not be called rejected.
  - **Inconclusive:** otherwise.
- **"The author's semantic claim holds"** if a Claude model is Supported at L3, or Supported at L1 or L2 and also beats B4. **"It fails"** if every Claude model is Rejected at L2 and L3; L1 is underpowered, so it is not required. Anything between is the mixed thesis.
- **Secondary (no gate):** L4, the paper's room test with a chance rate, probe log-loss against B3 (own house against wrong house), a member-vote likelihood-ratio test (truth ~ logit(B3) + vote, bootstrap by run), and mass-per-region ρ.

**The rest**
- **Oracle factorial (M2):** the 0.5 × (F1 − F5) line on ρ, decided by the CI, with the registered bias.
- **Smoke (M3)** and the **gate (G):** as in §3.
- **Live (E6):** as in §3.
- **Talk:** no number goes on a slide without a numbers.csv row.

## 5. Money

| Item | Cap | Expected |
|---|---|---|
| M3 smoke (40 members) | $40 | ~$27 |
| M4 Opus (176 members) | $280 | ~$190 |
| M4 Haiku (176) | $10 | ~$6 |
| M4 Sonnet (80) | $80 | ~$52 |
| M4 probe (Batch, 3 models) | $50 | ~$46 |
| **Static subtotal** | **$460** | **~$320** |
| Placebo v3 calibration (only if live) | $40 | $1-36 |
| E6 live, set by the gate table | ≤ B; $900 at the Sonnet central case | Sonnet $550-1,380 for 10 runs; Haiku $27-69; Opus $1,000-2,280 |
| Optional: Haiku on 259 inputs | $50 | $19-48 |

**Tiers by confirmed credit**

| Credit | Static work | Live arm |
|---|---|---|
| $500 | Opus, Haiku and probe | at most Haiku, 5 per cell; Sonnet static is dropped if Opus runs long |
| $1,000 | all static | Sonnet at 4 per cell with DeepSeek-like loops; otherwise Haiku |
| $2,000 | all static | Sonnet at 5 per cell; Opus only if its loops are short |

**Committed caps at the top tier:** about $1,400.

**Not spent:** DeepSeek's remaining $25 (October outputs are reused) and Gemini's unconfirmed balance.

## 6. Host hours

| Item | Hours |
|---|---|
| M0b check | 0.5 |
| M3 install and smoke | 3 |
| M4 replays | 8 |
| H1 readiness and canaries | 6 |
| E6 calibration and 10 m smokes | 2 |
| E6 campaign | 99 slot-hours central (64-133), about 50 h of wall time on 2 slots |
| M6 renders | 6 |
| **Total** | **about 125 slot-hours** (about 24 without a live arm; +14 for optional Haiku-259) |

## 7. Week by week (lane L = laptop, lane H = host session)

**Week 1 (Tue 11-03 to Mon 11-09)**
- **L:** M0a talk insurance (to Thu 11-05). M0b pre-registration and hash, with the reviewer's sign-off (to Thu 11-05). M1 on 259 DeepSeek stages, Gemini's 8 and placebo (Wed 11-04 to Sun 11-08). M3 code and fake-client tests (Wed 11-04 to Sat 11-07).
- **H:** the read-only host check (Wed 11-04). Install the SDK route and run the smoke test (Sun 11-08 to Mon 11-09). Hash the cost addendum (Mon 11-09).
- **Talk by Mon 11-09:**
  - the corrected negative-result block;
  - the base-rate slide;
  - the paper's room test with a chance rate;
  - DeepSeek's semantic verdict (exploratory).

**Week 2 (Tue 11-10 to Sun 11-15)**
- **L:** M2 oracle factorial (Mon 11-09 to Thu 11-12). Score M4 and run H5 (Thu 11-12).
- **H:** M4 replays and the probe batch (Tue 11-10 to Thu 11-12). H1 readiness and canaries (Tue 11-10 to Thu 11-12).
- **Gate (Fri 11-13).** Then placebo v3 calibration. The 10 m smokes run Sat 11-14 morning, with launches from 18:00.
- **Talk by Sun 11-15:**
  - "Is it the model?", with 5 models on identical inputs;
  - the oracle-factorial figure, with each model's error marked;
  - probe calibration;
  - the hashed gate decision.

**Week 3 (Mon 11-16 to Sun 11-22)**
- **H:** E6 runs, with daily checks of spend against projection, MemAvailable, free disk and the pacing flag. Freeze at Sat 11-21 06:00. M6 renders run when memory allows.
- **L:** the objective sketch (Wed 11-18 to Fri 11-20). E6 analysis and the blind semantic rerun (Sat 11-21 to Sun 11-22).
- **Talk by Sun 11-22:**
  - the live result, or the no-go with its arithmetic;
  - the render-sensitivity table;
  - the sketch figure.

**Week 4 (Mon 11-23 to Fri 11-27)**
- Numbers freeze Tue 11-24; independent recompute; deck Wed 11-25; rehearsals and buffer.

## 8. Cut order and what never gets cut

**Cut in this order:**
1. Haiku-259.
2. The objective sketch.
3. Sonnet static.
4. The probe.
5. Canaries, down to 1 per scene.
6. E6, from 5 to 4 per cell (never Opus at 4).
7. E6 entirely: if M3 has not passed by Thu 11-12, if G-feas fails, or if the gate slips past Mon 11-16.
8. M6 renders.

**Never cut:**
- M0a;
- the M0b hash before any number;
- M1;
- M2 (in its fallback form if needed);
- the concurrent, paced placebo beside any live Claude run;
- the independent number check.

**Fallback talk:** M0a + M1 + M2 (+ M4) is a complete talk on its own.

## 9. Risks

1. **The "unseen" truth is a proxy.** Doorway views inflate the base rates. M6 renders camera views to check.
2. **Two houses only.** B3a learns from one house, and B3b needs host files. Every verdict is pilot-level, and the derangement and wrong-house controls carry the base-rate defense.
3. **L1 is underpowered at 44 inputs** (about 20 pp detectable). Expect "inconclusive" there; the probe and Haiku-259 add power.
4. **Claude integration.**
   - Python 3.9 against SDK 1.x.
   - Preserved thinking: the shim must never edit history.
   - Slices of 5400 × 3600 px cost up to 4,784 tokens each.
   - Rate limits on an account tier we do not know.
   - Refusals drop members.
   - The temperature and seed deviations.
5. **Cost.** Claude may loop like Gemini (23-31 calls per member), not like DeepSeek (8.6). DeepSeek's real profile is 22.5k prompt tokens per call, not 9k. The smoke test, the M4 measurement, per-run caps and the gate table control this.
6. **The bench code hard-codes `/tmp/cvp_review`,** which the 11-01 reboot wiped. The symlink farm must reproduce 9,600 of 9,600 picks first.
7. **The yardstick is weak** (U_wall counts 19% of next-mapped objects), so M2 and H5 stay provisional until M6.
8. **Host.**
   - Disk is 98% full.
   - The shared host's memory: the OOM killer struck on 10-28.
   - The scheduler bugs: FREEZE_END skips every launch, and the watchdog leaves paid workers running.
   - A second container is not yet built.
   - The wall-clock limit has already cost one E1 cell.
9. **Schedule.** If M3 slips past Thu 11-12, the live arm goes. If the gate slips to Mon 11-16, only 108 h of window are left.
10. **Forking paths.** Every choice of model, effort, n and framing is hashed before launch. The objective variants live only in the exploratory sketch.

## 10. Deliberately not doing
- No change to the author's prompt, ensemble size, 50-turn cap, motion or scorer in the main tests. The only changes are the ones Claude's API forces (no temperature, no seed, adaptive thinking, tool_choice auto, sorted image order), and each is logged.
- No single-seed "demo" live runs: step 8 showed seeds do not pair runs. No Opus at 4 per cell. No reuse of the October placebo in the primary test, and no pooling of October and November arms.
- No Batch API for the multi-turn loop (each turn would wait on a batch, and the 5-minute cache would lapse). Batch is for the single-call probe only.
- No refusal fallbacks to other models inside an arm.
- No Fable 5.1 ($10/$50 per million tokens). No Gemini 2.5 Pro, and no Gemini beyond its 8 inputs, unless the balance is confirmed.
- No new scenes, no 100 m runs, no new objective in live runs, and no detector retraining.
- No fixes to the September docs or paper, and no commits, unless the student asks.

## 11. Slide outline (works under any outcome)
1. **Title:** "Right in meaning, wrong in place?"
2. **ASP in one picture:** 8 guessed graphs, and a score that rewards disagreement, with no term for truth or for unknown space.
3. **What we found before:**
   - DeepSeek − random +0.013 [−0.012, +0.040], p 0.22;
   - validator +0.003;
   - perfect objects +0.034 (p 0.10, the floor);
   - frontier at least as good, in 22-38 min against 2.1-5.7 h.
4. **Why:** swapping DeepSeek's guesses for random ones barely moves the pick (ρ 0.20 against 0.19).
5. **The author's defense and the student's hypothesis,** and the three questions we ask.
6. **The base-rate trap:**
   - an unseen bathroom remains in 88% of stages, a bedroom 82%, a kitchen 56%;
   - random room types "exist unexplored" more often than DeepSeek's (pilot 0.95 against 0.857, type-shuffled 0.834; re-derived under the frozen rule).
7. **Four levels of "right",** and the controls a skeptic accepts: a prior that sees the map, the wrong house, shuffled positions, derangement.
8. **The paper's room test with a chance rate:** LLM against paired placebo against the paper's 9 of 28.
9. **Same inputs, five models (L1 and L2, "what"):** DeepSeek, Gemini (8 inputs), Haiku, Sonnet, Opus.
10. **L3 ("roughly where") and the distance bands.**
11. **The probe:** what each model knows when asked directly, own house against wrong house.
12. **Perfect labels, real placement error:** the factorial, F-room and the error sweep, with each model's error marked.
13. **Claude in the decision:** H5 pick regret against placebo and oracle, predicted against observed.
14. **Live:** Claude against paced placebo against frontier, with the CI drawn against the +0.034 line. Or the hashed no-go with its arithmetic.
15. **Sensitivity:** rendered "seen" and the rendered yardstick.
16. **What semantics would need:** the S_j sketch (exploratory).
17. **Limits:** 2 houses, the proxy truth, static replays, the weak yardstick, residual confounds.
18. **One-line answer to the author:** the works, mixed or fails version.

**Backup slides:** cost and host arithmetic, the power curve, the deviations list, and the paper table (af_f1).

## 12. Facts checked

**Checked on 11-03 by this synthesis ($0, read-only)**
- **Counted runs.** 11 DeepSeek runs count: 5 official and 6 filter_only. `e1_00853_s44_official_60m` stopped at 46.8 m (wall clock), has 16 stage dirs and was excluded (`run_table.csv`; listing).
- **Sample stages.** All 36 (stages 3, 8 and 13 of the 12 runs) have `habitat_scene_graph_original_graph0.yaml` and 5-8 member completions. The filter_only stages hold `live_policy_raw`. All 36 are in the bench's `stages.jsonl` (384 stages, 24 runs).
- **Gemini inputs.** The 8 inputs are as listed in M0b; 00853 s43 FA1 stage 6 and the first 00871 s42 FA1 stage-5 test got 0 Gemini members (`gemini_static*_scores.json`).
- **Pinned `llm_completion.py`.**
  - temperature 0.2, thinking_budget −1, VALIDATED mode, max_turns 50;
  - images go in the first message only;
  - the loop returns None after 50 turns;
  - `_run_single_ensemble_member` never calls `generate_refinement_response`.
- **`campaign_sched.py`:** POOL (line 37), CAP 30.0 (38), MAX_ACTIVE 3 (39), FREEZE_END 2026-10-31 09:00 (49, 354), max_hours 7.5 (133, 136), watchdog `pkill -f run_pipeline_with_policy.py` (310).
- **`run_live_run.sh`:** the venv is python3.9; it md5s both shim copies.
- **claude-api reference.**
  - anthropic 1.x needs Python 3.10 or later; on 3.9, pip resolves the last 0.x.
  - Opus 5.5: thinking cannot be disabled; effort defaults to medium.
  - Sonnet 5.5: effort defaults to high; non-default temperature returns 400.
  - Haiku 5.5: effort defaults to medium.
  - API version 2026-10-21 rejects temperature, top_p and top_k on every model.
  - Forced tool_choice returns 400; auto works.
  - Edited history invalidates thinking blocks, with a 400 for accounts created from 2026-08-31.
  - Images cost up to 4,784 tokens at 2,576 px.
  - The minimum cacheable prefix is 512 tokens.
  - Refusal fallbacks are opt-in; Anthropic recommends them on, and this plan keeps them off.
- **Region typing.** 00871 region 7 holds kitchen and laundry markers, hence the multi-label rule. 00853 region 5 holds a dining table, though the prompt says the scene has no dining room.
- **B3b.** The laptop holds no HM3D `semantic.txt` for other houses, so B3b depends on the host.

**Taken from P1-P3 and not rechecked here**
- DeepSeek profile: 22.5k prompt and 1.93k completion tokens per call; 8.6 calls per member.
- Gemini profile: 23-31 calls per member; about 40k prompt tokens per call.
- Slices: 5400 × 3600 px.
- About 1.5 GB per run dir.
- Base rates: 88.4% bathroom, 82.2% bedroom, 79.2% living room, 55.6% kitchen, 42.1% laundry.
- The power simulation: 0.93 / 0.71 / 0.28.


---

## Appendix R. Red-team findings (full)

I checked the plan against the repo and the offline copy. Most of its facts hold:
- 150 official and 109 filter_only stages have inputs.
- Gemini's 8 inputs are as listed.
- 00871 region 7 has both kitchen and laundry markers.
- The scheduler line numbers are correct.
- The live runs made no refinement call: there were 2,096 final 'stop' calls for 2,114 members. The plan is right on this and the brief is wrong.

The blocking defect is the conversation-store key. It collides in the threaded static harness, so M3 and M4 fail as specified until the key changes. Next come four threats to E6's validity and feasibility:
- Placebo v3 does not match member agreement or drop rates.
- The reused pacing rule flagged all 5 pairs in October.
- G-feas has no time or memory check, and the 2-slot plan fails at plausible Claude waits.
- The 3,000-call cap and 16k-token truncation (if Claude loops like Gemini) would cut runs short and add reruns.

On framing:
- 'Mixed' is the default under a null.
- L3 credits completion of partly seen rooms.
- The label map is built without Claude's labels, and 29.5% of DeepSeek's labels fall outside the detector vocabulary ('bed' among them).
- The author's prompt names bedrooms and bathrooms, and 90% of DeepSeek's new rooms are exactly those.

On dependencies: M6 must move before the gate, and the bench symlink list needs completing. Fix these before hashing M0b. The $0 lane (M0a, M1, M2 with F0, M4) can carry the talk without E6.

- **FATAL: As written, the Claude conversation store breaks the static harness that M3 and M4 depend on. The store is keyed by (pid, sha256 of the first user message), and in the static harness all 4 members of a stage share both. So members read and overwrite each other's histories.**
  - Evidence: gemini_static.py runs members as threads in one process: ThreadPoolExecutor (line 25), pool.map over 4 members (lines 121-122). It renders slices once per stage (line 117). llm_completion.py gives every member of a graph the same contents: prompt, YAML, then images (lines 278-289). The plan builds claude_static.py 'in the shape of gemini_static.py'. Live runs hide the bug: MAX_PARALLEL_WORKERS 8 (pipeline_config.yaml line 108) equals the 8 jobs, so each member gets its own spawned process. In the static harness every stage collides, so members are dropped or cross-wired, and the one allowed smoke rerun is used up.
  - Fix: Remove the (pid, hash) key. Attach the raw Claude content blocks to the _FakeContent object the shim returns. genai Chat stores that same object in its history and passes it back on the next call (the shim docstring says so), so the shim can read the blocks back from the history. Alternatively, key each turn by a hash chain over the full prior history. Add a fake-client test in which 4 threads send the same first message at once.
- **MAJOR: Under a true null, the outcome rules default to 'Mixed', whose one-liner makes a positive claim. 'Fails' is close to unreachable.**
  - Evidence: The plan's own power table puts L2's detectable difference at 9-12 pp and L3's at about 5 pp (80% power, Holm worst case of about 3.5 SE). That makes the SE about 2.6-3.4 pp at L2 and about 1.4 pp at L3. So 'Rejected' (CI upper bound < δ) needs a point estimate at or below about 0 at both levels. 'Fails' needs all 3 Claude models Rejected at L2 and L3, which is unlikely even if semantics are pure base rate. Every all-inconclusive pattern then falls into 'anything between', and that thesis says 'Claude knows a house like this has another bathroom, beyond the prior'. Choosing the 'strongest comparator' after seeing the data is also a union rule with no adjustment.
  - Fix: Pre-write a fourth outcome, 'Inconclusive', with its own one-liner. Make Mixed require Supported at L1 or L2 (and beating B4) while not Supported at L3. Name the rejection comparator in advance, or use Bonferroni across comparators.
- **MAJOR: The author's prompt plants the room types. The 'semantics look right' demo is mostly the prompt hint plus base rate.**
  - Evidence: pipeline_config.yaml line 101 tells the model: 'Scene may contain more than one bedroom and more than one bathroom.' Across 214 stages of the 12 sample runs, DeepSeek track-0 members named 755 new rooms: 512 bedroom and 167 bathroom (90%), then study 27. The plan's own base rates are an unseen bedroom in 82% of stages and an unseen bathroom in 88%.
  - Fix: Put this count on the base-rate slide. Read L1 room claims as an echo of the prompt unless they beat B3 given the same hint. As an extra exploratory check, replay Haiku (about $5) with that one sentence removed to show how much of the room mix the hint sets. Keep it out of the main tests.
- **MAJOR: L3 gives credit for completing rooms the robot has partly seen. The author's claim is about rooms in the unexplored part.**
  - Evidence: A region counts as seen only with a stop inside it, an observed room node inside it, or at least 2 reference objects mapped within 0.5 m. The detector maps about 1 in 12 objects in view. So a bathroom with one mapped toilet, or one seen through a doorway, still counts as 'unseen', and a sink placed next to that toilet scores an L3 hit. B5, D and B3-at-LLM-positions all keep the LLM's positions, so none of them removes this credit.
  - Fix: Pre-register a stratum of 'unobserved' regions: no mapped vocabulary object, and no observed room node within 0.5 m of the footprint, at stage k. Run the L3 gate on that stratum, and report the partly seen stratum separately.
- **MAJOR: The label map and vocabulary choices will drive L2/L3, and they are biased against Claude.**
  - Evidence: The 52-word detector vocabulary (label_mapping.json) has no bed, plant, bookshelf, armchair or desk. Of 7,775 DeepSeek predicted objects in those runs, 29.5% fall outside the vocabulary and its synonym table: plant 598, bed 470, bookshelf 261, armchair 206. The Gemini static scores give DeepSeek in_vocab of 92/148 and 230/343. The plan builds the map only from DeepSeek, Gemini and placebo strings, and Claude labels missing from it count as 'other'. Classes outside the vocabulary can never be mapped, so they cannot raise F1.
  - Fix: Freeze one rule-based normaliser and apply it to every model: lower case, '_' to space, strip plurals, a head-noun rule, and an explicit synonym table. Report the unmapped share for each model. Score L2/L3 two ways: detector-vocabulary classes (primary for any link to ASP's map) and all classes (for 'semantics').
- **MAJOR: Placebo v3 matches shape but not member agreement or member drops, and ASP's score is driven by disagreement. So E6 does not isolate content.**
  - Evidence: The score is H(pooled) minus the mean within-member entropy, with one group per completion file (calculate_uncertainty.py lines 325-333 and 521-561). In October, LLM members agreed within 1 m on 29.4% of guesses against 4.4% for placebo, and official runs lost 7-24% of members while placebo lost none (handoff §2). Claude has no temperature setting (default 1.0, against the author's 0.2), so its agreement rate will differ again.
  - Fix: Fit placebo v3 to Claude's measured within-stage agreement rate, for example by drawing a shared stage-level set and copying each item into each member with a fitted probability. Drop placebo members at Claude's measured drop rate. Report both as pre-registered balance checks.
- **MAJOR: The pacing rule is the one that left every October pair flagged.**
  - Evidence: WRITEUP line 95: all five E1 pairs were flagged under the DEVIATIONS item 13 rule, with 10/16, 10/17, 13/15, 8/12 and 16/19 stages more than 20% off. The plan reuses that rule. Before any Claude run finishes, it uses M4 static waits, which come from 4-member jobs, while the live wait is the slowest of 8 members.
  - Fix: Pairs now launch together, so yoke them: placebo stage k sleeps the partner's measured stage-k wait when it is known, and the median otherwise. Or run the host's quiet-wait patch (ASP_DSG_QUIESCENT_S) in both arms and pre-register a check that the map snapshot does not depend on wait length. Record the pacing flag as a covariate.
- **MAJOR: G-feas has no time or memory check. The 2-slot plan fails at plausible Claude waits, and the scheduler's NEW_HOURS is not on the patch list.**
  - Evidence: DeepSeek's per-stage wait (slowest member, from usage.jsonl, 267 inferred stages) was mean 674 s, median 569, p90 1,278 and max 2,322. The plan's table stops at 1,000 s. With 107 GB available and the 12 GB watchdog floor, two runs fit only while 2(8 + gT) ≤ 95. That gives T ≤ 5.6 h (W ≤ about 1,020 s) at 7 GB/h, and T ≤ 4.9 h (W ≤ about 880 s) at 8 GB/h. With one slot, 23 runs need 133 h at W = 1,000 s and 156 h (the whole window) at 1,200 s. campaign_sched.py NEW_HOURS = 6.5 h for paid runs (line 45) drives both the freeze check (line 354) and the memory projection. The plan also gives 3 h (§2) and 8 h (§6) for the M4 replays. The 10-28 OOM killed another user's process.
  - Fix: Add G-feas item 5. Simulate the live wait from M4 as the slowest of 8 members per stage, and require the p90 projection to finish every run before the freeze under the memory rule. Patch NEW_HOURS and NEW_RATE from measured values. Give each container a docker memory limit, so an OOM kills our run and not other users' work.
- **MAJOR: The per-run call cap will cut live Claude runs short if Claude loops like Gemini.**
  - Evidence: run_live_run.sh sets MAX_CALLS=3000 (line 29), passed as ASP_LLM_MAX_CALLS, and live_runner.py sets MAX_CALLS_PER_STAGE = 400. Gemini static made 1,133 calls for 44 attempted members, about 26 each, and 26 × 150 members is about 3,900 calls per run. The cap would hit near stage 14, so runs end below 50 m and need reruns. When the cost cap hits, the shim returns empty text to all 8 members, which fires the outer retry loop.
  - Fix: Set the call cap from the M4 p99 calls per member × 150 × 1.2 and log the change. Make a cap stop end the run cleanly and label it, instead of returning empty text.
- **MAJOR: max_tokens 16,000 without streaming will truncate some members' output, and raising the cap needs streaming.**
  - Evidence: Gemini static calls went over 16,000 output tokens 5 times in 1,133 (max 23,583). At about 26 calls per member, roughly 11% of members would hit the cap at least once. DeepSeek hit 16,000 three times. Adaptive thinking counts against max_tokens. The Python SDK raises ValueError for large non-streaming max_tokens values.
  - Fix: Use messages.stream(...).get_final_message() with max_tokens 64,000. Log stop_reason and report drops by cause and by stage. Pre-register a check that drop rates balance across arms.
- **MAJOR: G-sci (b) almost cannot pass, and H5 confuses content with member diversity. In practice E6 runs in rule-out mode.**
  - Evidence: Step 6 measured an oracle/placebo regret ratio of 0.850 (CI 0.804-0.893) on 384 stages. H5 uses 36 stages, so its CI is about 3.3× wider, roughly 0.70-1.0 for the oracle itself. Requiring a Claude gain ≥ 0.6 × the oracle gain with the CI lower bound above 0 asks Claude to match the oracle. The 0.034 anchor comes from 00871 only, at 3 v 3, registered under deviation 26 after the data were seen. H5's placebo is calibrated on DeepSeek, while Claude's members differ in diversity.
  - Fix: Drop (b) as a gate, or replace it with a prediction from the M2 error curve. In H5, use Claude's own content shuffled across positions (B5 or D) as the comparator, so diversity stays fixed. Tell the student now that rule-out mode is the likely path.
- **MAJOR: M6 runs too late to decide M2, and rendering does not remove the circularity.**
  - Evidence: M6 runs 11-16 to 11-20, after the gate, and only while MemAvailable is above 40 GB. Two live runs use about 94 GB, so renders slip past the freeze, yet the plan says M6 'decides M2'. In October, validate_geometry_depth.py already rendered habitat-sim at 128 px inside the container, using little memory. The rendered yardstick still counts the same reference objects the oracle places, so it fixes occlusion, not circularity.
  - Fix: Render in week 2 (Tue-Thu, while M4 mostly waits on the API), with a memory floor of about 20 GB, so the gate uses the rendered yardstick. Weight the yardstick by each class's detection yield in the October runs, so classes the detector never maps count zero. Keep the registered bias statement.
- **MAJOR: In M2, 'perfect semantics' depends on how the oracle members are made to disagree. If all members agree on the truth, ASP's score is zero.**
  - Evidence: oracle_graph (live_policy.py 315-371) gives each member its own random draw of 6-16 true objects (Poisson mean 10). That draw is what makes members disagree. If all 4 members carried the full true set, the score would be zero everywhere and the pick would be the nearest candidate (the observed_only docstring says the same). F1's ranking power is therefore partly a product of the subsampling, and F-room's depends on how its per-type counts vary across members.
  - Fix: Add F0, with every member holding the full truth, as an anchor. Show it on a slide: 'perfectly right and agreed semantics are invisible to ASP's score.' Repeat F1-F3 at 25%, 50% and 100% subset sizes.
- **MAJOR: The symlink farm needed to revive the bench is incomplete, and the fallback has the same dependency. M2 is on the never-cut list.**
  - Evidence: The code hard-codes /tmp/cvp_review/{work_A, audit/audit, refs, gates, runs, analysis_pre/runs.txt, pipeline_pinned_copy} and /tmp/cvp_bench/refs/<scene>_walls.npz (bench.py lines 29, 51, 59, 366; audit.py 36, 47, 51, 234; replay.py 33-49). The plan links only work_A, calculate_uncertainty.py, oracle_sets.json and analysis/runs.txt. The repo's analysis/runs.txt lists 25 runs (it adds e3_00871_s44 at the end), against the bench's 24. audit/counterfactual.py imports the same work_A tree.
  - Fix: Build the farm from a grep of every /tmp/cvp_* string in A/, audit/ and bench/. Write analysis_pre/runs.txt from the first 24 lines. Point the walls path at bench/walls/*.npz. Reproduce 9,600 of 9,600 picks before writing new code, and budget a day for it.
- **MAJOR: Account limits and the preserved-thinking check are not confirmed before spending.**
  - Evidence: All Claude spend lands in November: $320 static plus up to $1,380 live. Rate limits are found only from 429s in the smoke test on 11-08. Preserved thinking is enforced by default only for accounts created on or after 2026-08-31. On an older account, the smoke criterion 'zero history-edit 400s' passes automatically and proves nothing.
  - Fix: Before M3, read the Console: usage tier, per-model RPM/ITPM/OTPM, any monthly or workspace spend limit, and the account's creation date. Ask for raises early. Send thinking.block_binding.prefix_mismatch_behavior 'error' (beta thinking-binding-controls-2026-08-01) so the check means the same on any account.
- **MAJOR: A rule-out E6 is the largest spend and host risk for little information.**
  - Evidence: From the plan's own numbers: power is 0.28 for a DeepSeek-size gain (+0.013), and a clean rule-out of +0.034 is about a coin flip. That costs $550-1,380 on Sonnet, about 100 slot-hours, and carries the host risks above.
  - Fix: Show the student these odds before the 11-13 opt-in. If E6 runs in rule-out mode, cap it ahead of time. Consider putting the money into wider static coverage instead: Opus on more stages and Haiku on all 259, which tighten the semantic answer.
- **MINOR: The drift flag fires by chance about half the time, and it pools October arms.**
  - Evidence: With 3 October frontier runs per scene and no drift, the chance that both of 2 new canaries fall outside their range is 3/10 = 0.3. The chance that at least one of the two scenes flags is 0.51. This also conflicts with §10's 'no pooling of October and November arms'.
  - Fix: Flag drift only if a canary lies more than 2.5 October SDs from the October mean. Report Claude minus frontier against the canaries and against October separately, without pooling.
- **MINOR: Region footprints taken as AABBs overlap and inflate base rates.**
  - Evidence: Floor and ceiling AABBs from semantic_geometry.json put 15% (00853) and 26% (00871) of the covered area in two or more regions. Living-room boxes cover 56% and 45% of the area, and in 00871 kitchen and laundry each cover 35%.
  - Fix: Rasterise floor triangles from the semantic mesh to get footprints. Report the chance rate for each type and level.
- **MINOR: The base-rate comparators are weak or fitted to the wrong model.**
  - Evidence: B3a learns from one house. B1 is DeepSeek's mix: placebo_calibration.json was fitted on 20 DeepSeek completions on 00069, with rooms bedroom 22, bathroom 10, kitchen 2, and both 'coffee table' and 'coffee_table'.
  - Fix: Build B3b from HM3D semantic annotations for 30 or more houses (small text files; host download with the student's OK). Otherwise do not call B3a a house-statistics prior. Fit B1 for each model from that model's own marginals on inputs outside the frame.
- **MINOR: The smoke test peeks at test inputs, and the relevance gate uses the raw L3 hit rate.**
  - Evidence: The smoke scores 5 settings on 2 of the 44 sample-frame inputs. A model that places more items in large living or kitchen footprints raises its raw L3 rate without better semantics.
  - Fix: Run the smoke on the 00069 dry-run stages and do not score semantics in it. Gate on L3 lift over each model's own derangement (D), not on the raw rate.
- **MINOR: The statistical family and the CI method need tightening.**
  - Evidence: DeepSeek is labelled exploratory but sits inside the confirmatory Holm family. Sonnet covers only 20 inputs and Gemini only 3 clusters. A Rademacher wild cluster bootstrap with 12 clusters has only 4,096 distinct draws. All clusters sit within 2 houses.
  - Fix: Make the confirmatory family 3 Claude models × 3 levels on a common input set. Report DeepSeek and Gemini descriptively. Get CIs by inverting the sign-flip test. State that inference holds only for these two houses.
- **MINOR: The pre-registration hash has no outside timestamp.**
  - Evidence: Nothing has been committed since 10-28 13:06, and a local .sha256 file cannot show when it was made.
  - Fix: With the student's OK, commit and push the pre-registration, or email its sha256 to the course staff before any number exists.
- **MINOR: Integration details: timeouts, IPv4, raw blocks, cache writes, disk.**
  - Evidence: With the SDK's default 600 s timeout and max_retries 8, one call can take up to 90 min. The shim's IPv4 fix patches urllib3 only, and httpx needs its own transport. A 0.x SDK may drop unknown block fields when re-serialising. The 4 members of a graph send identical first messages at the same moment, so each writes the cache; on Opus that wastes about $0.54 per graph-stage, about $20 per live run. The disk gate leaves out the docker commit size and /root/.ros/log growth.
  - Fix: Set timeout to about 300 s and max_retries to 3. Force IPv4 through the httpx transport. Store raw response JSON from with_raw_response and resend it. Pre-warm the cache with one max_tokens 0 call per graph. Clear the ROS logs and size the image before docker commit.
- **MINOR: Smaller design gaps.**
  - Evidence: F3's error histogram leaves out guesses with no unseen instance of that class. Runs that end after the freeze drop out, which removes the slowest runs. The placebo override and fit_placebo_calibration.py are scheduled on gate day. The paper's room test needs 8 members, but the replays use 4.
  - Fix: Add a label-error axis to F3. Exclude late runs at pair level, with a launch cutoff from the p90 run time. Write and test the M5 code in week 1. Report the room test as 1-of-4 and 2-of-4 with a chance rate, not against the paper's 9/28.
