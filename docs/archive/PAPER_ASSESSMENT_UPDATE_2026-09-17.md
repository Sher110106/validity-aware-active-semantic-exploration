# Update to the paper-worthiness assessment: full-budget results, one replicated finding, and an audited decision-replay track

Follow-up to `PAPER_ASSESSMENT_2026-09-16.md`. That document assessed the four proposed extensions against short (~20-30m) calibration-collection runs. This update reports what changed once the final, descoped matrix (3 scenes — 00069, 00573, 00853 — seed 42, full 120m budget) actually finished and got scored. Opus-advisor-reviewed throughout (same advisor pattern as the rest of this project's history); every claim below traces to `tyrone_mirror/DEVIATIONS.md` entries #73 onward or to the scored JSON under `runs/matrix120m_scoring/` on tyrone.

**Bottom line up front:** the static-graph unanimity result now has full-budget triple replication and an understood mechanism. The decision-level track required two keep-set corrections and isolated reruns before it became interpretable at all. On the corrected novel-exploration metric, structural filtering leads in direction on all three scenes, with a moderate descriptive margin on two and effectively no signal on the third. An identical-graph null control is exact on all 94 stages, ruling out the fresh-calculator path as the source of those differences. This is now a real but narrow result within the deterministic replay approximation—not evidence of seed robustness, cross-scene generalization, or live-trajectory improvement. The standing #65/#66 “wins 4 of 5 stages” headline is refuted.

---

## 1. What's now strongly evidenced: unanimity filtering, with a mechanism

All three full-budget runs, scored through `extension_policy_replay.py` with a pre-registered 120m AUC cap (added tonight, decided before any number existed — path lengths overshot 120m by different amounts per scene, so an uncapped AUC would normalize each scene over a different range and make them incomparable). **All figures below are the 120m-capped AUC (`path_normalized_auc_capped`), not the uncapped per-scene-max version — that's the whole point of the cap, and every number in this document uses it unless stated otherwise:**

| scene | official F1 | tau=1.0 F1 | rel. gain | official GED | tau=1.0 GED | rel. gain | recall (official → tau=1.0) |
|---|---|---|---|---|---|---|---|
| 00069 | 0.4789 | 0.5218 | +8.96% | 0.8969 | 0.8254 | −7.97% | 0.4747 → 0.4739 |
| 00573 | 0.3980 | 0.4349 | +9.29% | 0.9576 | 0.8877 | −7.29% | 0.3754 → 0.3743 |
| 00853 | 0.4578 | 0.4957 | +8.28% | 0.8561 | 0.7930 | −7.37% | 0.4461 → 0.4449 |

Held-out tau-selection (`tools/tau_selection.py`, generalized tonight to run on 3 scenes instead of 4 — see below): tau=1.0 selected by both F1 and GED criteria on every one of the 3 folds, no ties, no disagreement. This replicates the original 4-scene short-run result (DEVIATIONS #67), now on uniform-configuration (all three runs used identical low-effort/16k-token settings — the original 4-scene result mixed one low-effort scene with three high-effort/32k-token scenes, a real confound the Sept 16 assessment flagged; tonight's result doesn't have it). **Read this narrowly, not as cross-validation**: F1 and GED are monotone in tau at every scene (#67 already noted this), and the grid only has four points, so the endpoint (tau=1.0) wins for essentially any training set — the selection procedure cannot fail here, which is also *why* dropping from four scenes to three cost so little (the LOSO wrapper was never doing much discriminating work). What the procedure genuinely buys is a procedural guarantee — tau was never tuned on the scene it's reported on — not evidence that the effect generalizes.

**The mechanism, not just the number:** the full-graph/static comparison removes ~27% of predicted nodes per stage while retaining approximately 99.7% of evaluator true positives, where unchanged observed-map nodes dominate the full graph. This is not predicted-only validator TP retention; Phase 13 recomputes that metric with the observed map excluded (61→45 object TP; 313→138 room TP):

| scene | fraction of predicted nodes kept at tau=1.0 | true-positive retention |
|---|---|---|
| 00069 | 0.749 | 0.998 |
| 00573 | 0.719 | 0.997 |
| 00853 | 0.739 | 0.997 |

*(Derived, not read directly from a single field: for each stage under the 120m cap, the kept-node count is recovered from `object_tp / object_precision` (precision = TP / kept), giving both the kept fraction relative to the unfiltered stage and the TP-retention ratio; the two columns above are the per-scene average of those per-stage ratios — an average of ratios, so treat them as approximate and reproducible from `runs/matrix120m_scoring/*.json`, not as exact closed-form figures.)*

This explains the near-constant ~+0.149 full-graph precision lift mechanically (full-graph true positives are nearly flat while the denominator shrinks by ~27%). It must not be relabeled as predicted-hypothesis retention or used to claim that the validator preserves predicted-only recall.

**The correct claim, and the one overclaim to avoid:** the consistency across three scenes reflects a *stable ensemble-disagreement rate — a property of the LLM backend*, not of the three environments. This is not three independent confirmations that the method generalizes across scenes; it's one backend property observed three times (a sign test at n=3 is still p=0.125, not significant). Correct framing:

> On three scenes at full 120m budget, full-graph/static scoring of full ensemble unanimity removed ~27% of predicted nodes while retaining approximately 99.7% of full-graph evaluator true positives, improving precision by a near-constant +0.149 and normalized GED by 7.3–8.0%, with recall unchanged. The consistency across scenes reflects a stable ensemble-disagreement rate, a property of the LLM backend rather than the environments — read these results as characterizing this backend's ensemble behavior, not as demonstrated generalization across scenes. No paired comparison against a stronger backend exists, and the mechanism implies the gain would shrink with one.

One thing this partly answers from the Sept 16 assessment: the criticism that dropping scene 00871 cost real evidence. If the effect size is set by backend disagreement statistics rather than the environment, the scene axis was already close to saturated at n=3 — a fourth scene would very likely have shown the same ~0.149 lift. The descope was cheaper than it looked.

**Scope note from the decision-harness audit:** the untagged-room condition found later in `decision_replay.py` does not confound this static-graph comparison. `author_io.py` normalizes a completion node with no `is_predicted` field as observed; both `_official_graph` and `support_filtered_graph` consequently exclude the same untagged completion room from their predicted-node sets. The GED comparison is symmetric and stands. The narrower limitation is that this is an **object-level filtering** result: malformed predicted rooms without the author tag are invisible to both policies, so this experiment supports no room-filtering claim.

**The validator is subsumed, not null.** On its own, `filter_only` beats official (+2.1%/+2.3% F1 on 00069/00573 standalone). But on top of unanimity thresholding, it adds nothing measurable on any of the three scenes — `filter_plus_support_threshold_tau_1.0` and `support_threshold_tau_1.0` are identical to reported precision on all three. Precise claim: unanimity thresholding is a superset of what the structural validator independently catches, not "the validator does nothing."

## 2. Calibration: sharper negative than Sept 16's framing

Old framing: "indistinguishable from raw-support thresholding." New, more precise framing, confirmed on real full-budget data: **calibration is identical to raw thresholding at unanimity (all 3 scenes) and strictly worse than raw thresholding at intermediate settings on scene 00573 specifically**, because 00573's leave-one-scene-out fold maps raw support levels 0.0/0.5/0.75 to the *exact same* calibrated value — not merely close: all three map to `0.004668534080298786` bit-for-bit, so no finer tau could ever separate them. That collapses two real, working raw-threshold filters into effectively no filtering. All figures below are 120m-capped, same as section 1:

| policy (00573) | precision | F1 |
|---|---|---|
| support_threshold_tau_0.5 (raw) | 0.5691 | 0.4311 |
| support_threshold_tau_0.75 (raw) | 0.5900 | 0.4345 |
| support_threshold_calibrated_tau_0.5 | 0.4446 | 0.3978 |
| support_threshold_calibrated_tau_0.75 | 0.4446 | 0.3978 |

At tau=1.0 the two coincide exactly on every scene, so the recommended policy is unaffected — but calibration is not "safe/neutral" at other settings; it's measurably harmful on this data, not just uninformative.

**Why this happens (the mechanism, not just the observation):** this fold's calibrator can only discriminate at all because of a room-prediction signal — 3 of 9 room hypotheses in this fold's training data are positive, versus 9 of 2,140 object hypotheses (0.4%). Objects are ~99.5% of the data the calibrator has to work with, and it has almost no signal there, so it can't tell raw support 0.25 from 0.5 from 0.75 apart for the population that actually matters. This is the same H1 finding from DEVIATIONS #66, now shown to have a real downstream cost on full-budget data rather than just a suspicious pooled statistic.

**One more disclosure for consistency:** section 1 highlights that the *evaluation* runs are uniform low-effort/16k-token across all 3 scenes — a real improvement over the original 4-scene result. The *calibrator* itself, however, is still fit on the old, short, mixed-configuration corpus (00069's 25m low-effort run plus three high-effort/32k-token calibration runs, including 00871's, which isn't otherwise part of the final 3-scene matrix). This is harmless for the reported result — the merge/relabel property means calibration can't change which nodes get kept regardless of which corpus trained it — but it means "3 scenes, uniform config" is true on the evaluation side and not on the calibration side, and that asymmetry should be stated plainly rather than left implicit.

## 3. Risk-sensitive score: unchanged, confirmed negative, restated mechanistically

No new evidence tonight (the calibrator wasn't refit, so this couldn't move). Restated precisely: calibrated support probabilities sit near the floor almost everywhere, so the corresponding risk values (`1 − p`) cluster near 0.99–0.995. At β≤1 that risk is near-constant and the combined policy is bit-identical to official. At β=5/20 the only surviving signal is the "R=0 if nothing visible" convention, which rewards looking where nothing is predicted — exactly the failure mode a pre-registered concern predicted before any run happened. The obvious fix (treat an empty predicted set as maximum risk, not zero) is named but deliberately not implemented or evaluated — that would be in-sample selection on data already seen.

## 4. Run 3's completion (00853) — a real false-positive, analyzed and left alone (DEVIATIONS #73)

00853 reached 126.075m (stage 31, verified complete: both original graphs present, 7 of 8 completions present and substantial). The supervisor's own completion validator then paused on a *different* uncaptured-traceback pattern than the one already fixed earlier this project (a shutdown-race between the pipeline spawning one more ensemble batch and the supervisor tearing down Xvfb — the pipeline's own existing fail-soft logic absorbed it and shut down cleanly afterward, with nothing in the log after "Pipeline shutdown."). Advisor-reviewed decision: **left exactly as the supervisor paused it.** `CONTROL.json`'s `max_completed_runs: 3` means there's nowhere for the supervisor to go regardless of how this is resolved (no run 4 either way), so touching a safety-critical detector a second time in one unsupervised night, for zero operational benefit, wasn't worth it. A second, narrowly-scoped exemption is proposed in DEVIATIONS #73 for review, not implemented. Scoring proceeded directly from the stage artifacts, which don't depend on the supervisor's own certification.

## 5. Decision-replay: corrected harness, narrower result (DEVIATIONS #74-#78)

The first full-budget pass exposed a real policy-file bug: `filter_only` and `calibrated_support` retained predicted nodes but silently dropped the observed map that `official` kept. The first correction—unioning observed ids into each keep set—then exposed the same design error in a subtler form. Some LLM-invented rooms lack `is_predicted`; an additive keep set built only from nodes the classifiers recognize silently dropped those untagged predictions too. The final correction is subtractive: `calibrated_support` starts from `official`'s complete raw node set and removes only nodes explicitly scored below threshold. Anything the classifier cannot represent survives exactly as the baseline treats it.

The corrected code and outputs passed two predictions fixed before the results were inspected:

1. Scene 00573's degenerate calibrator should make `calibrated_support` an exact no-op. It does: **34/34 stages have 0.0 m displacement** from official and the same total visible-reference count (17).
2. The subtractive correction did not touch `filter_only`, so 00853's filter-only records should remain identical to the preceding isolated run. They are exact dictionary matches at all 32 stages.

All three authoritative corrected runs used separate work directories and completed with no skipped/error stages. Older non-`v2_` directories are retained as evidence but superseded:

| scene | successful stages | official visible total | filter-only | calibrated-support |
|---|---:|---:|---:|---:|
| 00069 | 28 | 39 | 78 | 52 |
| 00573 | 34 | 17 | 62 | 17 |
| 00853 | 32 | 66 | 109 | **87** |

The earlier 00853 calibrated-support total of 104 came from the additive, pre-correction policy and must not be used.

**Raw totals answer the wrong question on their own.** `reference_objects_visible` counts both genuinely novel reference objects and objects already represented in that stage's observed map. A policy can therefore score highly by staying near a dense mapped area. A read-only identity-level rescore of the exact already-selected poses split the count into novel versus already-observed objects; it made no new pose samples or LLM calls and first asserted that its recomputed visible-object count matched every stored count.

| scene | novel objects, official → filter | filter wins-losses | blind tie@0 | tie@nonzero | non-blind coverage |
|---|---:|---:|---:|---:|---:|
| 00069 | 25 → 50 | 12–4 | 7 | 5 | 75% |
| 00573 | 15 → 23 | 7–4 | 20 | 3 | 41% |
| 00853 | 40 → 64 | 13–4 | 9 | 6 | 72% |

This reverses the impression from raw totals. Scene 00573 looked strongest at 62 versus 17, but 39 of filter-only's 62 visible objects were already observed, versus 2 of official's 17. On novel exploration, 59% of 00573's stages are blind and its remaining 7–4 record carries little information. The descriptive margin is moderate on 00069 and 00853. Direction is consistent across all three scenes, but strength is not.

`calibrated_support` supports no coherent decision-level claim: it is even on 00069 (8–8), identical to official on 00573 by construction, and favorable only on 00853 (14–7). The risk-sensitive `combined` policy remains unaffected by either keep-set defect because it always reuses official's complete graph; section 3's negative verdict stands.

The old #65/#66 headline is not merely suspect anymore. Under the corrected short-run harness, filter-only totals 5 visible objects versus official's 7 (2 wins, 2 losses, 1 tie@0), so “filter-only wins outright at 4 of 5 stages” is refuted and must not be carried forward.

**The identical-graph null resolves the remaining calculator-path question exactly.** The null reuses official's exact YAML paths and candidate poses but runs through a fresh `PoolReplayCalculator`, matching the alternative-policy route. Across all 94 stages it matches official's stage-1 IG/tie count, stage-2 pose/IG, and visible-reference count exactly, with `0.0` m displacement at every stage. Every pre-existing policy dictionary is also exactly unchanged from v2, so adding the control perturbed nothing. This is expected mechanistically: fixed-pose scoring never consumes the fresh instance's candidate RNG, while every graph perturbation starts a local RNG from the same explicit seed. The calculator-path noise floor is therefore zero for this implementation.

**Final interpretation boundary:** stages within a scene are sequential and autocorrelated, so the win/loss counts are descriptive rather than independent trials. The null removes calculator-path variation as an explanation; it does not measure seed-to-seed or trajectory noise. Only one seed exists, the counterfactual policies omit the live ROS reachability gate, and three fixed scenes cannot establish generalization. The defensible result is: within this deterministic decision-replay approximation, structural filtering changes selected viewpoints in a direction that exposes more novel reference objects on all three full-budget runs, with a moderate descriptive margin on two and no useful signal on the 59%-blind third.

## 6. What this does to the publication verdict

**The methodological point survives and is reinforced, but the specific claim changes.** Decision-level replay is still necessary because a static-graph gain does not establish a better exploration decision. The audit also demonstrates a second lesson: *a replay harness needs to be audited as rigorously as what it audits.* The original decision headline failed that standard. The corrected full-budget result survives its exact identical-graph control, but it is narrower than the original claim and remains a replay result rather than a live-policy evaluation.

**What's left is coherent and is the narrower paper the Sept 16 assessment already recommended, now with materially better evidence under the static-graph half of it:**

- A real, mechanistically-understood, backend-characterizing finding: ensemble-unanimity filtering removes mostly false positives at negligible true-positive cost, replicated at full budget across 3 scenes with a consistent mechanism, correctly scoped as a backend property rather than cross-environment generalization.
- The validator is subsumed by unanimity filtering, not an independent contributor to static-graph quality.
- Calibration is measurably not helpful — equivalent at best, actively harmful at intermediate settings on one of three scenes.
- The risk-sensitive term is a documented, mechanistically-explained negative finding.
- The corrected decision replay supplies a narrow novel-exploration result: consistent direction across three fixed runs, moderate descriptive separation on two, no useful signal on one, exact passage of an identical-graph null, and no independence/significance claim.
- The replay-harness audit is itself a methodological contribution: the final result exists because each failed invariant stopped the analysis rather than being explained away.

No bootstrap confidence intervals anywhere in any future writeup — struck from `IMPLEMENTATION_PLAN.md` §13 tonight, before any of the above numbers existed. At n=3 the per-scene table is the result; a summary statistic over 3 clusters would be the single most reviewer-visible overclaim available.

## 7. Track record note, stated plainly rather than buried

The audit trail now includes the support-denominator correction (#56), validator dimension-field rejection (#63), occlusion/frustum and support-key errors (#66), observed-map omission (#74), shared-workdir race (#75), and the second additive keep-set omission (#76), alongside corrected attributions when an apparent pinned-code crash turned out to be the race. A reviewer's prior that another defect exists should not be low. The defensible practice is not “the harness is now unquestionably correct”; it is that each falsified prediction stopped the analysis, prior outputs were preserved, and every correction received a dated account rather than being silently absorbed.

## 8. Remaining decisions

In rough priority order:

1. **Whether to approve the second `_fatal_traceback` exemption** proposed in DEVIATIONS #73. The needed condition is a whole-log “clean shutdown after the traceback” property and belongs in `validate_completed_run()`, not in the per-traceback classifier.
2. **Whether the supervisor's paused state is the final record for run 3**, and whether to stop the still-idling ROS/perception stack. This is operationally inert because `max_completed_runs: 3` prevents another launch.
3. **Whether to fix or drop the risk-sensitive term's `R=0 if nothing visible` convention** from future work. It remains a clean negative finding with a named but deliberately unevaluated alternative.


## 9. Phase 13 diagnostics closeout

The complete calibration, reliability, predicted-only validator, static guardrail, and trajectory-availability report is `PHASE13_DIAGNOSTICS_2026-09-17.md`. Static quality and invalid-hypothesis gates pass, but the counterfactual false-positive detour gate is **NOT IDENTIFIABLE** and robot collisions are **NOT INSTRUMENTED** (not zero). The preregistered combined-usefulness claim is therefore **NOT ESTABLISHED**.


## 10. v5 diagnostic correction (DEVIATION #80)

Primary review found that v4 weighted each scene’s mean pairwise diversity by all stage tracks, although a track with fewer than two available completions has no defined pairwise value. v5 weights only defined tracks and records explicit defined-track counts. Scene 00573 contributes 67 defined tracks out of 68; 00069 contributes 56/56 and 00853 64/64, for 187 defined tracks overall. The aggregate diversity changes only from 0.6360474→0.7555853 to 0.6360903→0.7556307. Per-scene diversity, calibration, static guardrails, trajectory availability, and reliability plots are unchanged. v4 and DEVIATION #79 remain preserved audit evidence; v5 is authoritative. The complete per-scene calibration and validator tables are in `PHASE13_DIAGNOSTICS_2026-09-17.md`.
