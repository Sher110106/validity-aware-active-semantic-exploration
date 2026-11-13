# Part 3 results: are the model's guesses right in meaning?

Written 13 Nov 2026. Times are IST.

Every number here has a row in `numbers_part3.csv`, with its file and its path in that file. `build_numbers_part3.py` rebuilds the csv from the result files and fails if a table, or a number in the prose that carries its csv key in an HTML comment, no longer matches them. The tables sit between `<!-- table:name -->` markers: do not edit them by hand; run the script with `--fill`.

Every verdict below holds for two houses, on a truth that is a proxy for what the camera saw, on static replays.

## 1. What was tested

1. **The claim.** The ASP author says the model's guessed scene graphs sit in the wrong places but name the right things, and that this is enough for ASP. Part 3 tests the first half. M2 (section 8) tests the second.
2. **Three levels.** L1: does the model name room types that the house still holds, unseen and not yet mapped? L2: does it name object classes that the unseen part still holds? L3: does it put a new room or object in or near an unobserved region that has that type or holds that class?
3. **A hit.** An L1 or L2 claim hits if the house still holds that type or class, not yet mapped, in a region the robot has not seen. An L3 item hits if it lies inside an unobserved region of its type (or holding its class), or within 0.5<!--n:rule_reach_m--> m of one. Truth is the HM3D annotation of each house.
4. **The comparators.** At L1 and L2: B3, a prior built from 179<!--n:rule_houses--> other houses that makes the same number of claims as the model, and B1, a random placebo. At L3: B5, the model's own labels shuffled among its own items; D, the unobserved regions swapping what they hold; and B3L, the prior's labels put at the model's places. The comparator named for a verdict is B3 at L1 and L2 and D at L3.
5. **The family and the margins.** Two Claude models at three levels make 6<!--n:rule_hypotheses--> hypotheses, tested with Holm's correction at α = 0.05<!--n:rule_alpha-->. The unit is the cluster (scene × seed × arm); the test is the exact one-sided sign-flip test. The margin is 5<!--n:c_opus_L1_margin--> points at L1 and L2 and 3<!--n:c_opus_L3_margin--> points at L3.

**Verdict names.** *Supported*: the Holm-adjusted p is below 0.05<!--n:rule_alpha-->. *Rejected*: not Supported, and the upper end of the 95% interval for (model minus named comparator) lies below the margin. In plain words, the model did not beat the named comparator by the margin; it does not say the model is worse, so read the interval. *Inconclusive*: anything else.

## 2. How it was run

- **The frame.** 44<!--n:frame_rows--> rows in 12<!--n:frame_clusters--> clusters. 36<!--n:frame_rows_runs--> rows are stages 3, 8 and 13<!--n:frame_stages--> of 12<!--n:frame_runs--> saved DeepSeek runs (houses 00853 and 00871). 8<!--n:frame_rows_gemini--> rows are the inputs Gemini saw in October.
- **The models.** Claude Opus 5.5 and Claude Haiku 5.5, the blind, confirmatory test. Effort medium, 4<!--n:rule_members--> members per row, at most 50<!--n:rule_turns--> turns, `max_tokens` 64,000<!--n:rule_max_tokens-->, no temperature, no seed, no fallback model. The prompt, the collision tool and the parser are the author's. The rows came in 4<!--n:rounds_used--> rounds, and both models finished all of them.
- **The members.** 352<!--n:mem_total--> members, 176<!--n:mem_opus_n--> for each model. Opus: 176<!--n:status_opus_ok--> scored, 0<!--n:status_opus_dropped--> dropped. Haiku: 175<!--n:status_haiku_ok--> scored and 1<!--n:status_haiku_dropped--> dropped (row `e2_00871_s43_filter_st03`, member 3). Its final text did not parse (1<!--n:mem_haiku_parse_fail--> member); it was not refused and did not reach the turn limit. A member makes 2.35<!--n:mem_opus_calls--> calls (Opus) or 2.52<!--n:mem_haiku_calls--> (Haiku) on average, and 8.9<!--n:mem_opus_tools--> or 6.2<!--n:mem_haiku_tools--> collision checks.
- **Spend.** The replays cost $35.78<!--n:spend_replay-->: Opus $34.68<!--n:spend_replay_opus-->, Haiku $1.10<!--n:spend_replay_haiku-->. The caps were $280<!--n:rule_cap_opus--> and $20<!--n:rule_cap_haiku-->. The smoke test cost $2.84<!--n:spend_smoke--> and the no-hint replay $0.30<!--n:spend_nohint-->. The three ledgers sum to $38.92<!--n:spend_all-->. Prices come from the price card bundled with the tools, not from the live page.
- **Order of events** (13 Nov).
  - 18:59<!--n:t_prereg_hash-->: we hash the pre-registration (sha256 59c97ad6<!--n:hash_prereg-->…) and push it at 19:00<!--n:t_prereg_push-->.
  - 19:15<!--n:t_m2_hash-->: we hash the M2 pre-registration.
  - 19:25<!--n:t_cost_hash-->: we hash the cost addendum. The replay starts at 19:25<!--n:t_replay_start-->.
  - 20:12<!--n:t_truth_hash-->: we hash the truth files, label table and frame.
  - 20:13<!--n:t_exploratory-->: the first scoring run, on DeepSeek, Gemini and the placebo.
  - 20:14<!--n:t_freeze-->: we freeze the scorer (freeze file sha256 7d9c3822<!--n:hash_freeze-->…) and push it. No Claude output has been scored.
  - 20:38<!--n:t_replay_end-->: the replay ends.
  - 20:41<!--n:t_scored-->: we score the Claude outputs once, with the frozen scorer.
  - 20:50<!--n:t_nohint-->: the no-hint replay runs, after we knew the result (deviation 56). 21:10<!--n:t_margin_check-->: the margin check of section 3 runs, also after we knew the result (deviation 55).

**Points the frozen files left open** (deviations 51, 52 and 54; all settled before the scorer ran on any model output).
- A result can meet two thesis rows. The rows apply in the table's order.
- A new room typed "dining" is left out of L3 as well as L1, and counted.
- Names ending in beam, column or pillar map to a structure class. No score changes.
- The share of items that reach two regions is given twice: over all regions and over unobserved regions only.
- The paper's room test and the 2-of-8 view are given over all stages and over stages that hold 8 members.
- The prior that knows the house's size has three sensitivity lines: seen counts, size, and both.
- On a replay, "before it is seen" uses the states of the run the row came from.
- M2's silent points are listed in section 8.

## 3. The confirmatory result

The score is the model's mean hit rate over clusters. A difference is the model minus the comparator, in points, on the rows where both sides have a score, so the rows can differ from the score's. At L1 the Opus differences rest on 41<!--n:l1_rows_opus--> rows and the Haiku differences on 24<!--n:l1_rows_haiku--> of 44<!--n:frame_rows-->: a model with no typed new room in a row has no L1 score there, and 2<!--n:l1_impossible_opus--> rows have no open room type at all. p is one-sided: the chance that a difference this large or larger arises if the model were no better than the comparator. "Largest p" is the largest over the hypothesis's comparators.

**L1 and L2.**

<!-- table:conf_l12 -->
| Hypothesis | Score | Placebo's own score | Diff vs B3 (p) | Diff vs B1 placebo (p) | 95% interval vs B3 | Margin (points) | Largest p | Holm p | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Opus L1 | 85.4% | 87.5% | -5.8 (p 1.000) | -2.1 (p 0.727) | [-12.2, 0.0] | 5 | 1.000 | 1.000 | Rejected |
| Haiku L1 | 89.6% | 87.5% | -10.4 (p 1.000) | -5.2 (p 0.859) | [-20.8, 0.0] | 5 | 1.000 | 1.000 | Rejected |
| Opus L2 | 58.3% | 60.6% | -35.1 (p 1.000) | -2.3 (p 0.830) | [-41.3, -29.1] | 5 | 1.000 | 1.000 | Rejected |
| Haiku L2 | 68.8% | 60.6% | -24.9 (p 1.000) | +8.2 (p 0.014) | [-31.5, -18.1] | 5 | 1.000 | 1.000 | Rejected |
<!-- /table:conf_l12 -->

**L3.** The placebo is not a comparator at L3; its own score stands beside the model's.

<!-- table:conf_l3 -->
| Hypothesis | Score | Placebo's own score | Diff vs B5 (p) | Diff vs D (p) | Diff vs B3L (p) | 95% interval vs D | Margin (points) | Largest p | Holm p | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| Opus L3 | 4.2% | 1.7% | -0.2 (p 0.601) | +0.5 (p 0.326) | -6.3 (p 1.000) | [-1.9, +2.9] | 3 | 1.000 | 1.000 | Rejected |
| Haiku L3 | 4.4% | 1.7% | -0.5 (p 0.901) | +0.8 (p 0.150) | -5.8 (p 1.000) | [-0.8, +2.4] | 3 | 1.000 | 1.000 | Rejected |
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

**The independent recompute.** A checker wrote its own code from the pre-registration text, without opening the scorer. For both Claude models and DeepSeek, every count of claims, items and hits matches the scorer. The differences against the prior, the placebo and the prior's labels match to the last digit, and the p-values match exactly. The two randomised controls, B5 and D, match within the noise of their draws. The six verdicts and the thesis line match.

**The one close verdict.** Opus at L3 is Rejected because the upper end of its interval against D is 2.95<!--n:p_opus_L3_D_hi2--> points, and the margin is 3<!--n:c_opus_L3_margin-->: the gap is 0.05<!--n:p_opus_L3_D_gap--> points. D is a randomised control, so its draws move that end. After the result was known, the checker reran D with 10<!--n:rc_opus_runs200--> other seeds at the registered 200<!--n:rc_opus_draws_lo--> draws and 5<!--n:rc_opus_runs5000--> seeds at 5000<!--n:rc_opus_draws_hi--> draws. The upper end ran from 2.83<!--n:rc_opus_hi_min--> to 2.98<!--n:rc_opus_hi_max--> points, below 3<!--n:c_opus_L3_margin--> in 15<!--n:rc_opus_below--> of 15<!--n:rc_opus_below--> runs. A seed that crossed 3<!--n:c_opus_L3_margin--> would have made Opus at L3 Inconclusive, and the thesis line Inconclusive. This check was made after the result was seen (deviation 55). The registered figure, 2.95<!--n:p_opus_L3_D_hi2-->, is the one reported. Haiku's upper end is 2.36<!--n:p_haiku_L3_D_hi2-->, 0.64<!--n:p_haiku_L3_D_gap--> points below the margin; over its 15<!--n:rc_haiku_below--> reruns it ran from 2.30<!--n:rc_haiku_hi_min--> to 2.45<!--n:rc_haiku_hi_max-->.

## 4. What the table shows, and what it does not

At L1 and L2 each Claude model scores below the prior built from 179<!--n:rule_houses--> other houses, which makes the same number of claims as the model; at L2 the difference is -35.1<!--n:c_opus_L2_B3_diff--> points for Opus and -24.9<!--n:c_haiku_L2_B3_diff--> for Haiku. At L3 the comparison is with the model's own content traded across unobserved regions (D): the differences are +0.5<!--n:c_opus_L3_D_diff--> points for Opus and +0.8<!--n:c_haiku_L3_D_diff--> for Haiku, both intervals include zero, and the data show no detectable difference (the frozen detectable difference is 1.1<!--n:mdd_L3_mdd--> points; the intervals' half-widths are 2.4<!--n:p_opus_L3_D_hw--> and 1.6<!--n:p_haiku_L3_D_hw-->). The table does not show that the guesses reach the map: L3 hit rates are 4.2%<!--n:c_opus_L3_score--> for Opus and 4.4%<!--n:c_haiku_L3_score--> for Haiku, in two houses, on a proxy truth, on static replays.

Two facts weigh against the main result.
1. Opus at L3 is 0.05<!--n:p_opus_L3_D_gap--> points inside the margin: its interval's upper end is 2.95<!--n:p_opus_L3_D_hi2--> points against a margin of 3<!--n:c_opus_L3_margin-->. The reruns of section 3 stayed below 3<!--n:c_opus_L3_margin-->, but one crossing would have changed the verdict.
2. A Claude model beats the placebo once. Haiku at L2 scores +8.2<!--n:c_haiku_L2_B1_diff--> points above B1 (p 0.014<!--n:c_haiku_L2_B1_p-->, not adjusted). It does not lift the hypothesis: the hypothesis's p is the largest over B3 and B1, and B3 gives 1.000<!--n:c_haiku_L2_B3_p-->. Opus at L2 differs from B1 by -2.3<!--n:c_opus_L2_B1_diff--> points (p 0.830<!--n:c_opus_L2_B1_p-->): no detectable difference, the detectable difference being 5.2<!--n:mdd_L2_mdd--> points.

## 5. The detectable differences

The frozen table (written before any Claude output was scored) comes from the placebo's own members: the standard deviation across clusters of B1 minus B3 at L1 and L2, and of B5 minus D at L3.

<!-- table:mdd -->
| Level | Contrast | Clusters | SD of the contrast (points) | Detectable difference (points) | Margin (points) | Interval half-width (points) |
|---|---|---|---|---|---|---|
| L1 | B1-B3 | 12 | 6.1 | 5.7 | 5 | 3.8 |
| L2 | B1-B3 | 12 | 5.6 | 5.2 | 5 | 3.6 |
| L3 | B5-D | 12 | 1.2 | 1.1 | 3 | 0.7 |
<!-- /table:mdd -->

What they mean for reading "Rejected":
- A null is worded "no detectable difference", with the detectable difference beside it: 5.7<!--n:mdd_L1_mdd--> points at L1, 5.2<!--n:mdd_L2_mdd--> at L2, 1.1<!--n:mdd_L3_mdd--> at L3. All three levels can decide at 44<!--n:frame_rows--> inputs.
- The interval half-width is below the margin at each level (3.8<!--n:mdd_L1_hw--> against 5<!--n:mdd_L1_delta-->, 3.6<!--n:mdd_L2_hw--> against 5<!--n:mdd_L2_delta-->, 0.7<!--n:mdd_L3_hw--> against 3<!--n:mdd_L3_delta-->), so "Rejected" was within reach at each.
- At L2 the upper ends against B3 are -29.1<!--n:p_opus_L2_B3_hi--> (Opus) and -18.1<!--n:p_haiku_L2_B3_hi--> (Haiku) points: there "Rejected" means the model scores below the prior. At L1 the upper ends are 0.0<!--n:p_opus_L1_B3_hi--> and 0.0<!--n:p_haiku_L1_B3_hi-->: no gain over the prior shows, and the lower ends are well below zero.
- At L3 the intervals cross zero. "Rejected" there says that no gain as large as 3<!--n:c_opus_L3_margin--> points can be shown. A gain between 1.1<!--n:mdd_L3_mdd--> and 3<!--n:c_opus_L3_margin--> points would not be called a win, and it would not be ruled out either. Shuffling the model's labels (B5) or trading them across regions (D) moves its L3 score by -0.2<!--n:c_opus_L3_B5_diff--> and +0.5<!--n:c_opus_L3_D_diff--> points for Opus and -0.5<!--n:c_haiku_L3_B5_diff--> and +0.8<!--n:c_haiku_L3_D_diff--> for Haiku: no detectable difference. The Claude intervals against D are wider than the frozen half-width of 0.7<!--n:mdd_L3_hw--> points, because a model's contrast with D varies more than the placebo's.
- Haiku's L1 result rests on few claims (48<!--n:claims_haiku_l1--> claims, against 147<!--n:claims_opus_l1--> for Opus).

## 6. Exploratory results: DeepSeek, Gemini and the placebo

These are exploratory. The scorer was written after DeepSeek's numbers were seen. Each model has its own Holm family of three hypotheses; no thesis line applies. DeepSeek has 160<!--n:deepseek_members--> members on the 44<!--n:frame_rows--> rows (some failed in October); Gemini has 29<!--n:gemini_members--> members on its 8<!--n:gemini_rows--> rows, in 3<!--n:gemini_clusters--> clusters.

**L1 and L2.**

<!-- table:exp_l12 -->
| Hypothesis | Clusters | Score | Placebo's own score | Diff vs B3 (p) | Diff vs B1 placebo (p) | 95% interval vs B3 | Margin (points) | Largest p | Holm p | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| DeepSeek L1 | 12 | 89.2% | 87.5% | -1.7 (p 1.000) | +1.7 (p 0.301) | [-5.2, 0.0] | 5 | 1.000 | 1.000 | Rejected |
| Gemini L1 | 3 | 100.0% | 87.5% | 0.0 (p 1.000) | 0.0 (p 1.000) | unbounded | 5 | 1.000 | 1.000 | Inconclusive |
| Placebo L1 | 12 | 87.5% | 87.5% | -4.9 (p 1.000) | n/a | [-8.3, -0.8] | 5 | 1.000 | 1.000 | Rejected |
| DeepSeek L2 | 12 | 66.4% | 60.6% | -26.3 (p 1.000) | +5.8 (p 0.024) | [-33.2, -19.4] | 5 | 1.000 | 1.000 | Rejected |
| Gemini L2 | 3 | 88.1% | 60.6% | -10.5 (p 1.000) | +22.7 (p 0.125) | unbounded | 5 | 1.000 | 1.000 | Inconclusive |
| Placebo L2 | 12 | 60.6% | 60.6% | -32.6 (p 1.000) | n/a | [-36.2, -29.1] | 5 | 1.000 | 1.000 | Rejected |
<!-- /table:exp_l12 -->

**L3.**

<!-- table:exp_l3 -->
| Hypothesis | Clusters | Score | Placebo's own score | Diff vs B5 (p) | Diff vs D (p) | Diff vs B3L (p) | 95% interval vs D | Margin (points) | Largest p | Holm p | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DeepSeek L3 | 12 | 4.8% | 1.7% | -0.6 (p 0.925) | -0.6 (p 0.852) | -4.8 (p 0.998) | [-1.9, +0.6] | 3 | 0.998 | 1.000 | Rejected |
| Gemini L3 | 3 | 9.9% | 1.7% | -1.3 (p 1.000) | +0.4 (p 0.500) | -3.2 (p 1.000) | unbounded | 3 | 1.000 | 1.000 | Inconclusive |
| Placebo L3 | 12 | 1.7% | 1.7% | -0.1 (p 0.634) | -0.2 (p 0.739) | -4.1 (p 1.000) | [-1.0, +0.5] | 3 | 1.000 | 1.000 | Rejected |
<!-- /table:exp_l3 -->

**The wrong-house gate.** The 8<!--n:frame_rows_gemini--> Gemini rows have no partner house, so there is no gate for Gemini.

<!-- table:gate_exp -->
| Row | Mean difference (points) | Pairs | p | Passes |
|---|---|---|---|---|
| DeepSeek L1 | -1.7 | 6 | 1.000 | no |
| Gemini L1 | none | 0 | n/a | no |
| DeepSeek L2 | -5.3 | 6 | 1.000 | no |
| Gemini L2 | none | 0 | n/a | no |
<!-- /table:gate_exp -->

- DeepSeek is Rejected at all three levels. Against the placebo it scores +5.8<!--n:e_deepseek_L2_B1_diff--> points at L2 (p 0.024<!--n:e_deepseek_L2_B1_p-->, not adjusted).
- Gemini has 3<!--n:gemini_clusters--> clusters, so its intervals are unbounded and its verdicts are Inconclusive at all three levels. Its differences are for reading only.
- The placebo, scored as a model, is Rejected at all three levels. The verdict names a failure to beat the named comparator and says nothing more. B1 is itself, so it has no B1 contrast.

## 7. The secondary readouts

No verdict rests on these. Nothing is corrected for the number of looks. Each view is scored against comparators built under the same view.

**Claims behind the scores.** The count of claims and items each model made, over the rows it has.

<!-- table:claims -->
| Model | Members scored | Rows with an L1 score | L1 claims | L2 claims | L3 items |
|---|---|---|---|---|---|
| Opus | 176 | 42 | 147 | 1279 | 1495 |
| Haiku | 175 | 25 | 48 | 819 | 942 |
| DeepSeek | 160 | 44 | 181 | 1546 | 2046 |
| Gemini | 29 | 8 | 36 | 294 | 385 |
| Placebo | 176 | 44 | 221 | 1224 | 1942 |
<!-- /table:claims -->

**L1 and L2 under other rules.** *Looser rule*: a hit needs only an unseen region of the type, or one holding the class, mapped or not. *Detector words only*: the L2 classes in the detector's 52<!--n:rule_vocab-->-word vocabulary. *Without extended table*: "answers to" uses `synonym_primary` alone. Under the looser rule no member's score changed (0<!--n:loose_diff_opus--> of 176<!--n:loose_n_opus--> Opus members, 0<!--n:loose_diff_haiku--> of 175<!--n:loose_n_haiku--> Haiku, 0<!--n:loose_diff_deepseek--> of 160<!--n:loose_n_deepseek--> DeepSeek), so its rows repeat the primary rows: in these two houses the two rules find the same hits. A one-off check of the truth sets shows why: the looser sets differ from the primary ones in two of the frame's rows, both by the class "fridge" alone, and in no row by a room type; no member guessed a new fridge in those two rows. Two facts from the scorer's notes. A guess labelled "stove" can never hit in either house under the frozen label rules: in 00853 the annotation "oven and stove" answers to "oven", and in 00871 "stovetop" answers to "gas stove". In the view without the extended table, a bed answers only to "bed", and no detector "duvet" maps a bed.

<!-- table:sec_l1l2 -->
| Reading | Score | Diff vs B3 [interval] | Diff vs B1 placebo [interval] |
|---|---|---|---|
| Looser rule, Opus L1 | 85.4% | -5.8 [-12.2, 0.0] | -2.1 [-9.7, +4.2] |
| Looser rule, Opus L2 | 58.3% | -35.1 [-41.3, -29.1] | -2.3 [-7.4, +2.7] |
| Looser rule, Haiku L1 | 89.6% | -10.4 [-20.8, 0.0] | -5.2 [-16.2, +5.2] |
| Looser rule, Haiku L2 | 68.8% | -24.9 [-31.5, -18.1] | +8.2 [+1.1, +14.9] |
| Looser rule, DeepSeek L1 | 89.2% | -1.7 [-5.2, 0.0] | +1.7 [-4.2, +7.5] |
| Looser rule, DeepSeek L2 | 66.4% | -26.3 [-33.2, -19.4] | +5.8 [+0.1, +11.4] |
| Detector words only, Opus L2 | 78.9% | -15.1 [-26.8, -5.1] | +7.0 [-0.5, +14.0] |
| Detector words only, Haiku L2 | 84.4% | -9.5 [-15.4, -3.7] | +12.4 [+1.7, +23.1] |
| Detector words only, DeepSeek L2 | 74.9% | -18.7 [-28.9, -8.6] | +3.0 [+0.3, +5.7] |
| Without extended table, Opus L2 | 58.4% | -27.3 [-33.8, -21.7] | -2.9 [-8.5, +2.4] |
| Without extended table, Haiku L2 | 66.5% | -16.9 [-26.2, -6.9] | +5.2 [-2.0, +12.4] |
| Without extended table, DeepSeek L2 | 65.5% | -19.6 [-25.1, -13.9] | +4.2 [-0.9, +9.2] |
<!-- /table:sec_l1l2 -->

**L3 under other rules.** *Partly seen regions* replace the unobserved ones. The partly seen view leaves out rows with no such region.

<!-- table:sec_l3 -->
| Reading | Score | Rows with no region (left out) | Diff vs B5 [interval] | Diff vs D [interval] | Diff vs B3L [interval] |
|---|---|---|---|---|---|
| Partly seen regions, Opus | 3.1% | 17 | +0.7 [-0.3, +2.1] | +2.9 [-2.8, +12.9] | -1.0 [-2.3, 0.0] |
| Partly seen regions, Haiku | 3.4% | 17 | -0.4 [-1.4, +0.3] | +3.9 [-2.3, +13.3] | -4.7 [-13.6, +1.6] |
| Partly seen regions, DeepSeek | 1.8% | 17 | -0.6 [-1.4, +0.1] | +0.8 [-2.0, +3.9] | -2.7 [-7.0, 0.0] |
| Detector words only, Opus | 4.4% | 0 | -1.1 [-3.4, +1.0] | +0.2 [-3.3, +3.8] | -6.3 [-11.4, -1.4] |
| Detector words only, Haiku | 5.8% | 0 | -0.7 [-2.1, +0.6] | +0.9 [-2.0, +3.9] | -5.5 [-8.8, -2.4] |
| Detector words only, DeepSeek | 6.1% | 0 | -1.3 [-2.5, -0.2] | -0.2 [-1.7, +1.3] | -5.1 [-9.0, -1.2] |
| Without extended table, Opus | 4.2% | 0 | -0.2 [-1.8, +1.2] | +0.5 [-1.9, +3.0] | -5.1 [-8.0, -2.4] |
| Without extended table, Haiku | 4.4% | 0 | -0.4 [-1.2, +0.3] | +0.8 [-0.8, +2.5] | -5.2 [-9.0, -1.9] |
| Without extended table, DeepSeek | 4.8% | 0 | -0.5 [-1.4, +0.4] | -0.6 [-1.8, +0.7] | -4.6 [-7.5, -1.7] |
<!-- /table:sec_l3 -->

Clusters behind the partly seen contrasts (of 12<!--n:frame_clusters-->):

<!-- table:sec_partly_n -->
| Row | Clusters vs B5 | Clusters vs D |
|---|---|---|
| Opus | 10 | 7 |
| Haiku | 10 | 7 |
| DeepSeek | 10 | 7 |
<!-- /table:sec_partly_n -->

**The prior under three sensitivity forms** (diff vs the prior, in points).

<!-- table:sec_prior -->
| Row | B3 (registered) | B3 with seen counts | B3 with house size | B3 with both |
|---|---|---|---|---|
| Opus L1 | -5.8 [-12.2, 0.0] | -9.0 [-16.9, -1.4] | -5.8 [-12.2, 0.0] | -11.8 [-21.6, -2.1] |
| Haiku L1 | -10.4 [-20.8, 0.0] | -10.4 [-20.8, 0.0] | -10.4 [-20.8, 0.0] | -10.4 [-20.8, 0.0] |
| DeepSeek L1 | -1.7 [-5.2, 0.0] | -5.2 [-11.7, 0.0] | -1.7 [-5.2, 0.0] | -8.0 [-18.3, 0.0] |
| Opus L2 | -35.1 [-41.3, -29.1] | -33.7 [-40.0, -27.6] | -34.7 [-41.3, -28.2] | -33.4 [-39.0, -28.0] |
| Haiku L2 | -24.9 [-31.5, -18.1] | -24.4 [-29.9, -18.6] | -24.8 [-31.8, -17.7] | -22.8 [-28.8, -16.2] |
| DeepSeek L2 | -26.3 [-33.2, -19.4] | -24.6 [-31.2, -18.0] | -25.2 [-31.1, -19.2] | -23.9 [-29.3, -18.4] |
<!-- /table:sec_prior -->

**One claim for one region, rooms and objects apart.** The comparison is with the placebo.

<!-- table:x_misc -->
| Readout | Model | Model's share | Placebo's share | Diff vs placebo [interval] | p |
|---|---|---|---|---|---|
| L1, one claim to one region | Opus | 85.4% | 78.2% | +7.2 [-2.2, +16.5] | 0.057 |
| L1, one claim to one region | Haiku | 89.6% | 78.2% | +5.2 [-7.8, +18.8] | 0.216 |
| L1, one claim to one region | DeepSeek | 88.3% | 78.2% | +10.1 [+3.6, +16.5] | 0.004 |
| L3, rooms only | Opus | 16.7% | 2.7% | +13.9 [+1.4, +27.1] | 0.016 |
| L3, rooms only | Haiku | 6.0% | 2.7% | +2.1 [-7.3, +11.1] | 0.359 |
| L3, rooms only | DeepSeek | 5.9% | 2.7% | +3.1 [-3.0, +9.6] | 0.164 |
| L3, objects only | Opus | 3.1% | 1.5% | +1.6 [-1.0, +4.4] | 0.122 |
| L3, objects only | Haiku | 4.3% | 1.5% | +2.8 [-0.2, +6.0] | 0.034 |
| L3, objects only | DeepSeek | 4.8% | 1.5% | +3.3 [+0.9, +5.7] | 0.006 |
<!-- /table:x_misc -->

**Items that reach two regions.** The share of L3 items that reach two or more regions.

<!-- table:x_multi -->
| Readout | Model | Model's share | Placebo's share | Diff vs placebo [interval] | p |
|---|---|---|---|---|---|
| Share reaching two or more regions | Opus | 26.2% | 22.8% | +3.4 [-1.6, +8.6] | 0.089 |
| Share reaching two or more regions | Haiku | 25.1% | 22.8% | +2.3 [-4.5, +9.2] | 0.233 |
| Share reaching two or more regions | DeepSeek | 23.7% | 22.8% | +1.0 [-5.1, +6.9] | 0.361 |
| Share reaching two or more unobserved regions | Opus | 3.8% | 0.6% | +3.2 [+0.1, +6.4] | 0.021 |
| Share reaching two or more unobserved regions | Haiku | 3.2% | 0.6% | +2.6 [-0.4, +6.0] | 0.051 |
| Share reaching two or more unobserved regions | DeepSeek | 4.3% | 0.6% | +3.7 [+0.7, +6.9] | 0.005 |
<!-- /table:x_multi -->

**L4.** The share of new objects within a distance of an unmapped reference object of their class in an unseen region.

<!-- table:x_l4 -->
| Readout | Model | Model's share | Placebo's share | Diff vs placebo [interval] | p |
|---|---|---|---|---|---|
| Within 0.5 m | Opus | 0.2% | 0.2% | 0.0 [-0.2, +0.2] | 0.562 |
| Within 0.5 m | Haiku | 0.4% | 0.2% | +0.2 [-0.3, +0.9] | 0.406 |
| Within 0.5 m | DeepSeek | 0.5% | 0.2% | +0.3 [0.0, +0.8] | 0.062 |
| Within 1 m | Opus | 0.7% | 0.7% | +0.1 [-0.7, +0.9] | 0.404 |
| Within 1 m | Haiku | 1.1% | 0.7% | +0.5 [-0.7, +1.7] | 0.201 |
| Within 1 m | DeepSeek | 2.1% | 0.7% | +1.4 [+0.2, +2.8] | 0.015 |
| Within 2 m | Opus | 3.1% | 1.9% | +1.2 [-0.6, +3.2] | 0.111 |
| Within 2 m | Haiku | 5.9% | 1.9% | +4.0 [+0.4, +7.9] | 0.016 |
| Within 2 m | DeepSeek | 5.0% | 1.9% | +3.1 [+1.6, +4.9] | <0.001 |
| Within 3 m | Opus | 6.1% | 5.2% | +0.9 [-2.2, +4.1] | 0.271 |
| Within 3 m | Haiku | 9.5% | 5.2% | +4.3 [-0.1, +9.0] | 0.027 |
| Within 3 m | DeepSeek | 8.7% | 5.2% | +3.6 [+0.6, +6.6] | 0.010 |
<!-- /table:x_l4 -->

**Labels that are "other" or structure, untyped rooms, and new objects with and without the `is_predicted` flag.** [NOT IN A RESULT FILE. The scorer counts them in its dry mode and does not save them. They stay out of this text until `run_semantic.py` writes them to `results.json`.]

**The placement-error sample** (the input to M2's F3): the distance from each new object to the nearest unmapped object of its class in an unseen region. A guess with no such object is left out.

<!-- table:err -->
| Model | Distances | Guesses left out | Median (m) |
|---|---|---|---|
| Opus | 800 | 548 | 8.12 |
| Haiku | 617 | 277 | 7.13 |
| DeepSeek | 1249 | 610 | 7.67 |
| Gemini | 314 | 35 | 5.81 |
| Placebo | 1030 | 630 | 8.95 |
<!-- /table:err -->

**The paper's room test.** A region not seen at stage 0 counts as predicted before it is found if, at some stage before it is seen, at least 2<!--n:rule_room_k--> of the members put a new room within 2.5<!--n:rule_room_m--> m of its centre. The paper's figure is below. The placebo arm gives the chance rate: 8.7%<!--n:room_live_placebo_all_stages_typed_rate--> of its regions typed, 58.0%<!--n:room_live_placebo_all_stages_untyped_rate--> untyped, over all stages.

<!-- table:room_paper -->
| Source | Regions | Predicted before found |
|---|---|---|
| The paper | 28 | 9 |
<!-- /table:room_paper -->

*Live runs (DeepSeek, 8 members at most; the placebo arm is the chance rate).*

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
| DeepSeek | 171 | 11 | 46 | 7 | 28 |
| Gemini | 33 | 3 | 8 | 2 | 7 |
| Placebo | 171 | 8 | 40 | 2 | 15 |
<!-- /table:room_replay -->

**The validity layer.** The validator is the E2 filter. First, the share of guesses it removes, by reason.

<!-- table:val_removed -->
| Model | Guesses | Removed | Share removed | Box conflict | Impassable crossing | Object parent |
|---|---|---|---|---|---|---|
| Opus | 1553 | 132 | 8.5% | 22 | 110 | - |
| Haiku | 989 | 200 | 20.2% | 70 | 130 | - |
| DeepSeek | 2070 | 663 | 32.0% | 527 | 124 | 12 |
<!-- /table:val_removed -->

Second, kept against removed guesses, in points, with the registered reading. The reading is "no detectable difference" only when the interval lies within ±5<!--n:rule_valid_band--> points; otherwise the interval is too wide to read.

<!-- table:val_kept -->
| Row | Rows | Clusters | Kept minus removed [interval] | Reading |
|---|---|---|---|---|
| Opus L2 | 17 | 10 | -4.3 [-25.6, +18.7] | interval reaches beyond ±5 points |
| Haiku L2 | 36 | 12 | -3.4 [-12.7, +7.8] | interval reaches beyond ±5 points |
| DeepSeek L2 | 43 | 12 | +0.4 [-4.7, +6.1] | interval reaches beyond ±5 points |
| Opus L3 | 32 | 12 | -12.6 [-28.4, +1.0] | interval reaches beyond ±5 points |
| Haiku L3 | 37 | 12 | +0.1 [-4.7, +4.7] | no detectable difference |
| DeepSeek L3 | 43 | 12 | -0.1 [-2.3, +2.0] | no detectable difference |
<!-- /table:val_kept -->

Third, member support against L3 truth: Brier score and expected calibration error (ECE) of the raw support, then with an isotonic calibrator fitted on one house and tested on the other.

<!-- table:val_reliab -->
| Model | Items | Brier | ECE |
|---|---|---|---|
| Opus | 1495 | 0.257 | 0.379 |
| Haiku | 942 | 0.136 | 0.248 |
| DeepSeek | 2046 | 0.166 | 0.275 |
<!-- /table:val_reliab -->

The calibrator is fitted on one house and tested on the other:

<!-- table:val_cross -->
| Model and test house | Brier, raw support | Brier, calibrated | ECE, raw support | ECE, calibrated |
|---|---|---|---|---|
| Opus, tested on 00853 | 0.273 | 0.028 | 0.426 | 0.063 |
| Opus, tested on 00871 | 0.239 | 0.080 | 0.330 | 0.061 |
| Haiku, tested on 00853 | 0.157 | 0.056 | 0.257 | 0.040 |
| Haiku, tested on 00871 | 0.116 | 0.044 | 0.239 | 0.013 |
| DeepSeek, tested on 00853 | 0.175 | 0.051 | 0.286 | 0.005 |
| DeepSeek, tested on 00871 | 0.156 | 0.055 | 0.264 | 0.005 |
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
| DeepSeek 0.25 | 1626 | 6.3% |
| DeepSeek 0.50 | 248 | 2.4% |
| DeepSeek 0.75 | 99 | 6.1% |
| DeepSeek 1.00 | 73 | 1.4% |
<!-- /table:val_curve -->

Fourth, guesses kept and hits kept at each vote level.

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
| DeepSeek, raw | 2070 | 1039 | 1546 | 115 | 2046 |
| DeepSeek, validator | 1407 | 730 | 1095 | 77 | 1396 |
| DeepSeek, validator + vote 0.5 | 292 | 153 | 196 | 7 | 292 |
| DeepSeek, validator + vote 0.75 | 113 | 35 | 44 | 4 | 113 |
| DeepSeek, validator + vote 1.0 | 40 | 1 | 1 | 0 | 40 |
<!-- /table:val_votes -->

**The prompt's hint (exploratory).** Haiku on the 12<!--n:frame_round1--> round-1 rows with the sentence "Scene may contain more than one bedroom and more than one bathroom" removed: 48<!--n:nohint_members--> members, all parsed, $0.30<!--n:spend_nohint-->. It ran after the confirmatory result was known (deviation 56). The hinted figures are the same 12<!--n:frame_round1--> rows of the confirmatory run. Rows with no L1 claim have no L1 score, so the row sets differ. The no-hint run's own results file gives the same L1 score (87.5%<!--n:nohint_file_score-->). The counts are small and decide nothing.

<!-- table:nohint -->
| Run | Rows with an L1 score | L1 claims | L1 hits | L1 score (mean of row scores) | Members with a claim |
|---|---|---|---|---|---|
| With the hint | 6 | 9 | 5 | 66.7% | 9 |
| Without the hint | 8 | 12 | 11 | 87.5% | 12 |
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

M2 is descriptive, not blind; its reading rule was set in advance (pre-registration sha256 5b8a8400<!--n:m2_prereg_hash-->…). It reads ASP's own viewpoint score on 384<!--n:m2_stages--> bench stages from 24<!--n:m2_runs--> runs, and uses the Spearman correlation between the score and a yardstick of unmapped objects a candidate could see. F1 holds the true guesses, F5 the placebo, F6 none, F0 every true unmapped object, F3 the true objects moved by a model's placement error (its median error sits beside its row), and F-room only objects typical of each unseen region's type.

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

Every M2 verdict is "not shown sufficient, on a provisional yardstick". No arm comes near the half of A that the rule asks for. F3 with Haiku's error differs from F5 by -0.006<!--n:m2_B_haiku_mean--> and with Opus's error by -0.029<!--n:m2_B_opus_mean-->: the Haiku interval includes 0 and the Opus interval lies below it. F-room differs from F5 by +0.024<!--n:m2_C_mean-->. F0 differs from F5 by -0.017<!--n:m2_F0F5_mean-->: it is an identity, not a finding, because members that hold the same guesses leave the score to distance alone, and `ig` is 0 for every candidate in 2<!--n:m2_f0_ig_zero--> of 384<!--n:m2_f0_ig_zero_of--> stages (0.5%<!--n:m2_f0_ig_zero_share-->). No correction was made for running F3 for 3<!--n:rule_f3_models--> models.

Repeats on other yardsticks and subsets. Where a cell says "not shown", read "not shown sufficient, on a provisional yardstick".

<!-- table:m2_secondary -->
| Repeat | Stages | A | B DeepSeek | B Haiku | B Opus | C | Verdicts |
|---|---|---|---|---|---|---|---|
| `ig` alone | 382 | +0.244 [+0.221, +0.268] | -0.019 [-0.040, +0.002] | -0.005 [-0.024, +0.014] | -0.032 [-0.050, -0.013] | +0.019 [-0.008, +0.046] | B: not shown; C: not shown |
| Audit's U_cone | 384 | +0.505 [+0.467, +0.544] | +0.004 [-0.025, +0.033] | +0.007 [-0.026, +0.040] | -0.026 [-0.060, +0.008] | +0.162 [+0.121, +0.203] | B: not shown; C: not shown |
| U_360 | 384 | +0.318 [+0.289, +0.346] | +0.061 [+0.030, +0.092] | +0.060 [+0.028, +0.092] | +0.026 [-0.016, +0.070] | +0.194 [+0.147, +0.240] | B: not shown; C: inconclusive |
| Official-arm stages | 119 | +0.232 [+0.197, +0.268] | -0.008 [-0.027, +0.011] | -0.005 [-0.019, +0.008] | -0.027 [-0.048, -0.007] | +0.027 [-0.003, +0.058] | B: not shown; C: not shown |
| Runs clustered by scene and seed (6) | 384 | +0.218 [+0.189, +0.247] | -0.020 [-0.037, -0.002] | -0.006 [-0.018, +0.006] | -0.029 [-0.040, -0.019] | +0.024 [-0.005, +0.052] | B: not shown; C: not shown |
<!-- /table:m2_secondary -->

Counts. 384<!--n:m2_stages--> stages are usable and 0<!--n:m2_left_out--> are left out. F-room has 9.63<!--n:m2_froom_objects--> objects per member against 10.05<!--n:m2_f1_objects--> for F1, because 115<!--n:m2_froom_members--> of 2841<!--n:m2_members_total--> members had no unseen typed region (in 22<!--n:m2_froom_stages--> stages, and in 8<!--n:m2_froom_stages_all--> of them every member). No F3 member fell back to placebo objects (0<!--n:m2_fallback_deepseek-->, 0<!--n:m2_fallback_haiku--> and 0<!--n:m2_fallback_opus-->). F0 holds 151.4<!--n:m2_froom_f0_objects--> objects per member. The official-arm repeat uses 119<!--n:m2_official_stages--> stages from 7<!--n:m2_official_runs--> runs.

The registered biases:
- Toward "not shown sufficient": F1's objects are the very objects the yardstick counts.
- Toward "sufficient": F3 keeps the true labels; the error sample leaves out guesses with no unseen object of their class; and the nearest-object distance is a minimum, so common classes get short distances.
- The net direction is unknown.
- The yardstick U_wall failed part of its October check, and the rendered check that would test it (M6) is cut. Every M2 verdict is provisional.
- The error is measured on the semantic truth, while the moved objects are those of `oracle_sets.json`.

Readings where the frozen M2 file is silent (deviation 54): F0's "unmapped" objects are the yardstick's mask over both tracks; "the track's first F1 graph" is the first member id of that track; n_T enters F-room's draw as a proportion; the scene-by-seed clustering has only 6 clusters, so its interval is coarse.

## 9. Limits

- Two houses. Every verdict holds for these two and for no others.
- The truth is a proxy for what the camera saw: HM3D annotations, not the robot's view.
- The replays are static: the model saw one saved stage. No live Claude run was made (E6 is cut).
- The scorer was written after DeepSeek's numbers were seen, and frozen before any Claude output was scored. The margin at L3 was set knowing the gap between Gemini and DeepSeek at 1 m.
- One Haiku member was dropped (1<!--n:status_haiku_dropped--> of 176<!--n:mem_haiku_n-->): its final text did not parse.
- The 8<!--n:frame_rows_gemini--> Gemini rows have no wrong-house partner, and Gemini's 3<!--n:gemini_clusters--> clusters leave its intervals unbounded.
- A worker's check script printed, before the first scoring run, whether one secondary readout (kept against removed guesses) lay inside or beyond the ±5<!--n:rule_valid_band-->-point band for DeepSeek, the placebo and Gemini. It printed no number, and the scorer was not changed in response (deviation 52).
- The close L3 verdict was checked again after the result was seen (deviation 55). The no-hint replay was run after it too (deviation 56).
- M2 is provisional: its yardstick failed part of its October check and the rendered check is cut.
- Cut, and said so in §15 of the pre-registration: the direct probe; the Sonnet replay; Haiku on all stages; the rendered "seen" check (M6); the decision replay with Claude's members (H5) and the validity layer's fifth readout; live Claude (E6); the uniform comparator and the one-house logistic prior; B4 inside the family's p-values; the member-vote likelihood-ratio test and the mass-per-region correlation.
- The prompt's hint check has 12<!--n:frame_round1--> rows and 48<!--n:nohint_members--> members.

## 10. What this lets the talk say

The registered outcome is "The claim fails<!--n:thesis-->": both Claude models are Rejected at L2 and at L3, which means that neither beat the named comparator by the margin. This holds for two houses, on a truth that is a proxy for what the camera saw, on static replays. At L2 each model scores below the prior from 179<!--n:rule_houses--> other houses. At L3 the difference from the model's own content traded across unobserved regions shows no detectable difference (the frozen detectable difference is 1.1<!--n:mdd_L3_mdd--> points), and Opus's interval ends 0.05<!--n:p_opus_L3_D_gap--> points below the margin. M2 does not show that right meaning is sufficient: every arm is "not shown sufficient, on a provisional yardstick".

## What it does not let the talk say

It does not say where the guesses sit. Supported at L3 would have meant beating the named comparators at placing content in the right unobserved region; no model did. It does not say the guesses reach the map. It does not say Claude's guesses are no better than random: Haiku beats the placebo at L2 (+8.2<!--n:c_haiku_L2_B1_diff--> points, p 0.014<!--n:c_haiku_L2_B1_p-->, not adjusted). It does not use "equal", "did as well" or "failed to replicate". It does not speak for other houses, live runs, other models, or the paper's scale. It does not say M2's second half is settled: its yardstick is provisional and its net bias is unknown. The Opus verdict at L3 is close: the registered figure is 2.95<!--n:p_opus_L3_D_hi2--> against a margin of 3<!--n:c_opus_L3_margin-->, and the 15<!--n:rc_opus_below--> reruns stayed below it. A crossing would have made the thesis line "Inconclusive".
