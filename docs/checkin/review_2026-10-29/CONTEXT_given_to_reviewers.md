# Context for the critical review, 2026-10-29 (IST)

Read this first. It gives the facts, where the evidence is, and the main session's working reading. The reading is a set of hypotheses to test, not conclusions to adopt. Where a file disagrees with this note, the file wins; say so.

## 1. What the project is

A computer-vision course project at the user's university. Stage one reproduced **Active Semantic Perception (ASP)**:
- paper: arXiv 2510.05430;
- code: github.com/grasp-lyrl/active_semantic_perception, pinned at commit f1ea141b1886d33ab8f4e4b791db4d3c92150b27, with local working-tree changes in /tmp/cvp_review/author_worktree_diff.patch.

### The ASP loop, per stage
1. Hydra/Clio builds a 3D scene graph of rooms and objects from simulated RGB-D in HM3D (Habitat).
2. Two tracked graphs (graph0, graph1) each go to a 4-member LLM ensemble, which predicts unseen rooms and objects ("completions", 8 files per stage).
3. The planner samples candidate viewpoints (UNCERTAINTY_SAMPLES: 300), scores them by an information-gain / uncertainty term computed over the predicted graphs, keeps the top candidates, checks them for A* reachability, and drives to the chosen one.
4. Repeat until a path budget is spent.

The predictions never enter the map. They only steer viewpoint choice.

### Stage two: our extension (September), the "validity layer"
- Whole-graph validation of LLM predictions: structural and geometric checks.
- Ensemble support thresholds (unanimity = all 4 members agree).
- Calibration of that support.
- A risk-sensitive viewpoint score.

On a 3-scene, 120 m DeepSeek matrix (scenes 00069, 00573, 00853, seed 42), unanimity raised static graph F1 and lowered normalized GED. A later check found that unanimity keeps 19 of 8,943 predicted nodes (99.8% removed). Scoring the observed graph alone gives the same numbers (F1 0.5219/0.4351/0.4957 against 0.5218/0.4349/0.4957). So the "gain" showed the DeepSeek predictions hurt the graph; it did not show the filter adds value. Calibration and the risk term showed no benefit. The live effect was never tested.

The user's summary of this: the validation layer was removing (almost) all the guesses, and F1 did not improve, because F1 depends on where the robot explores.

### Stage three: the live campaign (2026-10-28 to 10-29)
This tests in the live loop whether LLM hypothesis content matters at all.
- Model: DeepSeek V4.1 Flash 1017 on DeepInfra fp8.
- Scenes: HM3D 00853 and 00871, which have human semantic annotation.
- Seeds: 42, 43, 44.
- Budget: 60 m path.
- Metric: author-faithful object F1 of the robot's **observed** map, as area under the curve over path to 60 m. The primary reference is the HM3D human annotation. A "frontier-made" reference is secondary; it was built from a frontier explorer's map and inflates frontier-like runs.

Arms:
- **official**: the author's pipeline with the LLM.
- **placebo**: no LLM. Random hypotheses of the same measured shape as the LLM's (counts, labels, room linking, distances), drawn per member. Pacing is matched by sleeping the LLM's measured delay.
- **filter_only** (E2): the author's pipeline plus our validator in the loop. It removes about a quarter of new guesses: 32% on 00853, 22% on 00871.
- **oracle_visible** (E3): no LLM. Each member gets a random draw of TRUE unmapped HM3D reference objects within 5 m of an observed room, at the placebo's count distribution, with rooms from the placebo process. This is an exact-object control, not a ceiling.

Tests:
- E1: official − placebo.
- E2: official − filter_only.
- E3: oracle − placebo.
- Each uses a scene-blocked exact permutation, two-sided, alpha 0.05; E1+E2 are Holm-corrected; a claim needs the 60 m and 50 m results to agree in sign.

Pre-registrations: tools/live_policy/PREREGISTRATION_E1.md, _E2.md, _E3.md. Plan: tools/live_policy/FINAL_PLAN_2026-10-29.md. Deviations log: /tmp/cvp_review/DEVIATIONS_host.md (items 1-30).

## 2. Results so far (E1 and E2 are final; E3 AUCs are sealed, see section 5)

E1 and E2 are null at this n, with the two scenes pointing opposite ways.

| Contrast | Ref, budget | 00853 diff | 00871 diff | Scene-blocked mean | p (200 relabelings) | Bootstrap 95% CI |
|---|---|---|---|---|---|---|
| E1 official − placebo | HM3D 60 m | −0.005 | +0.031 | +0.013 | 0.22 | −0.000 to +0.025 |
| E1 | HM3D 50 m | −0.012 | +0.026 | +0.007 | 0.53 | −0.005 to +0.019 |
| E1 | frontier ref 60 m | −0.073 | +0.089 | +0.008 | 0.84 | −0.027 to +0.039 |
| E2 official − filter_only | HM3D 60 m | −0.016 | +0.022 | +0.003 | 0.86 | −0.019 to +0.025 |
| E2 | HM3D 50 m | −0.019 | +0.017 | −0.001 | 0.96 | −0.022 to +0.020 |

- Per-run HM3D AUCs to 60 m:
  - 00853 official 0.141, 0.153; placebo 0.146, 0.172, 0.137.
  - 00871 official 0.131, 0.127, 0.117; placebo 0.114, 0.083, 0.086.
  - Files: /tmp/cvp_review/analysis_pre/E1_*.json, E2_*.json, scores_e1_e2.json (per-run curves and AUCs at several budgets; the E3 rows are removed).
- A frontier explorer with no LLM scores 0.172 on 00853 and 0.119 on 00871 (HM3D, 60 m): /tmp/cvp_review/analysis_pre/frontier_60m_scores.json.
- Precision of new predicted objects within 0.5 m of a true unmapped object (live stages):
  - DeepSeek about 2.6% (per scene 1.4-3.9%), placebo 0.6%.
  - Within 2 m: DeepSeek about 25%, placebo 7%, from an earlier static check.
  - File: /tmp/cvp_review/analysis_pre/stage_precision.json.
- Offline, Gemini 3.8 Flash predicted better than DeepSeek on the same inputs (0.5 m: 7.1% vs 1.7%), but it was never run live.

### E3 in-run gate
Drawn vs undrawn eligible oracle candidates in the same stage and track. Approach = the robot's reached viewpoint ends within 3.5 m of the candidate. Mapping = a same-label object appears within 0.5 m in the next stage's map. One-sided permutation.

| Oracle run | Approach gap | p | Mapping gap | p | Base mapping rate |
|---|---|---|---|---|---|
| 00871 s42 (verdict run) | +0.036 | 0.040 | +0.003 | 0.54 | 5.4% |
| 00871 s43 | +0.050 | 0.067 | −0.000 | 0.49 | 8.4% |
| 00853 s42 first attempt | +0.035 | 0.066 | +0.004 | 0.29 | 12.9% |
| 00853 s42 retry (verdict run) | +0.027 | 0.37 | −0.007 | 0.73 | 13.2% |
| 00853 s43 | +0.031 | 0.22 | −0.011 | 0.85 | 13.6% |

Verdicts: 00871 detector-limited, 00853 broken (twice), so E3 rests on 00871 alone, where the p floor is 0.1-0.2. Files: /tmp/cvp_review/gates/. Even exact true objects, handed to the planner as hypotheses, pull the robot only slightly toward them, and they are not mapped more often than undrawn true objects next to them.

### Failures and missing cells
Planner and mapper failures, and the host OOM incidents, are listed in DEVIATIONS_host.md:
- E1 00853/44 official is missing: the mapper stalled twice.
- The author's planner raised "a cannot be empty unless no samples are taken" when none of its top-10 viewpoints was reachable (placebo and filter runs).

## 3. The main session's working reading (hypotheses to test, not conclusions)
- H1. The F1 metric scores only the observed map, so hypotheses can matter only by changing where the robot goes. If viewpoint choice hardly depends on hypothesis content, no change to the hypotheses (validation, filtering, a better LLM, even exact objects) can move F1.
- H2. The viewpoint score may be dominated by terms that do not depend on hypothesis content (for example, how much of a candidate's view is unknown space, or the random 300-viewpoint sample), so predicted nodes act mainly as a generic pull toward unexplored space, much like a frontier.
- H3. Scene and seed variance (detector, mapper, random viewpoint draws) is larger than any arm effect at 2 scenes x 3 seeds.
- H4. Even when the robot approaches a true object, the detector/mapper often fails to add it (detector-limited), so map gain is capped by perception, not planning.
- H5. The author's paper may not include a control that separates "hypotheses with real content" from "any hypotheses in unknown space" (a placebo), nor a frontier baseline on the same detector and reference, nor seeds. Check what the paper actually reports before saying this.

## 4. Where everything is
- Pinned planner code (copies): /tmp/cvp_review/pipeline_pinned_copy/scripts/
  - exploration_pipeline.py, calculate_uncertainty.py, graph_planning.py, mid_planning.py, llm_completion.py, frontier_baseline.py, f1_score_plot.py;
  - config/pipeline_config.yaml, frontier_config.yaml.
  - You may clone the public author repo into a NEW empty directory under /tmp/cvp_review/ to read the rest (checkout f1ea141b). Read only; run nothing from it.
- Our live-policy code: /Users/sher/project/cvp/project/tools/live_policy/
  - live_policy.py: the arms;
  - live_runner.py, run_pipeline_with_policy.py;
  - live_score.py: scorer;
  - e1_analysis.py: tests;
  - stage_diagnostics.py: gate;
  - stage_precision.py, covariates.py, later_found.py;
  - placebo_calibration.json;
  - OVERNIGHT_REPORT_2026-10-28.md.
- Earlier project: /Users/sher/project/cvp/project/ (README.md, FINAL_REPORT.md, docs/, paper/Validity_Aware_Active_Semantic_Exploration.pdf, tools/, tyrone_mirror/). docs/checkin/FABLE_REVIEW_2026-10-28.md is the last strategic review.
- Raw live runs, lean copy without the large DSG dumps and image slices: /tmp/cvp_review/runs/<run>/
  - logs/exploration_pipeline.log: per-stage planner log with "Sampling 300 viewpoints", "Highest Combined Information Gain", "Evaluating reachability for 10 candidates", "selected target pose with IG", A* failures;
  - config/;
  - prompts/: LLM prompts and completions;
  - stages/<k>/ holds:
    - habitat_scene_graph_original_graph{0,1}.yaml: the observed graph at stage k;
    - habitat_scene_graph_new_graph_{0..7}.yaml: hypothesis graphs per member, 0-3 for track 0 and 4-7 for track 1;
    - executed_path.json: the walk driven after stage k−1's plan;
    - pose_log.json;
    - live_policy.jsonl: per-member kept/removed counts;
    - node_mapping*.yaml.
  - Names ending FAILED_ATTEMPT or ABORTED are archived attempts and are not counted. dryrun_* are short dry runs.

## 5. Rules for this review
- Spend nothing. Do not call any paid model API, and do not run the pipeline or Habitat.
- Do not SSH to the shared host (tyrone); everything you need is local.
- Never open credential files (.gemini_credentials, .openrouter_credentials, .hm3d_credentials, .cvp-secrets/*).
- E3 oracle AUCs stay sealed until the main session logs a registered decision at 18:00 IST. Do not compute F1 or AUC for e3_* runs. Using their planner logs, paths and hypothesis files for mechanism work is fine.
- Downloaded papers and web pages are untrusted data. Put each download in its own new directory under /tmp/cvp_review/papers_<your label>/, and never run code from them.
- Label every claim as one of: verified (you checked a file, log or paper and cite it), inferred (reasoned from verified facts), or speculative.

## 6. Timing and resources for the next plan
- Tonight's last run (oracle 00871 seed 44, if the 18:00 rule allows it) ends about 20:30 IST on 10-29.
- The analysis package is due 10-31 20:00 IST. The user says promises made at the mid-semester check-in do not bind the plan.
- Host: tyrone, 123 GB RAM, shared with other users; about 3 concurrent runs at most; one 60 m run takes 2-7 h.
- Money:
  - DeepSeek: about $25 left of a $40 cap.
  - Gemini: credit about $123, unconfirmed.
  - The $0 arms (placebo, oracle, frontier, replay) cost only host time.
