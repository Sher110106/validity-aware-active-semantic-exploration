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

---

## Appendix: the 16 Sept assessment

Merged on 2026-11-12 from `PAPER_ASSESSMENT_2026-09-16.md`, which is removed from the tree and remains in git history. This update (above) says it follows that document. The text below is the 16 Sept assessment as it stood after its 9 Oct correction (DEVIATIONS #93, kept inline in item 6 of "What a paper reviewer would immediately flag"). Its headings are moved down two levels. It was written against the short (about 20-30 m) calibration runs and is superseded by the full-budget results above.

### Assessment: Publication Potential of the ASP Replication's Four Extensions

Scope note: this reads `IMPLEMENTATION_RESEARCH.md`, `IMPLEMENTATION_PLAN.md`, `REVIEW_2026-09-14.md`, `SESSION_REPORT_2026-09-13.md`, the actual code in `tools/asp_offline/{validator,calibration,scoring,support_policy,models,evaluator}.py`, `tools/extension_policy_replay.py`, `tools/decision_replay.py`, `tools/tau_selection.py`, and `tyrone_mirror/DEVIATIONS.md` entries #50, #56, #57–59, #61–62, #63–64, #65, #66, #67 (and, for context on what remains open, #68–72). All entries and code cited below were read in full, not summarized secondhand.

Prepared 2026-09-16 by a Sonnet subagent, reviewed and relayed in this session.

---

#### 1. The four contributions, restated from the code

**1. Whole-graph structural validator** (`tools/asp_offline/validator.py`, `validate_completion`/`validate_ensemble`). A deterministic, ground-truth-free filter run on each of the LLM's 4-per-track sampled completions: schema/parseability checks, unique-ID checks, object→room parent checks, room containment, AABB overlap against observed/predicted blockers, and impassable-structure-crossing checks. Invalid predicted nodes are dropped with a logged reason; a completion that would drop an observed node is rejected outright; if every completion in an ensemble fails, it falls back to the observed graph plus a geometric frontier candidate list (`_geometric_frontier_candidates`) rather than halting. A unit test (`test_validator_functions_never_take_a_reference_graph`, described in `SESSION_REPORT_2026-09-13.md` §3.4) enforces via `inspect.signature` that the online decision path never receives a reference graph — genuinely a fail-soft, ground-truth-blind filter, not a filter that peeks at the answer.

**2. Leave-one-scene-out calibration of ensemble support** (`tools/asp_offline/calibration.py`: `IsotonicCalibrator`, `fit_leave_one_scene_out`; `tools/asp_offline/support_policy.py`: `fit_loso_calibrator`). Raw support `s = hits/4` (per scene-track ensemble of 4, not the paper's pooled "8" — DEVIATIONS #56) is mapped through a pooled-least-squares isotonic (PAVA) fit trained on the other three scenes' hypotheses, evaluated on the held-out scene. This is a real, working calibrator with two bugs found and fixed in the audit trail (a tied-x PAVA bug, DEVIATIONS #61; and a label-matching units bug that would have zeroed every label, avoided rather than shipped, same entry).

**3. Risk-sensitive viewpoint score** (`tools/asp_offline/scoring.py`: `score_viewpoint`, implementing `U(x)=I_object+λ_room·I_room−λ_d·d−β·R(x)`). `R(x)` is the mean of `(1 − calibrated_support)` over predicted nodes visible from a candidate pose, zero if none are visible. In `score_viewpoint` itself this is a pure, tested arithmetic function; it is only exercised as an actual re-ranking of real candidate viewpoints in `decision_replay.py`'s "combined" policy.

**4. Decision-replay methodology** (`tools/decision_replay.py`). Reuses the pinned `UncertaintyCalculator` class unmodified, draws one shared candidate pool under the official policy, and re-scores that same pool under filter-only, calibrated-support (β=0), and combined (β>0, unfiltered graph, risk-reweighted) policies — asking whether the *selected viewpoint* changes and whether it sees more real reference-graph content, not whether a static filtered graph scores better. It reproduces the live pipeline's own logged decision character-for-character (`gate_check.py`, cited in DEVIATIONS #65) before trusting any counterfactual comparison, and explicitly does not replay the live ROS reachability gate (applied "no reachability gate" uniformly across all four policies instead of special-casing the one with a real log).

---

#### 2. Evidence strength, per contribution

##### Contribution 1 — Validator

**Cross-scene, but as a static filter, not a decision-changer.** The filter-only policy was scored via `extension_policy_replay.py` on all 4 scenes (00069, 00573, 00853, 00871 — DEVIATIONS #64, #66). Its own history is a caution against taking it at face value: a real bug (`finite_geometry` silently rejecting every predicted room because rooms never carry a `dimension` field in this pipeline's wire format — DEVIATIONS #63) meant every `filter_only` number reported earlier in the project (in #50, #56, #60, #62, and both narrative reports) was wrong, computed against a validator that was effectively "delete all predicted rooms and everything inside them," not a real structural check. After the fix, node survival went from 16% to 63% on a real stage (DEVIATIONS #63), and the earlier apparently strong filter-only precision was disclosed as **survivorship bias** — the few nodes that had survived the broken check were disproportionately the easy, correct ones (DEVIATIONS #64). Post-fix, filter-only still beats official on precision at every scene (e.g., 00069: 0.490→0.526; 00573: → 0.374; 00853: → 0.474; 00871: → 0.584 — DEVIATIONS #64) with recall essentially unchanged. In the decision-replay track (single scene, 00069 only), filter-only is the one policy that survives the later occlusion-bug correction: it wins outright at 4 of 5 stages on real reference-object visibility (DEVIATIONS #66's corrected table). That is a real, if narrow, piece of decision-level evidence — but it is n=1 scene, 5 stages, no seeds.

**Verdict:** real and cross-scene as a static-graph filter; genuinely decision-relevant only on one scene's 5 checkpoints. Its own reported strength was inflated once by a bug and is now the smaller, corrected, still-positive number.

##### Contribution 2 — LOSO calibration

**Real fit, weak and uneven signal, disclosed rather than dressed up.** The fit is real: 2,829 hypotheses across all 4 scenes, only 23 positives overall (0.81% positive rate — DEVIATIONS #61), traced to a concrete, understood cause (70% of predicted labels share no vocabulary at all with the reference detector's category set — the already-disclosed unpublished-61-category gap, DEVIATIONS #51, #61). Every fold is genuinely monotone (not degenerate), but generalization is uneven: 00853 and 00871 hold out reasonably; **00573's fold could not distinguish raw support 0.25/0.5/0.75 from each other at all** — its training data (the other three scenes) showed no discriminative signal in that range, so PAVA merged all three levels into one calibrated value (DEVIATIONS #62). The audit further found (H1, DEVIATIONS #66) that the pooled fit's flagship "45–56% chance correct at unanimity" number is **entirely a room-prediction signal** (33–57% positive on 9–14 samples per fold) — object predictions, the vast majority of the data (1,769–2,420 samples per fold), sit at 0.4–0.6% positive with essentially no signal. The filter itself still uses the pooled (room+object) calibrator, so this is a real interpretive gap between what the calibrator is *reported* to mean and what it can actually discriminate for the object population that dominates the data.

A second, structurally important fact: because raw support under K=4 only takes 5 discrete values, a monotone calibrator can only relabel or merge those levels, never reorder them (proven in a unit test and verified on real data — 3 of 4 scenes' folds keep all 4 levels distinct; 00573's fold merges three of them — DEVIATIONS #62). This means **calibration, in the data collected so far, does not change which nodes get kept relative to the equivalent raw-support threshold** — it only attaches a probability interpretation to an existing threshold. That is a legitimate and useful thing (interpretability, a principled acceptance threshold instead of an arbitrary one), but it is not evidence that calibration *improves* filtering beyond what raw-support thresholding already does.

**Verdict:** the calibration machinery is real, correctly leave-one-scene-out, and honestly reports its own weak spots (a rare thing to see disclosed this cleanly). But the underlying signal is thin (23 positives total), driven almost entirely by rooms, and — on the data gathered so far — provably equivalent to raw-support thresholding rather than a demonstrated improvement over it.

##### Contribution 3 — Risk-sensitive score

**This is the contribution with the weakest support, and the evidence available argues against it as currently specified, not for it.** It is exercised only inside `decision_replay.py`, on one scene (00069), across 5 stages, at β ∈ {0, 1, 5, 20}. At β≤1 the risk term is near-constant (R(x)≈0.99–0.995, because the calibrator's probabilities sit near the floor almost everywhere), so `combined` is bit-identical to `official` — zero displacement, zero effect (DEVIATIONS #65). At β=5 or 20 the term dominates and jumps the selection 8–10 m away, but does **not** consistently see more real content — worse than official at some stages, tied at others (DEVIATIONS #65). This is exactly the failure mode an Opus advisor flagged *before any run happened*: "the '0 if none visible' convention rewards looking where nothing is predicted" (DEVIATIONS #65, reaffirmed in #66's H4 note). This is not a case of insufficient data; it is a real, replicated demonstration of a design flaw in the risk term as specified in `IMPLEMENTATION_RESEARCH.md` §4.3.

**Verdict:** not validated. The one test that exists is single-scene and shows the term either doing nothing or doing something counterproductive. Nothing in the record supports publishing this piece as a positive result.

##### Contribution 4 — Decision-replay methodology

This is where the project's strongest evidence lives, but the "evidence" is about the *method*, not about a settled conclusion the method produced. Two runs of the same harness on the same scene produced opposite headlines: the first (DEVIATIONS #65) reported filter-only and calibrated-support both beating official at 4 of 5 stages, driven by a `score_pose_against_reference` function that used frustum culling only, never occlusion. Once that bug was found and fixed (H3, DEVIATIONS #66), the result **reversed at stage 0** (official: 5 real objects visible; both alternatives: 0) and calibrated-support's advantage "mostly evaporates," tying official at 0 in 3 of 5 stages. Filter-only is the only policy whose advantage survives the fix. The methodology's own self-correction — catching that a static-graph improvement (contribution 1/2's precision gains) does not automatically mean the *selected viewpoint* improves, and that a decision-level metric itself can be silently wrong (frustum vs. occlusion) — is a genuinely valuable demonstration, arguably more valuable than any single number it produced. But as evidence for the extensions themselves it is: one scene, 5 stages, an explicitly labeled "approximation" (no live ROS reachability gate — M9 in DEVIATIONS #70 confirms false-positive detours, collisions, and path length are simply not measurable this way), and a track record of reversing its own conclusion once already.

**Verdict:** the methodology is sound and its self-correction is the most credible thing in the whole project. As a validated finding about the extensions, it currently supports only "filter-only shows a real, single-scene decision-level effect"; it does not support the calibration or risk-term contributions, and it cannot speak to trajectory-level outcomes (path length, collisions, false-positive detours) at all.

##### The one genuinely strong cross-scene quantitative result

Easy to miss under the other caveats: DEVIATIONS **#67** closes the review's own held-out tau-selection prescription properly. Held out one scene at a time, using only the other three scenes' curves, both the F1-maximizing and GED-minimizing criteria independently select **τ=1.0 (full 4/4 ensemble unanimity) in every one of the 4 folds, with zero disagreement between the two criteria.** Applied honestly to each held-out scene: F1 improves +9.7% to +13.7% relative and GED improves −6.7% to −7.0% relative to official, on every scene, with recall essentially flat (a threshold filter can only remove nodes, so the entire gain is precision/GED — this is disclosed in the same entry, not something to read as a free win on every axis). This is real cross-scene, held-out, non-circular evidence — the single best piece of quantitative support the project has. Its caveats: it is a static-graph metric, not decision-level; the underlying runs used to build the per-scene AUC curves are the short (~20–30 m) calibration-data-collection runs, not full-budget matrix runs; and the 4-point tau grid landing on an endpoint is, as the entry itself says, not that surprising in retrospect.

---

#### 3. What a paper reviewer would immediately flag

1. **Substitute LLM backend is a capability-tier change, not a version bump.** DeepSeek V4.1 Flash via OpenRouter replaced the paper's Gemini 2.5 Pro after the pinned model was deprecated (IMPLEMENTATION_PLAN.md §0; SESSION_REPORT §2.1, §6). The project's own framing is explicit and correct about this ("a reimplementation of ASP's method with a substitute backend... should not claim to reproduce ASP's own published numbers" — IMPLEMENTATION_PLAN.md §0). No paired same-input head-to-head between the two models exists (REVIEW_2026-09-14.md's "Model comparison" section states this plainly). A reviewer would ask, correctly, whether any of the four extensions' effects are an artifact of a weaker model producing noisier, less-agreeing completions that a filter then has an easier time cleaning up.

2. **Scope was descoped twice, in the direction of less evidence, both times disclosed.** The original 4-scenes × 3-seeds (12 runs) design is now 3 scenes × 1 seed (3 runs), for cost (~$240 projected) and time (IMPLEMENTATION_PLAN.md §0, dated today). No seed repeat means no variance estimate at all — the project cannot distinguish a real policy effect from seed noise anywhere in the final matrix. Dropping scene 00871 leaves one held-out (val-split) scene against two train-split scenes, unbalancing the original 2/2 split. Both costs are named plainly in the plan rather than absorbed silently, which helps credibility but does not remove the problem.

3. **The calibration signal is thin and uneven, and the headline positive-rate number pools two populations with wildly different behavior.** 23 positives across 2,829 hypotheses (DEVIATIONS #61); one of four folds (00573) cannot even order three of five support levels (DEVIATIONS #62); the "45–56% correct at unanimity" number is a room-only effect misreported as if it applied to objects too, until caught in audit (DEVIATIONS #66, H1).

4. **The risk-sensitive term has a demonstrated, not hypothesized, failure mode**, predicted by an advisor before any code ran and then observed exactly as predicted (DEVIATIONS #65). A reviewer would read this correctly as "this piece of the proposal doesn't work as specified," not as an open question.

5. **Decision-replay is explicitly an approximation that never touches the live ROS reachability gate**, and it already reversed its own headline once due to a visibility-scoring bug (frustum-only vs. real occlusion, DEVIATIONS #66). A reviewer would treat any surviving decision-level claim ("filter-only wins 4/5 stages") as fragile until it, too, survives independent re-scrutiny — the project's own track record on this exact question is 1-for-2.

6. **Ground truth is self-generated, not paper-sourced**, via an automated frontier-exploration policy standing in for the paper's human-piloted exhaustive coverage (IMPLEMENTATION_PLAN.md §0, DEVIATIONS #51). The direction of bias this introduces was reasoned through, not measured, and the paper's own unpublished 61-category F1 restriction could not be recovered despite an exhaustive search (DEVIATIONS #51) **[Corrected 2026-10-09, DEVIATIONS #93: the list is in the author repo, `task_def/objects_habitat_apartment_00573.yaml` (61 labels = the detector's 52 + 9). It barely affects our scores, since every reference label is already on the 52 list.]** — so absolute numbers are not comparable to the paper's Fig. 4 at all, and the project has repeatedly said so (SESSION_REPORT §11).

7. **GED numbers used for any paper comparison are a best-found upper bound from an anytime search, not a certified-exact minimum** — confirmed directly by running `nx.optimize_graph_edit_distance` and watching it plateau at value=163 after 0.36s with zero further improvement over 70+ seconds (DEVIATIONS #68). This is disclosed but is exactly the kind of thing a numerically careful reviewer checks, and, if not caught in advance, would flag as a serious gap.

8. **The final, descoped 3-scene × 1-seed × 120 m matrix has not itself been scored yet.** As of today's plan (IMPLEMENTATION_PLAN.md §0, "Not started: Phase 13's final evaluation, and scoring the 3 completed matrix runs"), the strongest cross-scene evidence (the #67 tau-selection result) is built on short, bounded (~20–30 m) calibration-collection runs, not the eventual full-budget matrix. Whether the effect holds at 120 m, with more hypotheses and (presumably) more high-support agreement, is genuinely unknown.

9. **A track record of self-correction is a fact a reviewer will weigh both ways.** It is a real strength (the project visibly does not let a flattering wrong number stand — three separate instances: the support denominator, the validator dimension bug, the occlusion-vs-frustum bug, each corrected in place with the old numbers struck through, not deleted). It is also a real weakness, because it means every number in this project has already been wrong once, and a reviewer's prior on "is there a fourth bug we haven't found yet" should not be low.

---

#### 4. Honest publication verdict

**Not yet publishable as a full paper. Marginal, honestly-scoped workshop material at best, and only after two specific gaps close.**

The case for "not yet, full-paper":
- Contribution 3 (risk-sensitive score) currently has negative-leaning evidence, not just insufficient evidence. It cannot be claimed as a contribution in its current form.
- Contribution 2 (calibration) is real but its practical effect — on the data gathered so far — is provably indistinguishable from raw-support thresholding (the relabel/merge property, DEVIATIONS #62). A paper claiming "calibrated support improves exploration" would be claiming something the project's own code disproves for the current dataset.
- Contribution 4's one clean decision-level finding (filter-only wins on reference-object visibility) is single-scene, 5 checkpoints, no seeds, and has already reversed once under its own correction.
- The final evaluation matrix — the thing the whole plan built toward — has not been scored yet, and what will be scored is 3 scenes × 1 seed with no variance estimate.

The case for genuine, publishable content existing somewhere in this work:
- The tau-selection result (#67) is real, held-out, non-circular, and consistent across all 4 scenes with two independent criteria agreeing every time. That is a legitimate, if narrow, empirical finding: unanimity-filtering of a small LLM ensemble improves precision and GED without hurting recall, on this backend, at this scale.
- The decision-replay *methodology* — reusing the pinned uncertainty calculator unmodified, sharing one candidate pool across policies, and catching that a static-graph win does not imply a decision-level win (twice: the merge/relabel property, and the frustum/occlusion reversal) — is a real methodological contribution independent of whether the specific extensions pan out. It is arguably the most defensible, most novel thing in the repository.

**Minimum additional work that would change this verdict**, in priority order:
1. Score the completed 3-scene × 1-seed × 120 m matrix through `extension_policy_replay.py` and, ideally, `decision_replay.py` for all three scenes, not just 00069. This is already planned (IMPLEMENTATION_PLAN.md §16, unchecked item) and is the single highest-value next step — it tests whether the #67 tau=1.0 result and the filter-only decision-level effect survive at full budget and across more than one scene's decision replay.
2. Either fix the risk-sensitive term's "0 if none visible" convention (the advisor's own critique names the mechanism to fix) or drop contribution 3 from the paper's claims entirely and report it as a documented negative result — the current data supports the latter, not silence.
3. Report the calibration result honestly as "a probability re-expression of raw-support thresholding, not shown to outperform it" rather than as an independent win, unless a genuinely discriminating dataset (more high-support positives, likely needing the full 120 m budget across more scenes) changes that.
4. If time/cost allow even one seed repeat on one scene, that would go a long way toward answering the "is this seed noise" question a reviewer will ask about every headline number.

None of this requires the originally-planned full 12-run matrix. The core validator+calibration+decision-replay methodology is evaluable, and largely already evaluated, at the current 3-scene, 4-reference-graph scale — what's missing is finishing the scoring pass on data that already exists or is already running, and being honest in the writeup about which of the four claimed contributions the data actually supports.

---

#### 5. If there is a viable paper, the framing that fits what was shown

**Do not frame this as "a validated method that improves active semantic exploration."** The data does not support that claim for two of the four pieces (calibration-as-distinct-from-thresholding, and the risk term), and the one piece with a decision-level result (filter-only) is single-scene.

**The framing that fits the evidence is closer to a case study in why decision-level replay matters more than offline graph metrics — with the validator/threshold-filtering result as the one piece of positive content, and the calibration and risk-term results reported as honest negative/null findings, not as failures to hide.**

Concretely, a workshop paper (or a strong course report, which is what this actually is per `IMPLEMENTATION_RESEARCH.md`'s own framing as "CVP course proposal") could credibly claim:

- **Headline finding:** a simple, deterministic structural validator plus an ensemble-unanimity filter on LLM scene-graph completions improves precision and normalized graph-edit-distance without hurting recall, held out across 4 scenes with zero disagreement between two independent selection criteria (DEVIATIONS #67) — under a substitute LLM backend, disclosed as such throughout.
- **Methodological contribution:** decision-level replay against the pinned uncertainty calculator is necessary, not optional, because a static-graph improvement does not imply a better navigation decision — demonstrated concretely twice in this project's own history (the candidate-pool-sharing fix and, more strikingly, the frustum-vs-occlusion bug that reversed the entire headline finding of an intermediate iteration). This is a methods point that generalizes past this specific pipeline: *whenever an offline "improved graph quality" ablation exists alongside a live decision-making loop, the ablation's win is not evidence about the loop until it is replayed through the loop's own scoring function with its own visibility model, not an approximation of it.*
- **Explicitly negative/null findings, reported as findings, not gaps:** leave-one-scene-out calibration produces a real but weak and unevenly-generalizing signal (0.81% positive rate, one of four folds unable to discriminate three support levels, the pooled headline number actually a room-only effect) and — under the data collected so far — is mathematically indistinguishable in its filtering behavior from uncalibrated support thresholding; the proposed risk-sensitive term exhibits the specific failure mode (rewarding low-information regions at high β) that a pre-registered concern predicted, confirmed on real replayed decisions rather than assumed.
- **Honest scope statement:** all of the above holds for one substitute LLM backend (DeepSeek V4.1 Flash, capability-tier different from the paper's Gemini 2.5 Pro, no paired comparison available), a small and now further-reduced scene count with no seed repeat, and a decision-replay harness that is an explicitly labeled approximation lacking the live ROS reachability gate.

That is a defensible, evidence-matched paper: strong on the validator/filtering result and the decision-replay methodology point, transparent and specific about where the calibration and risk-scoring proposals did not pan out as specified, and correctly scoped to what a substitute-backend, small-N replication can support. It is not the paper `IMPLEMENTATION_RESEARCH.md` set out to write (all four pieces working together as a calibrated-risk-sensitive policy that beats official ASP), and claiming that paper instead of this one is exactly the overclaim this project's own culture — visible in every DEVIATIONS.md correction — has so far refused to make.
