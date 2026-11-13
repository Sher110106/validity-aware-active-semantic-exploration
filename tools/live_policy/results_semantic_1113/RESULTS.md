# Part 3 results: are the model's guesses right in meaning?

Written 13 Nov 2026. Times are IST.

Every number here has a row in `numbers_part3.csv`, with its file and its path in that file. `build_numbers_part3.py` rebuilds the csv from the result files and fails if a table, or a number in the prose that carries its csv key in an HTML comment, no longer matches them. The tables sit between `<!-- table:name -->` markers: do not edit them by hand; run the script with `--fill`.

Every verdict below holds for two houses, on a truth that is a proxy for what the camera saw, on static replays. It says nothing about other houses.

**Words used here.**
- *Exploratory*: DeepSeek, Gemini and the placebo scored as a model. The scorer was written after DeepSeek's numbers were seen, so these results carry no verdict weight; the Claude replays are the blind test.
- *ASP*: the robot exploration method of the author's paper (arXiv 2510.05430), which the pipeline tests. *M2*: the part of the study that asks whether right meaning would be enough for ASP's score (section 8).
- *Row*: one stage of one saved run. There are 44<!--n:frame_rows-->. *Member*: one completion of a row's observed graph by a model; 4<!--n:rule_members--> per row. *Cluster*: scene × seed × arm; 12<!--n:frame_clusters--> in all. The cluster is the unit of every test.
- *Observed graph*: what the robot has mapped at that stage. *Mapped*: an observed object of the same class lies within 0.5<!--n:rule_reach_m--> m of the true one. *New object* and *new room*: a node more than 0.5<!--n:rule_reach_m--> m from every observed node of its kind.
- *Seen region*: the robot's path or map has covered it. *Unseen*: not seen. *Partly seen*: unseen, but a mapped object or an observed room node is in reach. *Unobserved*: unseen and not partly seen.
- *Open*: a room type is open if some unseen region of that type has none of its type's marker objects mapped (a toilet marks a bathroom). A class is open if an unseen region holds an unmapped object of that class.
- *Claim*: at L1 a distinct room type among a member's new rooms; at L2 a distinct class among its new objects. At L3 each new room or object is an *item*.
- *B1*: a random placebo. *B2*: copy the map (claim what is already observed; reported only). *B3*: the other-house prior. *B3L*: the prior's labels at the model's places. *B4*: the wrong-house comparator. *B5*: the model's labels shuffled among its own items. *D*: the unobserved regions swap what they hold.
- *Margin* (δ): the gain over the named comparator that a verdict tests for. *p*: one-sided; the chance of a difference this large or larger if the model were no better than the comparator.
- *ig*: the part of ASP's viewpoint score that measures how far the members' guesses differ about a candidate viewpoint. *U_wall_cone*: the unmapped objects a candidate could see past the walls inside the camera's cone; *U_cone* is the same without the wall test; *U_360* counts over a full turn.

## 1. What was tested

1. **The claim.** The ASP author says the model's guessed scene graphs sit in the wrong places but name the right things, and that this is enough for ASP. Part 3 tests the first half. M2 (section 8) tests the second.
2. **Three levels.** L1: does the model name room types that the house still holds, unseen and not yet mapped? L2: does it name object classes that the unseen part still holds? L3: does it put a new room or object in or near an unobserved region that has that type or holds that class?
3. **A hit.** An L1 or L2 claim hits if the house still holds that type or class, not yet mapped, in a region the robot has not seen. An L3 item hits if it lies inside an unobserved region of its type (or holding its class), or within 0.5<!--n:rule_reach_m--> m of one. Truth is the HM3D annotation of each house.
4. **The comparators.** At L1 and L2: B3, a prior built from 179<!--n:rule_houses--> other houses that makes the same number of claims as the model, and B1, a random placebo. At L3: B5, the model's own labels shuffled among its own items; D, the unobserved regions swapping what they hold; and B3L, the prior's labels put at the model's places. The comparator named for a verdict is B3 at L1 and L2 and D at L3.
5. **The family and the margins.** Two Claude models at three levels make 6<!--n:rule_hypotheses--> hypotheses, tested with Holm's correction at α = 0.05<!--n:rule_alpha-->. The unit is the cluster (scene × seed × arm); the test is the exact one-sided sign-flip test. The margin is 5<!--n:c_opus_L1_margin--> points at L1 and L2 and 3<!--n:c_opus_L3_margin--> points at L3.

**Verdict names.** *Supported*: the Holm-adjusted p is below 0.05<!--n:rule_alpha-->. *Rejected*: not Supported, and the upper end of the 95% interval for (model minus named comparator) lies below the margin. In plain words, the interval rules out a gain over the named comparator as large as the margin. It does not say the model is worse. Where the interval lies wholly below zero (L2 against the prior), the model does score below the comparator; that is a separate statement, and the tables show it. *Inconclusive*: anything else.

## 2. How it was run

- **The frame.** 44<!--n:frame_rows--> rows in 12<!--n:frame_clusters--> clusters. 36<!--n:frame_rows_runs--> rows are stages 3, 8 and 13<!--n:frame_stages--> of 12<!--n:frame_runs--> saved DeepSeek runs (houses 00853 and 00871). 8<!--n:frame_rows_gemini--> rows are the inputs Gemini saw in October.
- **The models.** Claude Opus 5.5 and Claude Haiku 5.5, the blind, confirmatory test. Effort medium, 4<!--n:rule_members--> members per row, at most 50<!--n:rule_turns--> turns, `max_tokens` 64,000<!--n:rule_max_tokens-->, no temperature, no seed, no fallback model. The prompt, the collision tool and the parser are the author's. The rows came in 4<!--n:rounds_used--> rounds, and both models finished all of them.
- **The members.** 352<!--n:mem_total--> members, 176<!--n:mem_opus_n--> for each model. Opus: 176<!--n:status_opus_ok--> scored, 0<!--n:status_opus_dropped--> dropped. Haiku: 175<!--n:status_haiku_ok--> scored and 1<!--n:status_haiku_dropped--> dropped (row `e2_00871_s43_filter_st03`, member 3). It stopped at the token limit (the `stop_max_tokens` flag in the `flags` field of its `record.json`; it is the only Haiku member with that flag, 1<!--n:mem_haiku_maxtok--> of 176<!--n:mem_haiku_n-->), and its final text did not parse (1<!--n:mem_haiku_parse_fail--> member). It was not refused and did not reach the turn limit. A member makes 2.35<!--n:mem_opus_calls--> calls (Opus) or 2.52<!--n:mem_haiku_calls--> (Haiku) on average, and 8.9<!--n:mem_opus_tools--> or 6.2<!--n:mem_haiku_tools--> collision checks.
- **Spend.** The replays cost $35.78<!--n:spend_replay-->: Opus $34.68<!--n:spend_replay_opus-->, Haiku $1.10<!--n:spend_replay_haiku-->. The caps were $280<!--n:rule_cap_opus--> and $20<!--n:rule_cap_haiku-->. The smoke test cost $2.84<!--n:spend_smoke--> and the no-hint replay $0.30<!--n:spend_nohint-->. The three ledgers sum to $38.92<!--n:spend_all-->. Prices come from the price card bundled with the tools, not from the live page.
- **Order of events** (13 Nov).
  - 18:59<!--n:t_prereg_hash-->: we hash the pre-registration (sha256 59c97ad6<!--n:hash_prereg-->…) and push it at 19:00<!--n:t_prereg_push-->.
  - 19:15<!--n:t_m2_hash-->: we hash the M2 pre-registration.
  - 19:25<!--n:t_cost_hash-->: we hash the cost addendum. The replay starts at 19:25<!--n:t_replay_start-->.
  - 20:12<!--n:t_truth_hash-->: we hash the truth files, label table and frame.
  - 20:13<!--n:t_exploratory-->: the first scoring run, on DeepSeek, Gemini and the placebo.
  - 20:14<!--n:t_freeze-->: we freeze the scorer (freeze file sha256 7d9c3822<!--n:hash_freeze-->…) and push it. No Claude output has been scored.
  - 20:38<!--n:t_replay_end-->: the replay ends.
  - 20:41<!--n:t_scored-->: the saved Claude scores come from a single run with the frozen scorer; no other run is recorded. No scorer file changed between the freeze and this run, and the driver refuses to score Claude output unless the freeze check passes.
  - 20:50<!--n:t_nohint-->: the no-hint replay runs, after we knew the result (deviation 56). 21:10<!--n:t_margin_check-->: the margin check of section 3 runs, also after we knew the result (deviation 55).

**Points the frozen files left open** (deviations 51 and 52, settled before the scorer ran on any model output).
- A result can meet two thesis rows. The rows apply in the table's order.
- A new room typed "dining" is left out of L3 as well as L1, and counted.
- Names ending in beam, column or pillar map to a structure class. No score changes.
- The share of items that reach two regions is given twice: over all regions and over unobserved regions only.
- The paper's room test is given over all stages and over stages that hold 8 members. The 2-of-8 view is reported for DeepSeek, the only model with live members, over the stages the file holds.
- The prior that knows the house's size has three sensitivity lines: seen counts, size, and both.
- The head-noun step of the label table gives a few names in other houses an odd class ("dog bed" answers to bed). Neither test house holds such a name; only the other-house prior's counts change.
- On a replay, "before it is seen" uses the states of the run the row came from.
- M2's silent points (deviation 54, written at 20:25, after the 20:13 exploratory run and before M2's first pass) are listed in section 8.

## 3. The confirmatory result

A score is the model's mean hit rate over the 12<!--n:frame_clusters--> clusters. A difference is the model minus the comparator, in points. It uses only the rows where both sides have a score; the Rows column counts them (rows for the named comparator). At L1 a model has no score in a row where it proposed no typed new room, and 2<!--n:l1_impossible_opus--> rows have no open room type at all. So the L1 contrasts rest on 41<!--n:l1_rows_opus--> rows for Opus (44<!--n:frame_rows--> − 2<!--n:l1_impossible_opus--> − 1<!--n:l1_noclaim_opus-->), 24<!--n:l1_rows_haiku--> for Haiku (44<!--n:frame_rows--> − 2<!--n:l1_impossible_opus--> − 18<!--n:l1_noclaim_haiku-->) and 42<!--n:l1_rows_deepseek--> for DeepSeek (exploratory; 44<!--n:frame_rows--> − 2<!--n:l1_impossible_opus--> − 0<!--n:l1_noclaim_deepseek-->). L3 against D uses 43<!--n:c_opus_L3_rows--> rows: a row with fewer than two unobserved regions has no D score. "Largest p" is the largest p over the hypothesis's comparators.

**L1 and L2.**

<!-- table:conf_l12 -->
| Hypothesis | Rows | Score | Placebo's own score | Diff vs B3 (p) | Diff vs B1 placebo (p) | 95% interval vs B3 | Margin (points) | Largest p | Holm p | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| Opus L1 | 41 | 85.4% | 87.5% | -5.8 (p 1.000) | -2.1 (p 0.727) | [-12.2, 0.0] | 5 | 1.000 | 1.000 | Rejected |
| Haiku L1 | 24 | 89.6% | 87.5% | -10.4 (p 1.000) | -5.2 (p 0.859) | [-20.8, 0.0] | 5 | 1.000 | 1.000 | Rejected |
| Opus L2 | 44 | 58.3% | 60.6% | -35.1 (p 1.000) | -2.3 (p 0.830) | [-41.3, -29.1] | 5 | 1.000 | 1.000 | Rejected |
| Haiku L2 | 44 | 68.8% | 60.6% | -24.9 (p 1.000) | +8.2 (p 0.014) | [-31.5, -18.1] | 5 | 1.000 | 1.000 | Rejected |
<!-- /table:conf_l12 -->

**L3.** The placebo is not a comparator at L3; its own score stands beside the model's.

<!-- table:conf_l3 -->
| Hypothesis | Rows | Score | Placebo's own score | Diff vs B5 (p) | Diff vs D (p) | Diff vs B3L (p) | 95% interval vs D | Margin (points) | Largest p | Holm p | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Opus L3 | 43 | 4.2% | 1.7% | -0.2 (p 0.601) | +0.5 (p 0.326) | -6.3 (p 1.000) | [-1.9, +2.9] | 3 | 1.000 | 1.000 | Rejected |
| Haiku L3 | 43 | 4.4% | 1.7% | -0.5 (p 0.901) | +0.8 (p 0.150) | -5.8 (p 1.000) | [-0.8, +2.4] | 3 | 1.000 | 1.000 | Rejected |
<!-- /table:conf_l3 -->

**The wrong-house gate.** B4 scores the same model's guesses for the other house against this house's truth. The gate asks whether the model does better with its own house: the exact sign-flip test over the 6<!--n:rule_gate_pairs--> seed × arm pairs, one-sided, p below 0.05<!--n:rule_alpha-->, with no Holm correction. With 6<!--n:rule_gate_pairs--> pairs the smallest possible p is 1/64<!--n:rule_gate_pmin-->. No row passes. Haiku L1 has fewer pairs because a pair had no value.

<!-- table:gate -->
| Row | Mean difference (points) | Pairs | p | Passes |
|---|---|---|---|---|
| Opus L1 | +8.9 | 6 | 0.125 | no |
| Haiku L1 | -5.0 | 5 | 1.000 | no |
| Opus L2 | -6.3 | 6 | 1.000 | no |
| Haiku L2 | -4.4 | 6 | 0.953 | no |
<!-- /table:gate -->

**The thesis.** The result file gives "The claim fails<!--n:thesis-->". The rule is the registered one: *the claim fails* when every Claude model is Rejected at L2 and at L3. Both models are Rejected at L2 and at L3 in the tables above. The earlier rows do not apply: no Claude model is Supported at L3 (the claim holds) and none is Supported at L1 or L2 (mixed). My reading of the rule gives the same line as the file, and so does every verdict above.

**The independent recompute.** A checker wrote its own code from the pre-registration text, without opening the scorer. For both Claude models and DeepSeek, every count of claims, items and hits matches the scorer. The differences against the prior, the placebo and the prior's labels match to the last digit, and the p-values match exactly. The two randomised controls, B5 and D, match within the noise of their draws. The six verdicts and the thesis line match. The checker's code carries options for points the rules leave open (`reach_to`, set to "square"; `step7_from`, set to "singular"). Its README and its header do not say whether they were set before or after it compared its output with the scorer's.

**The one close verdict.** Opus at L3 is Rejected because the upper end of its interval against D is 2.95<!--n:p_opus_L3_D_hi2--> points, and the margin is 3<!--n:c_opus_L3_margin-->: the gap is 0.05<!--n:p_opus_L3_D_gap--> points. D is a randomised control, so its draws move that end. After the result was known, the checker reran D with 10<!--n:rc_opus_runs200--> other seeds at the registered 200<!--n:rc_opus_draws_lo--> draws and 5<!--n:rc_opus_runs5000--> seeds at 5000<!--n:rc_opus_draws_hi--> draws. The upper end ran from 2.83<!--n:rc_opus_hi_min--> to 2.98<!--n:rc_opus_hi_max--> points, below 3<!--n:c_opus_L3_margin--> in 15<!--n:rc_opus_below--> of 15<!--n:rc_opus_below--> runs. A seed that crossed 3<!--n:c_opus_L3_margin--> would have made Opus at L3 Inconclusive, and the thesis line Inconclusive. This check was made after the result was seen (deviation 55). The registered figure, 2.95<!--n:p_opus_L3_D_hi2-->, is the one reported. Haiku's upper end is 2.36<!--n:p_haiku_L3_D_hi2-->, 0.64<!--n:p_haiku_L3_D_gap--> points below the margin; over its 15<!--n:rc_haiku_below--> reruns it ran from 2.30<!--n:rc_haiku_hi_min--> to 2.45<!--n:rc_haiku_hi_max-->.

## 4. What the table shows, and what it does not

At L1 and L2 each Claude model scores below the prior built from 179<!--n:rule_houses--> other houses, which makes the same number of claims as the model; at L2 the difference is -35.1<!--n:c_opus_L2_B3_diff--> points for Opus and -24.9<!--n:c_haiku_L2_B3_diff--> for Haiku, and the interval lies wholly below zero. At L3 the comparison is with the model's own content traded across unobserved regions (D): the differences are +0.5<!--n:c_opus_L3_D_diff--> points [-1.9<!--n:c_opus_L3_Dci_lo-->, +2.9<!--n:c_opus_L3_Dci_hi-->] for Opus and +0.8<!--n:c_haiku_L3_D_diff--> [-0.8<!--n:c_haiku_L3_Dci_lo-->, +2.4<!--n:c_haiku_L3_Dci_hi-->] for Haiku, both intervals include zero, and the data show no detectable difference (the registered detectable difference is 1.1<!--n:mdd_L3_mdd--> points, computed on the placebo's contrast; section 5 says why it is too small here), so gains up to 2.95<!--n:p_opus_L3_D_hi2--> (Opus) and 2.36<!--n:p_haiku_L3_D_hi2--> (Haiku) points are not ruled out. The table does not show that the guesses reach the map: L3 hit rates are 4.2%<!--n:c_opus_L3_score--> for Opus and 4.4%<!--n:c_haiku_L3_score--> for Haiku, in two houses, on a proxy truth, on static replays.

Two facts weigh against the main result.
1. Opus at L3 is 0.05<!--n:p_opus_L3_D_gap--> points inside the margin: its interval's upper end is 2.95<!--n:p_opus_L3_D_hi2--> points against a margin of 3<!--n:c_opus_L3_margin-->. The reruns of section 3 stayed below 3<!--n:c_opus_L3_margin-->, but one crossing would have changed the verdict.
2. One contrast favours a Claude model. Haiku scores +8.2<!--n:c_haiku_L2_B1_diff--> points above the placebo at L2 (p 0.014<!--n:c_haiku_L2_B1_p-->, one contrast, not adjusted). Its hypothesis stays Rejected: the hypothesis's p is the largest over B3 and B1, and B3 gives 1.000<!--n:c_haiku_L2_B3_p-->. Opus at L2 differs from the placebo by -2.3<!--n:c_opus_L2_B1_diff--> points [-7.4<!--n:p_opus_L2_B1ci_lo-->, +2.7<!--n:p_opus_L2_B1ci_hi-->] (p 0.830<!--n:c_opus_L2_B1_p-->): no detectable difference. The registered detectable difference at L2, 5.2<!--n:mdd_L2_mdd--> points, was computed on the placebo's own B1 minus B3 contrast, so it is only a guide to this contrast.

## 5. The detectable differences

The frozen table was written before any Claude output was scored. It comes from the placebo's own members: the standard deviation across clusters of B1 minus B3 at L1 and L2, and of B5 minus D at L3. It is the gain a test would find 80%<!--n:mdd_power--> of the time. It does not come from any Claude contrast.

<!-- table:mdd -->
| Level | Contrast | Clusters | SD of the contrast (points) | Detectable difference (points) | Margin (points) | Interval half-width (points) |
|---|---|---|---|---|---|---|
| L1 | B1-B3 | 12 | 6.1 | 5.7 | 5 | 3.8 |
| L2 | B1-B3 | 12 | 5.6 | 5.2 | 5 | 3.6 |
| L3 | B5-D | 12 | 1.2 | 1.1 | 3 | 0.7 |
<!-- /table:mdd -->

What they mean for reading "Rejected":
- A null is worded "no detectable difference", with the detectable difference beside it: 5.7<!--n:mdd_L1_mdd--> points at L1, 5.2<!--n:mdd_L2_mdd--> at L2, 1.1<!--n:mdd_L3_mdd--> at L3. Rejected is within reach at each level. But at L1 and L2 the detectable difference is larger than the 5<!--n:c_opus_L1_margin-->-point margin (5.7<!--n:mdd_L1_mdd--> and 5.2<!--n:mdd_L2_mdd-->), so a true gain equal to the margin would be found less than 80%<!--n:mdd_power--> of the time.
- The interval half-width in the frozen table is below the margin at each level (3.8<!--n:mdd_L1_hw--> against 5<!--n:mdd_L1_delta-->, 3.6<!--n:mdd_L2_hw--> against 5<!--n:mdd_L2_delta-->, 0.7<!--n:mdd_L3_hw--> against 3<!--n:mdd_L3_delta-->).
- At L2 the upper ends against B3 are -29.1<!--n:p_opus_L2_B3_hi--> (Opus) and -18.1<!--n:p_haiku_L2_B3_hi--> (Haiku) points: there "Rejected" means the model scores below the prior. At L1 the upper ends are 0.0<!--n:p_opus_L1_B3_hi--> and 0.0<!--n:p_haiku_L1_B3_hi-->: no gain over the prior shows, and the lower ends are well below zero.
- At L3 the intervals include zero. There, Rejected says only that the interval rules out a gain as large as 3<!--n:c_opus_L3_margin--> points. Gains up to 2.95<!--n:p_opus_L3_D_hi2--> (Opus) and 2.36<!--n:p_haiku_L3_D_hi2--> (Haiku) points are not ruled out.
- The registered L3 figure (1.1<!--n:mdd_L3_mdd--> points) comes from the placebo's B5 minus D contrast. That contrast varies less than a Claude model's contrast with D: the half-widths are 0.7<!--n:mdd_L3_hw--> points for the placebo and 2.4<!--n:p_opus_L3_D_hw--> and 1.6<!--n:p_haiku_L3_D_hw--> for Opus and Haiku. So a gain of 1.1<!--n:mdd_L3_mdd--> points could not have been seen in these data.
- Against B5 (the labels shuffled among the model's own items) the L3 difference is -0.2<!--n:c_opus_L3_B5_diff--> points [-1.8<!--n:p_opus_L3_B5ci_lo-->, +1.2<!--n:p_opus_L3_B5ci_hi-->] for Opus and -0.5<!--n:c_haiku_L3_B5_diff--> [-1.2<!--n:p_haiku_L3_B5ci_lo-->, +0.2<!--n:p_haiku_L3_B5ci_hi-->] for Haiku: no detectable difference. The registered figure, 1.1<!--n:mdd_L3_mdd--> points, is for the placebo's B5 minus D contrast.
- Haiku's L1 result rests on few claims (48<!--n:claims_haiku_l1--> claims, against 147<!--n:claims_opus_l1--> for Opus). Many of its new rooms have no scored type: 43<!--n:sup_haiku_untyped--> of 91<!--n:sup_haiku_rooms--> (47.3%<!--n:sup_haiku_share_u-->).

## 6. Exploratory results: DeepSeek, Gemini and the placebo

These are exploratory. The scorer was written after DeepSeek's numbers were seen. Each model has its own Holm family of three hypotheses; no thesis line applies. DeepSeek has 160<!--n:deepseek_members--> members on the 44<!--n:frame_rows--> rows (some failed in October); Gemini has 29<!--n:gemini_members--> members on its 8<!--n:gemini_rows--> rows, in 3<!--n:gemini_clusters--> clusters.

**L1 and L2.**

<!-- table:exp_l12 -->
| Hypothesis | Rows | Clusters | Score | Placebo's own score | Diff vs B3 (p) | Diff vs B1 placebo (p) | 95% interval vs B3 | Margin (points) | Largest p | Holm p | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DeepSeek (exploratory) L1 | 42 | 12 | 89.2% | 87.5% | -1.7 (p 1.000) | +1.7 (p 0.301) | [-5.2, 0.0] | 5 | 1.000 | 1.000 | Rejected |
| Gemini (exploratory) L1 | 8 | 3 | 100.0% | 87.5% | 0.0 (p 1.000) | 0.0 (p 1.000) | unbounded | 5 | 1.000 | 1.000 | Inconclusive |
| Placebo (exploratory) L1 | 42 | 12 | 87.5% | 87.5% | -4.9 (p 1.000) | n/a | [-8.3, -0.8] | 5 | 1.000 | 1.000 | Rejected |
| DeepSeek (exploratory) L2 | 44 | 12 | 66.4% | 60.6% | -26.3 (p 1.000) | +5.8 (p 0.024) | [-33.2, -19.4] | 5 | 1.000 | 1.000 | Rejected |
| Gemini (exploratory) L2 | 8 | 3 | 88.1% | 60.6% | -10.5 (p 1.000) | +22.7 (p 0.125) | unbounded | 5 | 1.000 | 1.000 | Inconclusive |
| Placebo (exploratory) L2 | 44 | 12 | 60.6% | 60.6% | -32.6 (p 1.000) | n/a | [-36.2, -29.1] | 5 | 1.000 | 1.000 | Rejected |
<!-- /table:exp_l12 -->

**L3.**

<!-- table:exp_l3 -->
| Hypothesis | Rows | Clusters | Score | Placebo's own score | Diff vs B5 (p) | Diff vs D (p) | Diff vs B3L (p) | 95% interval vs D | Margin (points) | Largest p | Holm p | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DeepSeek (exploratory) L3 | 43 | 12 | 4.8% | 1.7% | -0.6 (p 0.925) | -0.6 (p 0.852) | -4.8 (p 0.998) | [-1.9, +0.6] | 3 | 0.998 | 1.000 | Rejected |
| Gemini (exploratory) L3 | 8 | 3 | 9.9% | 1.7% | -1.3 (p 1.000) | +0.4 (p 0.500) | -3.2 (p 1.000) | unbounded | 3 | 1.000 | 1.000 | Inconclusive |
| Placebo (exploratory) L3 | 43 | 12 | 1.7% | 1.7% | -0.1 (p 0.634) | -0.2 (p 0.739) | -4.1 (p 1.000) | [-1.0, +0.5] | 3 | 1.000 | 1.000 | Rejected |
<!-- /table:exp_l3 -->

**The wrong-house gate.** The 8<!--n:frame_rows_gemini--> Gemini rows have no partner house, so there is no gate for Gemini.

<!-- table:gate_exp -->
| Row | Mean difference (points) | Pairs | p | Passes |
|---|---|---|---|---|
| DeepSeek (exploratory) L1 | -1.7 | 6 | 1.000 | no |
| Gemini (exploratory) L1 | none | 0 | n/a | no |
| DeepSeek (exploratory) L2 | -5.3 | 6 | 1.000 | no |
| Gemini (exploratory) L2 | none | 0 | n/a | no |
<!-- /table:gate_exp -->

- DeepSeek is Rejected at all three levels. Against the placebo it scores +5.8<!--n:e_deepseek_L2_B1_diff--> points at L2 (p 0.024<!--n:e_deepseek_L2_B1_p-->, not adjusted).
- Gemini has 3<!--n:gemini_clusters--> clusters, so its intervals are unbounded and its verdicts are Inconclusive at all three levels. Its differences are for reading only.
- The placebo, scored as a model, is Rejected at all three levels. The verdict says only that the interval rules out a gain as large as the margin. B1 is itself, so it has no B1 contrast.

## 7. The secondary readouts

No verdict rests on these. Nothing is corrected for the number of looks. Each view is scored against comparators built under the same view. Rows for DeepSeek, Gemini and the placebo are exploratory; each is marked. In every table of this section a difference uses only the rows where both sides have a score, while the scores and shares beside it use all the rows a side has. The two need not agree.

**Claims behind the scores.** The claims and items each model made. "Rows behind the L1 contrasts" counts rows with a possible hit and an L1 score, so it agrees with the Rows column of section 3.

<!-- table:claims -->
| Model | Members scored | Rows behind the L1 contrasts | L1 claims | L2 claims | L3 items |
|---|---|---|---|---|---|
| Opus | 176 | 41 | 147 | 1279 | 1495 |
| Haiku | 175 | 24 | 48 | 819 | 942 |
| DeepSeek (exploratory) | 160 | 42 | 181 | 1546 | 2046 |
| Gemini (exploratory) | 29 | 8 | 36 | 294 | 385 |
| Placebo (exploratory) | 176 | 42 | 221 | 1224 | 1942 |
<!-- /table:claims -->

**L1 and L2 under other rules.** *Looser rule*: a hit needs only an unseen region of the type, or one holding the class, mapped or not. *Detector words only*: the L2 classes in the detector's 52<!--n:rule_vocab-->-word vocabulary. *Without extended table*: "answers to" uses `synonym_primary` alone. Under the looser rule no member's score changed (0<!--n:loose_diff_opus--> of 176<!--n:loose_n_opus--> Opus members, 0<!--n:loose_diff_haiku--> of 175<!--n:loose_n_haiku--> Haiku, 0<!--n:loose_diff_deepseek--> of 160<!--n:loose_n_deepseek--> DeepSeek members, exploratory), so its rows repeat the primary rows: in these two houses the two rules find the same hits. The reason lies in the truth sets (`supplement/supplement.json`). The looser sets differ from the primary ones in 2<!--n:loose_rows--> of the 44<!--n:frame_rows--> rows: by one class, "fridge<!--n:loose_label-->", in 2<!--n:loose_rows_classes--> rows, and by a room type in 0<!--n:loose_rows_types-->. In those rows no member proposed a new object of that class: 0<!--n:loose_claims_opus--> of 8<!--n:loose_members_in_rows_opus--> Opus members, 0<!--n:loose_claims_haiku--> of 8<!--n:loose_members_in_rows_haiku--> Haiku, 0<!--n:loose_claims_deepseek--> of 6<!--n:loose_members_in_rows_deepseek--> DeepSeek. Two facts from the scorer's notes. A guess labelled "stove" can never hit in either house under the frozen label rules: in 00853 the annotation "oven and stove" answers to "oven", and in 00871 "stovetop" answers to "gas stove". In the view without the extended table, a bed answers only to "bed", and no detector "duvet" maps a bed.

<!-- table:sec_l1l2 -->
| Reading | Score | Diff vs B3 [interval] | Diff vs B1 placebo [interval] |
|---|---|---|---|
| Looser rule, Opus L1 | 85.4% | -5.8 [-12.2, 0.0] | -2.1 [-9.7, +4.2] |
| Looser rule, Opus L2 | 58.3% | -35.1 [-41.3, -29.1] | -2.3 [-7.4, +2.7] |
| Looser rule, Haiku L1 | 89.6% | -10.4 [-20.8, 0.0] | -5.2 [-16.2, +5.2] |
| Looser rule, Haiku L2 | 68.8% | -24.9 [-31.5, -18.1] | +8.2 [+1.1, +14.9] |
| Looser rule, DeepSeek (exploratory) L1 | 89.2% | -1.7 [-5.2, 0.0] | +1.7 [-4.2, +7.5] |
| Looser rule, DeepSeek (exploratory) L2 | 66.4% | -26.3 [-33.2, -19.4] | +5.8 [+0.1, +11.4] |
| Detector words only, Opus L2 | 78.9% | -15.1 [-26.8, -5.1] | +7.0 [-0.5, +14.0] |
| Detector words only, Haiku L2 | 84.4% | -9.5 [-15.4, -3.7] | +12.4 [+1.7, +23.1] |
| Detector words only, DeepSeek (exploratory) L2 | 74.9% | -18.7 [-28.9, -8.6] | +3.0 [+0.3, +5.7] |
| Without extended table, Opus L2 | 58.4% | -27.3 [-33.8, -21.7] | -2.9 [-8.5, +2.4] |
| Without extended table, Haiku L2 | 66.5% | -16.9 [-26.2, -6.9] | +5.2 [-2.0, +12.4] |
| Without extended table, DeepSeek (exploratory) L2 | 65.5% | -19.6 [-25.1, -13.9] | +4.2 [-0.9, +9.2] |
<!-- /table:sec_l1l2 -->

**L3 under other rules.** *Partly seen regions* replace the unobserved ones. The partly seen view leaves out rows with no such region.

<!-- table:sec_l3 -->
| Reading | Score | Rows with no region (left out) | Diff vs B5 [interval] | Diff vs D [interval] | Diff vs B3L [interval] |
|---|---|---|---|---|---|
| Partly seen regions, Opus | 3.1% | 17 | +0.7 [-0.3, +2.1] | +2.9 [-2.8, +12.9] | -1.0 [-2.3, 0.0] |
| Partly seen regions, Haiku | 3.4% | 17 | -0.4 [-1.4, +0.3] | +3.9 [-2.3, +13.3] | -4.7 [-13.6, +1.6] |
| Partly seen regions, DeepSeek (exploratory) | 1.8% | 17 | -0.6 [-1.4, +0.1] | +0.8 [-2.0, +3.9] | -2.7 [-7.0, 0.0] |
| Detector words only, Opus | 4.4% | 0 | -1.1 [-3.4, +1.0] | +0.2 [-3.3, +3.8] | -6.3 [-11.4, -1.4] |
| Detector words only, Haiku | 5.8% | 0 | -0.7 [-2.1, +0.6] | +0.9 [-2.0, +3.9] | -5.5 [-8.8, -2.4] |
| Detector words only, DeepSeek (exploratory) | 6.1% | 0 | -1.3 [-2.5, -0.2] | -0.2 [-1.7, +1.3] | -5.1 [-9.0, -1.2] |
| Without extended table, Opus | 4.2% | 0 | -0.2 [-1.8, +1.2] | +0.5 [-1.9, +3.0] | -5.1 [-8.0, -2.4] |
| Without extended table, Haiku | 4.4% | 0 | -0.4 [-1.2, +0.3] | +0.8 [-0.8, +2.5] | -5.2 [-9.0, -1.9] |
| Without extended table, DeepSeek (exploratory) | 4.8% | 0 | -0.5 [-1.4, +0.4] | -0.6 [-1.8, +0.7] | -4.6 [-7.5, -1.7] |
<!-- /table:sec_l3 -->

Clusters behind the partly seen contrasts (of 12<!--n:frame_clusters-->):

<!-- table:sec_partly_n -->
| Row | Clusters vs B5 | Clusters vs D |
|---|---|---|
| Opus | 10 | 7 |
| Haiku | 10 | 7 |
| DeepSeek (exploratory) | 10 | 7 |
<!-- /table:sec_partly_n -->

**The prior under three sensitivity forms** (diff vs the prior, in points).

<!-- table:sec_prior -->
| Row | B3 (registered) | B3 with seen counts | B3 with house size | B3 with both |
|---|---|---|---|---|
| Opus L1 | -5.8 [-12.2, 0.0] | -9.0 [-16.9, -1.4] | -5.8 [-12.2, 0.0] | -11.8 [-21.6, -2.1] |
| Haiku L1 | -10.4 [-20.8, 0.0] | -10.4 [-20.8, 0.0] | -10.4 [-20.8, 0.0] | -10.4 [-20.8, 0.0] |
| DeepSeek (exploratory) L1 | -1.7 [-5.2, 0.0] | -5.2 [-11.7, 0.0] | -1.7 [-5.2, 0.0] | -8.0 [-18.3, 0.0] |
| Opus L2 | -35.1 [-41.3, -29.1] | -33.7 [-40.0, -27.6] | -34.7 [-41.3, -28.2] | -33.4 [-39.0, -28.0] |
| Haiku L2 | -24.9 [-31.5, -18.1] | -24.4 [-29.9, -18.6] | -24.8 [-31.8, -17.7] | -22.8 [-28.8, -16.2] |
| DeepSeek (exploratory) L2 | -26.3 [-33.2, -19.4] | -24.6 [-31.2, -18.0] | -25.2 [-31.1, -19.2] | -23.9 [-29.3, -18.4] |
<!-- /table:sec_prior -->

**B2, copy the map.** B2 claims what the observed graph already holds. It is reported only, beside the comparators of the family.

<!-- table:b2 -->
| Row | Rows | Diff vs B2 (p) | Interval |
|---|---|---|---|
| Opus L1 | 41 | +5.3 (p 0.113) | [-3.9, +14.3] |
| Haiku L1 | 24 | +2.4 (p 0.312) | [-5.6, +10.4] |
| DeepSeek (exploratory) L1 | 42 | +8.6 (p 0.023) | [+0.4, +17.7] |
| Opus L2 | 44 | -15.3 (p 1.000) | [-20.8, -9.9] |
| Haiku L2 | 44 | -4.8 (p 0.931) | [-11.2, +1.8] |
| DeepSeek (exploratory) L2 | 44 | -7.2 (p 0.996) | [-12.0, -2.3] |
<!-- /table:b2 -->

**One claim for one region, rooms and objects apart.** The comparison is with the placebo. For every Claude member the one-claim L1 score equals the plain L1 score (0<!--n:oneclaim_diff_opus--> of 136<!--n:oneclaim_n_opus--> Opus members and 0<!--n:oneclaim_diff_haiku--> of 47<!--n:oneclaim_n_haiku--> Haiku members differ); for DeepSeek (exploratory) 4<!--n:oneclaim_diff_deepseek--> of 155<!--n:oneclaim_n_deepseek--> differ.

<!-- table:x_misc -->
| Readout | Model | Model's share | Placebo's share | Diff vs placebo [interval] | p |
|---|---|---|---|---|---|
| L1, one claim to one region | Opus | 85.4% | 78.2% | +7.2 [-2.2, +16.5] | 0.057 |
| L1, one claim to one region | Haiku | 89.6% | 78.2% | +5.2 [-7.8, +18.8] | 0.216 |
| L1, one claim to one region | DeepSeek (exploratory) | 88.3% | 78.2% | +10.1 [+3.6, +16.5] | 0.004 |
| L3, rooms only | Opus | 16.7% | 2.7% | +13.9 [+1.4, +27.1] | 0.016 |
| L3, rooms only | Haiku | 6.0% | 2.7% | +2.1 [-7.3, +11.1] | 0.359 |
| L3, rooms only | DeepSeek (exploratory) | 5.9% | 2.7% | +3.1 [-3.0, +9.6] | 0.164 |
| L3, objects only | Opus | 3.1% | 1.5% | +1.6 [-1.0, +4.4] | 0.122 |
| L3, objects only | Haiku | 4.3% | 1.5% | +2.8 [-0.2, +6.0] | 0.034 |
| L3, objects only | DeepSeek (exploratory) | 4.8% | 1.5% | +3.3 [+0.9, +5.7] | 0.006 |
<!-- /table:x_misc -->

**Items that reach two regions.** The share of L3 items that reach two or more regions.

<!-- table:x_multi -->
| Readout | Model | Model's share | Placebo's share | Diff vs placebo [interval] | p |
|---|---|---|---|---|---|
| Share reaching two or more regions | Opus | 26.2% | 22.8% | +3.4 [-1.6, +8.6] | 0.089 |
| Share reaching two or more regions | Haiku | 25.1% | 22.8% | +2.3 [-4.5, +9.2] | 0.233 |
| Share reaching two or more regions | DeepSeek (exploratory) | 23.7% | 22.8% | +1.0 [-5.1, +6.9] | 0.361 |
| Share reaching two or more unobserved regions | Opus | 3.8% | 0.6% | +3.2 [+0.1, +6.4] | 0.021 |
| Share reaching two or more unobserved regions | Haiku | 3.2% | 0.6% | +2.6 [-0.4, +6.0] | 0.051 |
| Share reaching two or more unobserved regions | DeepSeek (exploratory) | 4.3% | 0.6% | +3.7 [+0.7, +6.9] | 0.005 |
<!-- /table:x_multi -->

**L4.** The share of new objects within a distance of an unmapped reference object of their class in an unseen region.

<!-- table:x_l4 -->
| Readout | Model | Model's share | Placebo's share | Diff vs placebo [interval] | p |
|---|---|---|---|---|---|
| Within 0.5 m | Opus | 0.2% | 0.2% | 0.0 [-0.2, +0.2] | 0.562 |
| Within 0.5 m | Haiku | 0.4% | 0.2% | +0.2 [-0.3, +0.9] | 0.406 |
| Within 0.5 m | DeepSeek (exploratory) | 0.5% | 0.2% | +0.3 [0.0, +0.8] | 0.062 |
| Within 1 m | Opus | 0.7% | 0.7% | +0.1 [-0.7, +0.9] | 0.404 |
| Within 1 m | Haiku | 1.1% | 0.7% | +0.5 [-0.7, +1.7] | 0.201 |
| Within 1 m | DeepSeek (exploratory) | 2.1% | 0.7% | +1.4 [+0.2, +2.8] | 0.015 |
| Within 2 m | Opus | 3.1% | 1.9% | +1.2 [-0.6, +3.2] | 0.111 |
| Within 2 m | Haiku | 5.9% | 1.9% | +4.0 [+0.4, +7.9] | 0.016 |
| Within 2 m | DeepSeek (exploratory) | 5.0% | 1.9% | +3.1 [+1.6, +4.9] | <0.001 |
| Within 3 m | Opus | 6.1% | 5.2% | +0.9 [-2.2, +4.1] | 0.271 |
| Within 3 m | Haiku | 9.5% | 5.2% | +4.3 [-0.1, +9.0] | 0.027 |
| Within 3 m | DeepSeek (exploratory) | 8.7% | 5.2% | +3.6 [+0.6, +6.6] | 0.010 |
<!-- /table:x_l4 -->

**What the guesses hold.** The scorer does not save these counts; `supplement/supplement.py` counts them with the scorer's own loaders and label functions. A new object is "other" if its label has no class in the label table, and "structure" if it maps to a structure class. The flag is `is_predicted`. A new room typed dining is left out of L1 and L3 and counted here (deviation 51). Opus flags all its new objects; Haiku flags 51<!--n:sup_haiku_flag--> of 898<!--n:sup_haiku_objects-->; Gemini flags none. No model has a new room typed dining.

<!-- table:sup_labels -->
| Model | Members | New objects | Labelled other | Labelled structure | Share other or structure | With the flag | Without the flag | New rooms | Untyped | Share untyped | Typed dining (left out) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Opus | 176 | 1363 | 15 | 0 | 1.1% | 1363 | 0 | 190 | 43 | 22.6% | 0 |
| Haiku | 175 | 898 | 4 | 0 | 0.4% | 51 | 847 | 91 | 43 | 47.3% | 0 |
| DeepSeek (exploratory) | 160 | 1872 | 13 | 0 | 0.7% | 1849 | 23 | 198 | 11 | 5.6% | 0 |
| Gemini (exploratory) | 29 | 350 | 1 | 0 | 0.3% | 0 | 350 | 44 | 8 | 18.2% | 0 |
| Placebo (exploratory) | 176 | 1686 | 26 | 0 | 1.5% | 1686 | 0 | 282 | 0 | 0.0% | 0 |
<!-- /table:sup_labels -->

**The placement-error sample** (the input to M2's F3): the distance from each new object to the nearest unmapped object of its class in an unseen region. A guess with no such object is left out.

<!-- table:err -->
| Model | Distances | Guesses left out | Median (m) |
|---|---|---|---|
| Opus | 800 | 548 | 8.12 |
| Haiku | 617 | 277 | 7.13 |
| DeepSeek (exploratory) | 1249 | 610 | 7.67 |
| Gemini (exploratory) | 314 | 35 | 5.81 |
| Placebo (exploratory) | 1030 | 630 | 8.95 |
<!-- /table:err -->

**The paper's room test.** A region not seen at stage 0 counts as predicted before it is found if, at some stage before it is seen, at least 2<!--n:rule_room_k--> of the members put a new room within 2.5<!--n:rule_room_m--> m of its centre. The paper's figure is below. The placebo arm gives the chance rate: 8.7%<!--n:room_live_placebo_all_stages_typed_rate--> of its regions typed, 58.0%<!--n:room_live_placebo_all_stages_untyped_rate--> untyped, over all stages.

<!-- table:room_paper -->
| Source | Regions | Predicted before found |
|---|---|---|
| The paper | 28 | 9 |
<!-- /table:room_paper -->

*Live runs (DeepSeek, exploratory; 8 members at most; the placebo arm is the chance rate).*

<!-- table:room_live -->
| Live arm | Regions | Typed, all stages | Untyped, all stages | Typed, 8-member stages | Untyped, 8-member stages |
|---|---|---|---|---|---|
| Official | 59 | 13 (22.0%) | 52 (88.1%) | 10 (16.9%) | 37 (62.7%) |
| Filter only | 69 | 7 (10.1%) | 37 (53.6%) | 2 (2.9%) | 11 (15.9%) |
| Oracle visible | 39 | 5 (12.8%) | 26 (66.7%) | 5 (12.8%) | 26 (66.7%) |
| Placebo (chance rate) | 69 | 6 (8.7%) | 40 (58.0%) | 6 (8.7%) | 40 (58.0%) |
<!-- /table:room_live -->

*Replays (4 members; 1 of 4 and 2 of 4).* With the type required, Opus predicts 11<!--n:room_rep_opus_1of4_typed--> regions at 1 of 4 and 6<!--n:room_rep_opus_2of4_typed--> at 2 of 4, and Haiku 2<!--n:room_rep_haiku_1of4_typed--> and 1<!--n:room_rep_haiku_2of4_typed-->, of 171<!--n:room_rep_opus_of-->; the placebo predicts 8<!--n:room_rep_placebo_1of4_typed--> and 2<!--n:room_rep_placebo_2of4_typed-->. These are counts, not tests.

<!-- table:room_replay -->
| Model | Regions | 1 of 4, typed | 1 of 4, untyped | 2 of 4, typed | 2 of 4, untyped |
|---|---|---|---|---|---|
| Opus | 171 | 11 | 47 | 6 | 38 |
| Haiku | 171 | 2 | 27 | 1 | 17 |
| DeepSeek (exploratory) | 171 | 11 | 46 | 7 | 28 |
| Gemini (exploratory) | 33 | 3 | 8 | 2 | 7 |
| Placebo (exploratory) | 171 | 8 | 40 | 2 | 15 |
<!-- /table:room_replay -->

**The validity layer.** The validator is the E2 filter. First, the share of guesses it removes, by reason, for all five models.

<!-- table:val_removed -->
| Model | Guesses | Removed | Share removed | Box conflict | Impassable crossing | Object parent |
|---|---|---|---|---|---|---|
| Opus | 1553 | 132 | 8.5% | 22 | 110 | - |
| Haiku | 989 | 200 | 20.2% | 70 | 130 | - |
| DeepSeek (exploratory) | 2070 | 663 | 32.0% | 527 | 124 | 12 |
| Gemini (exploratory) | 394 | 14 | 3.6% | 4 | 10 | - |
| Placebo (exploratory) | 1968 | 1355 | 68.9% | 1168 | 187 | - |
<!-- /table:val_removed -->

Second, kept against removed guesses, in points, with the registered reading. The reading is "no detectable difference" only when the interval lies within ±5<!--n:rule_valid_band--> points; otherwise the interval is too wide to read.

<!-- table:val_kept -->
| Row | Rows | Clusters | Kept minus removed [interval] | Reading |
|---|---|---|---|---|
| Opus L2 | 17 | 10 | -4.3 [-25.6, +18.7] | interval reaches beyond ±5 points |
| Haiku L2 | 36 | 12 | -3.4 [-12.7, +7.8] | interval reaches beyond ±5 points |
| DeepSeek (exploratory) L2 | 43 | 12 | +0.4 [-4.7, +6.1] | interval reaches beyond ±5 points |
| Gemini (exploratory) L2 | 2 | 2 | -10.6 unbounded | interval reaches beyond ±5 points |
| Placebo (exploratory) L2 | 44 | 12 | +0.5 [-4.7, +5.8] | interval reaches beyond ±5 points |
| Opus L3 | 32 | 12 | -12.6 [-28.4, +1.0] | interval reaches beyond ±5 points |
| Haiku L3 | 37 | 12 | +0.1 [-4.7, +4.7] | no detectable difference |
| DeepSeek (exploratory) L3 | 43 | 12 | -0.1 [-2.3, +2.0] | no detectable difference |
| Gemini (exploratory) L3 | 6 | 3 | -4.5 unbounded | interval reaches beyond ±5 points |
| Placebo (exploratory) L3 | 44 | 12 | -0.2 [-1.9, +1.4] | no detectable difference |
<!-- /table:val_kept -->

Before the first scoring run, a worker's check script printed whether this readout lay inside or beyond the band for DeepSeek, the placebo and Gemini. It printed no number, and the scorer was not changed (deviation 52).

Third, member support against L3 truth: Brier score and expected calibration error (ECE) of the raw support, then with an isotonic calibrator fitted on one house and tested on the other.

<!-- table:val_reliab -->
| Model | Items | Brier | ECE |
|---|---|---|---|
| Opus | 1495 | 0.257 | 0.379 |
| Haiku | 942 | 0.136 | 0.248 |
| DeepSeek (exploratory) | 2046 | 0.166 | 0.275 |
<!-- /table:val_reliab -->

Raw support against the calibrated score, by test house:

<!-- table:val_cross -->
| Model and test house | Brier, raw support | Brier, calibrated | ECE, raw support | ECE, calibrated |
|---|---|---|---|---|
| Opus, tested on 00853 | 0.273 | 0.028 | 0.426 | 0.063 |
| Opus, tested on 00871 | 0.239 | 0.080 | 0.330 | 0.061 |
| Haiku, tested on 00853 | 0.157 | 0.056 | 0.257 | 0.040 |
| Haiku, tested on 00871 | 0.116 | 0.044 | 0.239 | 0.013 |
| DeepSeek (exploratory), tested on 00853 | 0.175 | 0.051 | 0.286 | 0.005 |
| DeepSeek (exploratory), tested on 00871 | 0.156 | 0.055 | 0.264 | 0.005 |
<!-- /table:val_cross -->

The reliability curve behind them: support is the share of the 4 members that hold the guess.

<!-- table:val_curve -->
| Model and support | Items | L3 hit rate |
|---|---|---|
| Opus 0.25 | 882 | 5.1% |
| Opus 0.50 | 286 | 4.2% |
| Opus 0.75 | 178 | 8.4% |
| Opus 1.00 | 149 | 4.7% |
| Haiku 0.25 | 819 | 5.5% |
| Haiku 0.50 | 87 | 4.6% |
| Haiku 0.75 | 7 | 0.0% |
| Haiku 1.00 | 29 | 0.0% |
| DeepSeek (exploratory) 0.25 | 1626 | 6.3% |
| DeepSeek (exploratory) 0.50 | 248 | 2.4% |
| DeepSeek (exploratory) 0.75 | 99 | 6.1% |
| DeepSeek (exploratory) 1.00 | 73 | 1.4% |
<!-- /table:val_curve -->

Fourth, guesses kept and hits kept at each vote level. The paper's 2-of-8 view exists for DeepSeek only, the one model with live members; the file holds one such view, over the stages it holds.

<!-- table:val_votes -->
| Model and view | Guesses kept | L2 hits | L2 claims | L3 hits | L3 items |
|---|---|---|---|---|---|
| Opus, raw | 1553 | 763 | 1279 | 79 | 1495 |
| Opus, validator | 1421 | 732 | 1235 | 65 | 1379 |
| Opus, validator + vote 0.5 | 555 | 290 | 468 | 23 | 538 |
| Opus, validator + vote 0.75 | 285 | 148 | 234 | 17 | 277 |
| Opus, validator + vote 1.0 | 122 | 67 | 100 | 4 | 122 |
| Haiku, raw | 989 | 573 | 819 | 49 | 942 |
| Haiku, validator | 789 | 468 | 669 | 43 | 756 |
| Haiku, validator + vote 0.5 | 116 | 64 | 79 | 3 | 105 |
| Haiku, validator + vote 0.75 | 33 | 9 | 9 | 0 | 31 |
| Haiku, validator + vote 1.0 | 26 | 5 | 5 | 0 | 24 |
| DeepSeek (exploratory), raw | 2070 | 1039 | 1546 | 115 | 2046 |
| DeepSeek (exploratory), validator | 1407 | 730 | 1095 | 77 | 1396 |
| DeepSeek (exploratory), validator + the paper's 2-of-8 rule | 472 | 267 | 347 | 23 | 471 |
| DeepSeek (exploratory), validator + vote 0.5 | 292 | 153 | 196 | 7 | 292 |
| DeepSeek (exploratory), validator + vote 0.75 | 113 | 35 | 44 | 4 | 113 |
| DeepSeek (exploratory), validator + vote 1.0 | 40 | 1 | 1 | 0 | 40 |
<!-- /table:val_votes -->

**The balance checks** (section 12). The drop rate is members not scored over members; the flag is a rate above 25<!--n:rule_drop_flag-->%. The "rejected because history was edited" count comes from the records: the loop sends history append-only and asks the API to fail on any edit, so a rejection would show as a ledger line whose `status` is not `ok`, or as a member record with an `error` or a `status` other than `ok`. Opus has 176<!--n:bal_records_opus--> member records and 457<!--n:bal_ledger_lines_opus--> ledger lines, Haiku 176<!--n:bal_records_haiku--> and 488<!--n:bal_ledger_lines_haiku-->. None has an error or a status other than `ok`.

<!-- table:sup_balance -->
| Model | Members | Dropped | Drop rate | Ledger lines not ok | Member records with an error |
|---|---|---|---|---|---|
| Opus | 176 | 0 | 0.0% | 0 | 0 |
| Haiku | 176 | 1 | 0.6% | 0 | 0 |
<!-- /table:sup_balance -->

**The prompt's hint (exploratory).** Haiku on the 12<!--n:frame_round1--> round-1 rows with the sentence "Scene may contain more than one bedroom and more than one bathroom" removed: 48<!--n:nohint_members--> members, all parsed, $0.30<!--n:spend_nohint-->. It ran after the confirmatory result was known (deviation 56). The hinted figures are the same 12<!--n:frame_round1--> rows of the confirmatory run. Rows with no L1 claim have no L1 score, so the row sets differ. The no-hint run's own results file gives the same L1 score (87.5%<!--n:nohint_file_score-->). The counts are small and decide nothing. Haiku's object claims that hit: 146<!--n:nohint_hint_l2h--> of 219<!--n:nohint_hint_l2n--> with the sentence and 150<!--n:nohint_nohint_l2h--> of 230<!--n:nohint_nohint_l2n--> without it.

<!-- table:nohint -->
| Run | Rows with an L1 score | L1 claims | L1 hits | L1 score (mean of row scores) | Members with a claim | L2 claims | L2 hits |
|---|---|---|---|---|---|---|---|
| With the hint | 6 | 9 | 5 | 66.7% | 9 | 219 | 146 |
| Without the hint | 8 | 12 | 11 | 87.5% | 12 | 230 | 150 |
<!-- /table:nohint -->

New rooms are room nodes more than 0.5 m, horizontally, from every room node of the row's observed graph. Over the 48<!--n:nhr_hint_members--> hinted members Haiku proposed 22<!--n:nhr_hint_total--> new rooms; over the 48<!--n:nhr_nohint_members--> members without the hint, 28<!--n:nhr_nohint_total-->. Names are as the model wrote them, with "an image of a" removed.

<!-- table:nohint_rooms -->
| New room name | With the hint | Without the hint |
|---|---|---|
| storage room | 7 | 9 |
| living room | 4 | 6 |
| bedroom | 3 | 4 |
| hallway | 1 | 5 |
| home office | 2 | 2 |
| bathroom | 1 | 1 |
| laundry room | 1 | 1 |
| study | 2 | 0 |
| closet | 1 | 0 |
| All new rooms | 22 | 28 |
<!-- /table:nohint_rooms -->

## 8. M2: would right meaning be enough for ASP's score?

M2 is descriptive, not blind; its reading rule was set in advance (pre-registration sha256 5b8a8400<!--n:m2_prereg_hash-->…). It reads ASP's own viewpoint score on 384<!--n:m2_stages--> bench stages from 24<!--n:m2_runs--> runs, and uses the Spearman correlation between the score and a yardstick of unmapped objects a candidate could see. F1 holds the true guesses, F5 the placebo, F6 none, F0 every true unmapped object, F3 the true objects moved by a model's placement error (its median error sits beside its row; DeepSeek's error file is exploratory), and F-room only objects typical of each unseen region's type.

<!-- table:m2_arms -->
| Arm | Mean correlation [interval] | Median per stage | Median placement error (m) |
|---|---|---|---|
| F1 (true guesses) | +0.284 [+0.261, +0.307] | +0.293 | - |
| F5 (placebo) | +0.065 [+0.042, +0.089] | +0.064 | - |
| F6 (no guesses) | -0.028 [-0.048, -0.007] | -0.028 | - |
| F0 (all true) | +0.048 [+0.027, +0.069] | +0.045 | - |
| F3 with DeepSeek's error | +0.046 [+0.028, +0.063] | +0.044 | 7.67 |
| F3 with Haiku's error | +0.060 [+0.041, +0.078] | +0.050 | 7.13 |
| F3 with Opus's error | +0.036 [+0.019, +0.054] | +0.034 | 8.12 |
| F-room (types only) | +0.089 [+0.073, +0.106] | +0.091 | - |
<!-- /table:m2_arms -->

The reading rule. A = F1 minus F5. If A lies wholly above 0, a candidate X is *sufficient* when the interval of X minus 0.5<!--n:rule_m2_half--> of A lies wholly above 0, *not shown sufficient* when it lies wholly below, and *inconclusive* otherwise. A is +0.218<!--n:m2_A_mean--> [+0.195<!--n:m2_A_lo-->, +0.241<!--n:m2_A_hi-->], so the rule goes on.

<!-- table:m2_reading -->
| Contrast | X minus F5 [interval] | X minus half of A [interval] | Verdict |
|---|---|---|---|
| A = F1 minus F5 | +0.218 [+0.195, +0.241] | - | F1 separates from F5 |
| B, F3 with DeepSeek's error | -0.020 [-0.036, -0.003] | -0.129 [-0.144, -0.113] | not shown sufficient, on a provisional yardstick |
| B, F3 with Haiku's error | -0.006 [-0.020, +0.009] | -0.115 [-0.130, -0.099] | not shown sufficient, on a provisional yardstick |
| B, F3 with Opus's error | -0.029 [-0.043, -0.015] | -0.138 [-0.154, -0.123] | not shown sufficient, on a provisional yardstick |
| C, F-room | +0.024 [+0.001, +0.047] | -0.085 [-0.103, -0.068] | not shown sufficient, on a provisional yardstick |
| F0 minus F5 | -0.017 [-0.031, -0.004] | - | not part of the reading rule |
| F6 minus F5 | -0.093 [-0.109, -0.078] | - | not part of the reading rule |
<!-- /table:m2_reading -->

On the primary yardstick, every M2 verdict is "not shown sufficient, on a provisional yardstick". No arm comes near the half of A that the rule asks for. F3 with Haiku's error differs from F5 by -0.006<!--n:m2_B_haiku_mean--> and with Opus's error by -0.029<!--n:m2_B_opus_mean-->: the Haiku interval includes 0 and the Opus interval lies below it. F-room differs from F5 by +0.024<!--n:m2_C_mean-->. F0 scores below F5: the difference is -0.017<!--n:m2_F0F5_mean--> [-0.031<!--n:m2_F0F5_lo-->, -0.004<!--n:m2_F0F5_hi-->], and the interval excludes zero. `ig` is 0 for every candidate in only 2<!--n:m2_f0_ig_zero--> of 384<!--n:m2_f0_ig_zero_of--> stages (0.5%<!--n:m2_f0_ig_zero_share-->). We have no tested account of why F0 falls below F5. The pre-registration (M2 §7) names it a property of the score: the score counts disagreement between members. No correction was made for running F3 for 3<!--n:rule_f3_models--> models.

Repeats on other yardsticks and subsets. The columns from A to C are X minus F5; the verdicts come from X minus half of A. Where a cell says "not shown", read "not shown sufficient, on a provisional yardstick".

<!-- table:m2_secondary -->
| Repeat | Stages | A = F1 minus F5 | B DeepSeek (X minus F5) | B Haiku (X minus F5) | B Opus (X minus F5) | C (X minus F5) | Verdicts (from X minus half of A) |
|---|---|---|---|---|---|---|---|
| `ig` alone | 382 | +0.244 [+0.221, +0.268] | -0.019 [-0.040, +0.002] | -0.005 [-0.024, +0.014] | -0.032 [-0.050, -0.013] | +0.019 [-0.008, +0.046] | B: not shown; C: not shown |
| Audit's U_cone | 384 | +0.505 [+0.467, +0.544] | +0.004 [-0.025, +0.033] | +0.007 [-0.026, +0.040] | -0.026 [-0.060, +0.008] | +0.162 [+0.121, +0.203] | B: not shown; C: not shown |
| U_360 | 384 | +0.318 [+0.289, +0.346] | +0.061 [+0.030, +0.092] | +0.060 [+0.028, +0.092] | +0.026 [-0.016, +0.070] | +0.194 [+0.147, +0.240] | B: not shown; C: inconclusive |
| Official-arm stages | 119 | +0.232 [+0.197, +0.268] | -0.008 [-0.027, +0.011] | -0.005 [-0.019, +0.008] | -0.027 [-0.048, -0.007] | +0.027 [-0.003, +0.058] | B: not shown; C: not shown |
| Runs clustered by scene and seed (6) | 384 | +0.218 [+0.189, +0.247] | -0.020 [-0.037, -0.002] | -0.006 [-0.018, +0.006] | -0.029 [-0.040, -0.019] | +0.024 [-0.005, +0.052] | B: not shown; C: not shown |
<!-- /table:m2_secondary -->

Under U_360 the reading for C is inconclusive: X minus half of A is +0.035<!--n:m2_u360_Chalf_mean--> [-0.004<!--n:m2_u360_Chalf_lo-->, +0.074<!--n:m2_u360_Chalf_hi-->]. The B arms stay "not shown sufficient" under every yardstick.

**R1 regret and objects per member, all stages.** R1 regret is the bench's measure of the first pick; lower is better.

<!-- table:m2_regret -->
| Arm | R1 regret under U_wall [interval] | R1 regret under U_wall_cone [interval] |
|---|---|---|
| F1 (true guesses) | 8.98 [8.52, 9.43] | 4.20 [3.95, 4.44] |
| F5 (placebo) | 9.66 [9.26, 10.07] | 4.52 [4.28, 4.76] |
| F6 (no guesses) | 10.06 [9.69, 10.41] | 4.90 [4.73, 5.07] |
| F0 (all true) | 10.57 [9.92, 11.20] | 5.06 [4.90, 5.22] |
| F3 with DeepSeek's error | 9.40 [8.98, 9.83] | 4.59 [4.40, 4.77] |
| F3 with Haiku's error | 9.61 [9.17, 10.04] | 4.68 [4.56, 4.80] |
| F3 with Opus's error | 9.87 [9.25, 10.48] | 4.71 [4.56, 4.86] |
| F-room (types only) | 9.59 [8.93, 10.25] | 4.62 [4.45, 4.79] |
<!-- /table:m2_regret -->

<!-- table:m2_objects -->
| Arm | Objects per member (mean) | Fewest | Most | Stages with ig = 0 for every candidate |
|---|---|---|---|---|
| F1 | 10.05 | 6 | 16 | 0 of 384 |
| F5, set A | 10.14 | 6 | 16 | 0 of 384 |
| F5, set B | 10.00 | 6 | 16 | 0 of 384 |
| F6 | 0.00 | 0 | 0 | 2 of 384 |
| F0 | 151.45 | 60 | 226 | 2 of 384 |
| F3 with DeepSeek's error | 10.05 | 6 | 16 | 0 of 384 |
| F3 with Haiku's error | 10.05 | 6 | 16 | 0 of 384 |
| F3 with Opus's error | 10.05 | 6 | 16 | 0 of 384 |
| F-room | 9.63 | 0 | 16 | 0 of 384 |
<!-- /table:m2_objects -->

**The official-arm stages alone** (119<!--n:m2_official_stages--> stages from 7<!--n:m2_official_runs--> runs): the same figures.

<!-- table:m2_arms_off -->
| Arm | Mean correlation [interval] | Median per stage | Median placement error (m) |
|---|---|---|---|
| F1 (true guesses) | +0.297 [+0.268, +0.326] | +0.309 | - |
| F5 (placebo) | +0.065 [+0.024, +0.106] | +0.075 | - |
| F6 (no guesses) | -0.025 [-0.061, +0.010] | -0.042 | - |
| F0 (all true) | +0.051 [+0.015, +0.086] | +0.041 | - |
| F3 with DeepSeek's error | +0.056 [+0.013, +0.100] | +0.052 | 7.67 |
| F3 with Haiku's error | +0.059 [+0.018, +0.101] | +0.054 | 7.13 |
| F3 with Opus's error | +0.038 [-0.003, +0.078] | +0.036 | 8.12 |
| F-room (types only) | +0.092 [+0.078, +0.105] | +0.089 | - |
<!-- /table:m2_arms_off -->

<!-- table:m2_reading_off -->
| Contrast | X minus F5 [interval] | X minus half of A [interval] | Verdict |
|---|---|---|---|
| A = F1 minus F5 | +0.232 [+0.197, +0.268] | - | F1 separates from F5 |
| B, F3 with DeepSeek's error | -0.008 [-0.027, +0.011] | -0.125 [-0.153, -0.096] | not shown sufficient, on a provisional yardstick |
| B, F3 with Haiku's error | -0.005 [-0.019, +0.008] | -0.122 [-0.139, -0.104] | not shown sufficient, on a provisional yardstick |
| B, F3 with Opus's error | -0.027 [-0.048, -0.007] | -0.143 [-0.174, -0.113] | not shown sufficient, on a provisional yardstick |
| C, F-room | +0.027 [-0.003, +0.058] | -0.089 [-0.111, -0.066] | not shown sufficient, on a provisional yardstick |
| F0 minus F5 | -0.014 [-0.033, +0.005] | - | not part of the reading rule |
| F6 minus F5 | -0.090 [-0.108, -0.073] | - | not part of the reading rule |
<!-- /table:m2_reading_off -->

<!-- table:m2_regret_off -->
| Arm | R1 regret under U_wall [interval] | R1 regret under U_wall_cone [interval] |
|---|---|---|
| F1 (true guesses) | 8.70 [8.22, 9.17] | 4.20 [3.75, 4.65] |
| F5 (placebo) | 9.05 [8.59, 9.51] | 4.50 [4.30, 4.70] |
| F6 (no guesses) | 9.57 [9.04, 10.11] | 4.87 [4.64, 5.11] |
| F0 (all true) | 9.76 [9.37, 10.15] | 4.98 [4.71, 5.26] |
| F3 with DeepSeek's error | 9.12 [8.58, 9.61] | 4.69 [4.41, 4.97] |
| F3 with Haiku's error | 9.09 [8.66, 9.51] | 4.54 [4.38, 4.71] |
| F3 with Opus's error | 9.02 [8.59, 9.45] | 4.57 [4.25, 4.90] |
| F-room (types only) | 8.67 [7.86, 9.48] | 4.40 [4.26, 4.54] |
<!-- /table:m2_regret_off -->

<!-- table:m2_objects_off -->
| Arm | Objects per member (mean) | Fewest | Most | Stages with ig = 0 for every candidate |
|---|---|---|---|---|
| F1 | 9.96 | 6 | 16 | 0 of 119 |
| F5, set A | 9.96 | 6 | 16 | 0 of 119 |
| F5, set B | 10.17 | 6 | 16 | 0 of 119 |
| F6 | 0.00 | 0 | 0 | 2 of 119 |
| F0 | 154.25 | 95 | 225 | 2 of 119 |
| F3 with DeepSeek's error | 9.96 | 6 | 16 | 0 of 119 |
| F3 with Haiku's error | 9.96 | 6 | 16 | 0 of 119 |
| F3 with Opus's error | 9.96 | 6 | 16 | 0 of 119 |
| F-room | 9.62 | 0 | 16 | 0 of 119 |
<!-- /table:m2_objects_off -->

The other yardsticks, on the official-arm stages alone:

<!-- table:m2_secondary_off -->
| Repeat | Stages | A = F1 minus F5 | B DeepSeek (X minus F5) | B Haiku (X minus F5) | B Opus (X minus F5) | C (X minus F5) | Verdicts (from X minus half of A) |
|---|---|---|---|---|---|---|---|
| `ig` alone | 117 | +0.260 [+0.230, +0.289] | -0.008 [-0.030, +0.015] | -0.002 [-0.021, +0.016] | -0.027 [-0.049, -0.006] | +0.025 [-0.015, +0.065] | B: not shown; C: not shown |
| Audit's U_cone | 119 | +0.530 [+0.447, +0.612] | +0.028 [-0.009, +0.065] | +0.021 [-0.033, +0.076] | -0.008 [-0.067, +0.052] | +0.160 [+0.075, +0.244] | B: not shown; C: not shown |
| U_360 | 119 | +0.311 [+0.263, +0.359] | +0.089 [+0.034, +0.145] | +0.080 [+0.006, +0.154] | +0.069 [-0.002, +0.143] | +0.180 [+0.080, +0.279] | B: not shown; C: inconclusive |
<!-- /table:m2_secondary_off -->

Counts. 384<!--n:m2_stages--> stages are usable and 0<!--n:m2_left_out--> are left out. F-room has 9.63<!--n:m2_froom_objects--> objects per member against 10.05<!--n:m2_f1_objects--> for F1, because 115<!--n:m2_froom_members--> of 2841<!--n:m2_members_total--> members had no unseen typed region (in 22<!--n:m2_froom_stages--> stages, and in 8<!--n:m2_froom_stages_all--> of them every member). No F3 member fell back to placebo objects (0<!--n:m2_fallback_deepseek-->, 0<!--n:m2_fallback_haiku--> and 0<!--n:m2_fallback_opus-->). F0 holds 151.45<!--n:m2_froom_f0_objects--> objects per member. The official-arm repeat uses 119<!--n:m2_official_stages--> stages from 7<!--n:m2_official_runs--> runs.

The registered biases:
- Toward "not shown sufficient": F1's objects are the very objects the yardstick counts.
- Toward "sufficient": F3 keeps the true labels; the error sample leaves out guesses with no unseen object of their class; and the nearest-object distance is a minimum, so common classes get short distances.
- The net direction is unknown.
- The yardstick U_wall failed part of its October check, and the rendered check that would test it (M6) is cut. Every M2 verdict is provisional.
- The error is measured on the semantic truth, while the moved objects are those of `oracle_sets.json`.

Readings where the frozen M2 file is silent (deviation 54): F0's "unmapped" objects are the yardstick's mask over both tracks; "the track's first F1 graph" is the first member id of that track; n_T enters F-room's draw as a proportion; the scene-by-seed clustering has only 6 clusters, so its interval is coarse.

## 9. Limits

- Two houses. Every verdict says nothing about other houses.
- The truth is a proxy for what the camera saw: HM3D annotations, not the robot's view.
- The replays are static: the model saw one saved stage. No live Claude run was made (E6 is cut).
- The scorer was written after DeepSeek's numbers were seen, and frozen before any Claude output was scored. The margin at L3 was set knowing the gap between Gemini and DeepSeek at 1 m.
- One Haiku member was dropped (1<!--n:status_haiku_dropped--> of 176<!--n:mem_haiku_n-->): its final text did not parse.
- The 8<!--n:frame_rows_gemini--> Gemini rows have no wrong-house partner, and Gemini's 3<!--n:gemini_clusters--> clusters leave its intervals unbounded.
- At L1 the contrasts rest on 24<!--n:l1_rows_haiku--> rows for Haiku, 41<!--n:l1_rows_opus--> for Opus and 42<!--n:l1_rows_deepseek--> for DeepSeek (exploratory), not 44<!--n:frame_rows-->.
- A worker's check script printed, before the first scoring run, whether one secondary readout (kept against removed guesses) lay inside or beyond the ±5<!--n:rule_valid_band-->-point band for DeepSeek, the placebo and Gemini. It printed no number, and the scorer was not changed in response (deviation 52).
- A guess labelled "stove" can never hit in either house under the frozen label rules (section 7).
- The close L3 verdict was checked again after the result was seen (deviation 55). The no-hint replay was run after it too (deviation 56).
- M2 is provisional: its yardstick failed part of its October check and the rendered check is cut.
- Cut, and said so in §15 of the pre-registration: the direct probe; the Sonnet replay; Haiku on all stages; the rendered "seen" check (M6); the decision replay with Claude's members (H5) and the validity layer's fifth readout; live Claude (E6); the uniform comparator and the one-house logistic prior; B4 inside the family's p-values; the member-vote likelihood-ratio test and the mass-per-region correlation.
- The prompt's hint check has 12<!--n:frame_round1--> rows and 48<!--n:nohint_members--> members.

## 10. What this lets the talk say

The registered outcome is "The claim fails<!--n:thesis-->": both Claude models are Rejected at L2 and at L3. In plain words, the intervals rule out a gain over the named comparator as large as the margin. The verdict alone does not say the models are worse; at L2 the interval does. This holds for two houses, on a truth that is a proxy for what the camera saw, on static replays, and says nothing about other houses. At L2 each model scores below the prior from 179<!--n:rule_houses--> other houses, and the interval lies wholly below zero. At L3 the difference from the model's own content traded across unobserved regions shows no detectable difference (intervals [-1.9<!--n:c_opus_L3_Dci_lo-->, +2.9<!--n:c_opus_L3_Dci_hi-->] for Opus and [-0.8<!--n:c_haiku_L3_Dci_lo-->, +2.4<!--n:c_haiku_L3_Dci_hi-->] for Haiku; the registered detectable difference, 1.1<!--n:mdd_L3_mdd--> points, comes from the placebo's contrast and is too small for these), and gains up to 2.95<!--n:p_opus_L3_D_hi2--> points for Opus and 2.36<!--n:p_haiku_L3_D_hi2--> for Haiku are not ruled out. Opus's interval ends 0.05<!--n:p_opus_L3_D_gap--> points below the margin. At L1 the contrasts rest on 41<!--n:l1_rows_opus--> rows for Opus, 24<!--n:l1_rows_haiku--> for Haiku and 42<!--n:l1_rows_deepseek--> for DeepSeek (exploratory), of 44<!--n:frame_rows-->. M2 does not show that right meaning is sufficient: on the primary yardstick every arm is "not shown sufficient, on a provisional yardstick".

## What it does not let the talk say

It does not say where the guesses sit. Supported at L3 would have meant beating the named comparators at placing content in the right unobserved region; no model did. It does not say the guesses reach the map. It does not say Claude's guesses are no better than random: Haiku scores +8.2<!--n:c_haiku_L2_B1_diff--> points above the placebo at L2 (p 0.014<!--n:c_haiku_L2_B1_p-->, one contrast, not adjusted). It does not use "equal", "did as well" or "failed to replicate". It does not speak for other houses, live runs, other models, or the paper's scale. It does not show that a language model cannot help exploration. It does not say M2's second half is settled: its yardstick is provisional and its net bias is unknown. The Opus verdict at L3 is close: the registered figure is 2.95<!--n:p_opus_L3_D_hi2--> against a margin of 3<!--n:c_opus_L3_margin-->, and the 15<!--n:rc_opus_below--> reruns stayed below it. A crossing would have made the thesis line "Inconclusive".
