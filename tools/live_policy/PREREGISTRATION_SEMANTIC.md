# Pre-registration: is the LLM right in meaning? (end-sem plan, milestones M0b, M1, M4)

Written 2026-11-13. This file is frozen by its sha256 in `PREREGISTRATION_SEMANTIC.sha256` before any score of an LLM against truth or against a comparator is computed under these rules. §2 lists what had been seen before the hash.

The plan is `docs/ENDSEM_PLAN_2026-11-03.md` (§3 M0b, M1, M4; §4; Section A) as changed by `docs/ENDSEM_FINAL_PLAN_2026-11-13.md`. Where they differ from this file, this file wins. §15 lists what the plan asked for and this file does not do.

## 1. Question

The ASP author says the LLM's guessed scene graphs sit in the wrong places but name the right things, and that this is enough for ASP. We test the first half as a hypothesis, on the robot's own saved inputs, at three levels:

- **L1, which rooms.** Does the model name room types that the house still holds, unseen?
- **L2, which objects.** Does it name object classes that the unseen part still holds?
- **L3, roughly where.** Does it put a room or an object in or near an unobserved region that really is of that type, or really holds that class?

The second half ("this is enough for ASP's score") is M2. It is registered apart, in `PREREGISTRATION_M2.md`, before any of its arms runs.

## 2. What had been seen before the hash

Every number below comes from DeepSeek, Gemini, the placebo or the oracle. No Claude output on these inputs exists yet.

- E1-E3 and steps 6-8, in full (`results_2026-10-31/WRITEUP.md`): LLM minus placebo +0.013; the filter; exact objects; frontier; the bench's Spearman 0.20 against 0.19 and its regret ratios 0.933, 0.904, 0.853, 0.850.
- Where guesses land: 3.0% of DeepSeek's objects lie within 0.5 m of a real same-name object, against 0.5% for the placebo; 24.1% within 2 m on matched inputs for Gemini; Gemini 9 points ahead of DeepSeek at 1 m.
- Member agreement within 1 m: 29.4% for the LLM, 4.4% for the placebo.
- Base rates: an unseen bathroom remains in 88% of stages, a bedroom in 82%, a kitchen in 56%.
- Pilot counts under earlier, cruder rules: the room test (official 34 of 46, filter_only 17 of 38, placebo 18 of 40); random room types "exist unexplored" at 0.95 against DeepSeek's 0.857, and 0.834 with types shuffled; pilot lifts of DeepSeek over shuffled and placebo guesses.
- The plan's counts of DeepSeek's October guesses: 69% of its new rooms were bedrooms and 21% bathrooms (of 724 rooms), and 29.5% of its labels lie outside the 52-word detector vocabulary. A recount of strings on 11-13 gives other totals (1,353 room nodes; 34.6% outside the vocabulary). The author's prompt says "Scene may contain more than one bedroom and more than one bathroom".
- The strings of every label in the saved DeepSeek, Gemini and placebo outputs, with their counts, read to build the label table (§6).
- The validator removed 81% of DeepSeek's added nodes in the midsem data.
- The September results on scenes 00069, 00573 and 00853.
- The truth files of §5 and their checks (`semantic/truth/README.md`). They hold no model output.
- A forecast, not a result: `docs/STATUS_2026-11-12.md` §4 expects the "mixed" outcome.

So every verdict on DeepSeek, Gemini and the placebo is **exploratory**. The Claude replays are the **blind, confirmatory** test. The scorer is written after these numbers were seen; §14 freezes it before any Claude output exists. The margin δ at L3 (§10) was set knowing the 9-point gap above.

## 3. Inputs

**The sample frame** is `semantic/sample_frame.txt`, 44 rows, hashed with this file.
- 36 rows: stages 3, 8 and 13 of 12 DeepSeek runs. Six are E1 official runs: 00853 seeds 42, 43, 44 and 00871 seeds 42, 43, 44, where 00853 seed 44 is the excluded attempt `e1_00853_s44_official_60m` (its inputs are valid; only its outcome was excluded). Six are the E2 filter_only runs.
- 8 rows: the inputs Gemini was given in October, all from first-attempt runs: 00871 seed 42, stages 2, 3, 5, 6; 00853 seed 42, stage 4; 00853 seed 43, stages 1, 2, 5.

**Clusters.** A cluster is scene × seed × arm, so there are 12. A first-attempt run joins the cluster of the official run with its scene and seed.

**Track and members.** Every row uses the track-0 map (`habitat_scene_graph_original_graph0.yaml`) as the observed graph. A model's members for a row are its completions of that graph: 4 intended. Some saved rows hold fewer (DeepSeek lacks 16 of 144 members on the 36 rows; three Gemini rows hold 3), because a member failed at the time. A row is scored on the members it has. Where a rule needs the intended count, it is 4.

## 4. Models

| Model | Role | Output |
|---|---|---|
| Claude Opus 5.5 (`claude-opus-5-5`) | confirmatory | replayed on the frame, §12 |
| Claude Haiku 5.5 (`claude-haiku-5-5`) | confirmatory | replayed on the frame, §12 |
| DeepSeek V4.1 Flash 1017 | exploratory | its saved completions on all 44 rows |
| Gemini | exploratory | its saved completions on its 8 rows |
| Placebo v2 | comparator B1, and exploratory | four draws per row, §9 |

## 5. Truth

Truth comes from the HM3D semantic annotation of each scene, moved to the pipeline frame, where x and y are horizontal and z is up. It uses no run's map. All distances below are horizontal.

**5.1 Regions and reach.** A region is an HM3D region id. Its footprint is its `any` mask in `semantic/truth/<scene>_region_footprints.npz`: the 0.05 m grid cells covered by the triangles of all its objects. (The floor mesh has gaps under furniture, so floor triangles alone hold only 43% and 28% of object centres.) A point is **inside** a region if it lies in a footprint cell. A point **reaches** a region if it is inside it or within 0.5 m of one of its footprint cells. A point may be inside, or reach, more than one region.

**5.2 Region types.** A region's types come from the raw HM3D names of its objects. A marker matches a name if the marker's words appear in the name as one run of whole words, lower case; so "oven and stove" marks a kitchen and "shower floor" a bathroom, and "bedside lamp" marks nothing. A "bed stand" marks a bedroom; it answers to nightstand (§5.3), so a mapped nightstand there counts as a mapped bedroom marker.

| Type | Markers |
|---|---|
| bathroom | toilet, bathtub, bath tub, shower |
| bedroom | bed |
| kitchen | oven, stove, stovetop |
| laundry | washing machine, laundry machine, washer, dryer |
| living | couch, sofa |
| dining (reported only) | dining table |

A name that contains, as whole words, hair dryer, hand dryer, dish dryer, dog bed, cat bed, pet bed, massage bed, toaster oven or sauna oven marks nothing. A region carries every type it has a marker for. A region with no marker is "other".

The list is the plan's, changed after reading the houses' annotations and nothing else: "washer" and "dryer" were added because 00871 holds a "washer-dryer"; "laundry machine", "bath tub" and the exclusions were added from the other houses' names, where they change only the prior of §9. Neither test house holds any of the excluded names.

**5.3 Reference objects, and the classes they answer to.** The robot's detector has its own words: it has no "bed" and calls a bed "duvet". So an annotated object **answers to** a class c if c is the canonical class of its raw name (§6), or the canonical class of the detector's label for that name, as `label_mapping.json` gives it in `synonym_primary` or `extended_sensitivity_only`. A bed answers to bed and to duvet. `label_mapping.json` reserves `extended_sensitivity_only` for sensitivity runs; this file uses it in the primary rule, because models read the detector's words in the observed graph and repeat them, and §11 reports the rule without it.

A reference object is an annotated object that has geometry, a region, and answers to at least one class that is not a structure class. Its centre is the midpoint of `world_min` and `world_max` in `<scene>_semantic_geometry.json`.

**5.4 What the robot has seen at stage k.** From the row's observed graph and the robot's path up to stage k (the start pose, and every point of `world_frame_path` in the `executed_path.json` of stages 1 to k):
- A reference object is **mapped** if an observed object node (`node_type: object`) of a class it answers to lies within 0.5 m of its centre. A marker of §5.2 is mapped by the same rule; a marker with no geometry, or one that answers only to structure classes, is never mapped.
- A region is **seen** if a path point lies in its floor mask (in its `any` mask if it has no floor), or an observed room node's centre is inside it, or at least 2 of its reference objects are mapped. The floor mask is used for the path because the `any` mask takes in the walls, so a robot passing a doorway would mark the next room seen.
- A region is **partly seen** if it is not seen, and at least 1 of its reference objects is mapped or an observed room node's centre reaches it.
- A region is **unobserved** otherwise.
- **Unseen** means partly seen or unobserved.

**5.5 What is still open at stage k.**
- A room type T is **open** if some unseen region R of type T has none of its T markers mapped, and no observed room node of type T is inside R, or reaches R while inside no other region of type T. (A bedroom node standing in a seen bedroom does not close the unseen bedroom next door.)
- A class c is **open** if an unseen region holds a reference object that answers to c and is not mapped.

## 6. Labels

One frozen normaliser serves every model and the truth. In order: (1) lower case; (2) `_`, `-` and `/` become spaces; (3) digits go; (4) spaces collapse; (5) the whole string is looked up in the synonym table; (6) failing that, a plural ending is stripped from the last word ("ies" to "y"; "es" after s, x, z, ch or sh; else a final "s" that is not "ss") and the string is looked up again; (7) failing that, the last word alone is looked up; (8) failing that, the label is "other".

The table is `semantic/canon_labels.json`. It is built from strings only: every category name in `semantic/truth/hm3d_semantic_summary.json`, the 52-word detector vocabulary, `label_mapping.json`, and every distinct label in the saved DeepSeek, Gemini and placebo outputs. Its rules:
1. Each of the 52 detector words is a canonical class.
2. Every other category name that at least 20 of the 181 annotated houses hold is a canonical class of its own.
3. A string is merged into a class only if it is a spelling variant, a plural or a plain synonym of it. When in doubt it is not merged.
4. The **structure classes** are wall, floor, ceiling, door, door frame, window, window frame, stairs and unknown, with every string in `label_mapping.json`'s `structural_never_mapped` and `door_excluded` lists mapped to the one that fits. "Window" is a detector word, but it is treated as structure here.

A label that is "other" or a structure class takes no part in L2 or L3, for models and comparators alike; each model's share of such labels is reported.

A predicted or observed room's type comes from its normalised name, by the first rule that matches: (1) it contains "bath", "toilet", "restroom", "washroom" or "shower", or holds the word "wc": bathroom; (2) it contains "bed": bedroom; (3) "kitchen": kitchen; (4) "laundry" or "utility": laundry; (5) "living", "lounge", "family" or "sitting": living; (6) "dining": dining. A room that matches none has no type and takes no part in L1; the share is reported.

L2 and L3 are scored over all canonical classes (primary) and again over the classes in the detector vocabulary only (secondary).

## 7. What counts as a guess

From one completion of the observed graph:
- A **new object** is an object node whose centre lies more than 0.5 m from every observed object node.
- A **new room** is a room node whose centre lies more than 0.5 m from every observed room node.

Node ids and the `is_predicted` flag play no part: the saved outputs reuse observed ids in about 130 cases, and one model flags none of its new objects. The counts of new objects with and without the flag are reported.

For filter_only rows the raw completions are used, before the filter: the files under `live_policy_raw/attempt_<n>/` with the highest n. This raw view is the only confirmatory view.

Per member:
- **L1 claims:** the distinct typed room types among its new rooms (dining left out).
- **L2 claims:** the distinct canonical classes among its new objects.
- **L3 items:** each new room with a type and each new object with a canonical class, with its centre. Rooms and objects are pooled, each item counting once; they are also reported apart.

## 8. Scores

- **L1:** a claim of type T is a hit if T is open.
- **L2:** a claim of class c is a hit if c is open.
- **L3:** an item is a hit if it reaches an **unobserved** region that is of its type (a room) or holds a reference object that answers to its class (an object). The share of items that reach two or more regions is reported.

A member's score at a level is hits over claims (or items). A member with no claim at a level has no score there. A row's score is the mean over its members that have one. A cluster's score is the mean over its rows that have one. A row where no hit is possible at a level (no open type, no open class, no unobserved region) is left out at that level and counted.

## 9. Comparators

Each comparator is given only the row's observed graph, and its claims are scored by the rules of §8.

| Name | What it is | Used at |
|---|---|---|
| B3 | The other-house prior (below), making as many claims as the member did. | L1, L2 |
| B1 | Placebo v2: `live_policy.placebo_graph` on the row's observed graph, with `np.random.default_rng([seed, stage, member])` for members 0 to 3 (the live arm's key for a first attempt, with no rerun salt), and the calibration file hashed in the freeze. | L1, L2 |
| B5 | Swap: the member's own labels permuted among its own L3 items of the same kind (rooms among rooms, objects among objects), centres kept; the mean of 1,000 seeded draws. | L3 |
| D | Derangement: the unobserved regions swap what they hold. Under a derangement σ of the row's unobserved regions, an item is a hit if it reaches a region R such that σ(R) is of its type or holds a reference object that answers to its class. The mean of 200 seeded draws. A row with fewer than 2 unobserved regions has no D score. | L3 |
| B3L | The prior's labels at the model's places. Rank the member's distinct labels of each kind by how often they occur (ties alphabetical). The i-th is replaced, wherever it occurs, by the prior's i-th label of that kind. Centres are kept. | L3 |
| B4 | Wrong house: the same model's members on the row of the other scene with the same seed, arm and stage, scored against this row's truth; the mean over that row's members. The 8 Gemini rows have no partner and are left out. | L1, L2, as a gate (§10) |
| B2 | Copy the map: claims the types and classes already observed. Reported only. | L1, L2 |

B3, B3L, B5 and D are computed for each model member, so each is paired with that member. B1 and B4 are paired with the row. Every contrast uses only the rows where both sides have a score; a cluster with no such row leaves that contrast, and n shrinks.

**The other-house prior, B3.** `hm3d_semantic_summary.json` lists the object names in each region of every annotated HM3D house. Houses are counted once by number (four appear in two splits), and the two test houses are left out: 179 remain. For a house h, N_T(h) is its number of regions of type T (§5.2) and N_c(h) its number of objects that answer to class c (§5.3).
- **Rooms.** m_T is 1 if the observed graph holds a room node of type T, else 0. (The map splits rooms into several nodes, so their count is not used.) The prior's score for T is the share of houses with N_T > m_T among those with N_T ≥ m_T; it is 0 if no house has N_T ≥ m_T.
- **Objects.** n_c is the number of observed object nodes of class c. The score for c is the share of houses with N_c > n_c among those with N_c ≥ n_c; it is 0 if no house has N_c ≥ n_c.
- **Claims.** The prior claims its top-k labels by score, where k is the number of claims the member made at that level (for B3L, the number of the member's distinct labels of that kind). Ties go to the label held by more of the 179 houses, then to alphabetical order. At L1 the labels are the five scored room types; at L2 and L3 they are the canonical classes that are not structure classes.

Two more forms of B3 are reported as sensitivity lines: one whose counts are the truly seen regions and mapped objects of §5.4, and one that also knows the house's size (its number of regions, in thirds).

## 10. Test

- **Unit:** the cluster. **Statistic:** the mean over clusters of (model − comparator).
- **Test:** the exact sign-flip test over clusters, one-sided (model above comparator).
- **A hypothesis** is one model at one level. Its p-value is the largest over its comparators: B3 and B1 at L1 and L2; B5, D and B3L at L3.
- **Family:** {Opus, Haiku} × {L1, L2, L3}, six hypotheses, Holm, α = 0.05.
- **Interval:** the 95% two-sided interval from inverting the sign-flip test.
- **Analysis set:** the whole rounds (§12) that both models finished.

**Verdict for a hypothesis**
- **Supported:** Holm-adjusted p < 0.05.
- **Rejected:** not Supported, and the interval's upper end for (model − named comparator) lies below δ. The named comparator is B3 at L1 and L2, and D at L3. δ is 5 points at L1 and L2 and 3 points at L3. The interval is not widened for the six tests, because the "fails" line below needs four intervals to lie below δ at once.
- **Inconclusive:** otherwise.

**The wrong-house gate.** B4 pairs each cluster with its partner in the other scene, so its differences come in dependent pairs. It is therefore tested apart: the exact sign-flip test over the 6 seed × arm pairs, one-sided, p < 0.05, not Holm-adjusted. A pair's value is the mean of its two clusters' differences. The smallest possible p is 1/64.

**The thesis**

| Outcome | Rule |
|---|---|
| The claim holds | A Claude model is Supported at L3. |
| Mixed | No Claude model is Supported at L3, and one is Supported at L1 or L2 and passes the wrong-house gate at that level. |
| The claim fails | Every Claude model is Rejected at L2 and at L3. |
| Inconclusive | Anything else. |

**Detectable difference.** For each level, MDD = (z(1 − α/6) + z(0.8)) × SD / √n, where n is the number of clusters and SD is the standard deviation across clusters of a contrast between two comparators on the frame rows, computed for the placebo's own members: B1 − B3 at L1 and L2, and B5 − D at L3. The same contrasts give the interval half-width that shows whether "Rejected" is within reach at each level. Both are written into the freeze (§14) before any Claude output is scored. A null is reported as "no detectable difference", with the MDD. The plan put L1's detectable difference near 20 points; if the freeze confirms that L1 cannot decide, the slide says so.

## 11. Secondary readouts (no verdict rests on them)

- L1 and L2 under the plan's looser rule: a hit needs only an unseen region of the type, or one holding the class, mapped or not.
- L3 on the partly seen regions, apart from the unobserved ones.
- L2 and L3 on the detector vocabulary only.
- L1 with one claim matched to one region, so a second "bedroom" needs a second open bedroom.
- L4: the share of new objects within 0.5, 1, 2 and 3 m of an unmapped reference object that answers to its class in an unseen region.
- L2 and L3 with "answers to" built from `synonym_primary` alone, without `extended_sensitivity_only`.
- DeepSeek, Gemini and the placebo under every rule above, labelled exploratory.
- **The paper's room test, with a chance rate.** On live stages with 8 members: a region not seen at stage 0 counts as predicted before found if, at some stage before it is seen (§5.4), at least 2 of the 8 members put a new room within 2.5 m of the region's `centroid_xy` in `<scene>_regions.json`. It is scored twice: with the room's type required to match, and without. Reported per live arm, with the placebo arm as the chance rate and the paper's 9 of 28 beside it. On the 4-member replays the same count is given at 1 of 4 and at 2 of 4.
- **The validity layer,** scored in the same pass on every row and model. Views: raw; V (guesses that pass `validate_completion` with `ValidationConfig(allow_parsed_mapping=True)`, the E2 filter); V plus a vote at 0.5, 0.75 and 1.0 of the 4 intended members; and, on live 8-member stages, the paper's 2-of-8 rule. Readouts:
  1. the share of guesses the validator removes, by reason;
  2. L2 and L3 hit rates of kept guesses against removed ones, with the interval of the difference; "no detectable difference" if that interval lies within ±5 points;
  3. member support against L3 truth: a reliability curve, Brier score and ECE, with an isotonic calibrator fit on one scene and tested on the other;
  4. hits kept against guesses kept, at each vote level.
- **The prompt's hint (exploratory).** Haiku on the round-1 rows with the sentence "Scene may contain more than one bedroom and more than one bathroom" removed; its L1 claims beside the hinted run's.

## 12. The Claude replays (M4)

- **Inputs.** Each row's inputs are exported from the host by `m4/export_replay_inputs.py`: the observed graph byte for byte, the author's prompt from the run's own config (one text for all 44 rows, sha256 05ddf86bb9c4d09d…), and the 6 slices rendered again with the author's `create_scene_slices`. For the 8 rows Gemini was given, the re-rendered slices and graph are compared by sha256 with the inputs saved in October; a row that differs is listed and reported, and no row is dropped for it. (Checked on 11-13 before the hash: all 8 are identical.)
- **Loop:** a direct port of the author's tool loop to the Anthropic API (`tools/llm_anthropic/`): his prompt text, the YAML, then the 6 slice images in sorted filename order, in the first message only; his `check_collision` tool, answered by his own feasibility function; at most 50 turns; his `parse_response` on the final text.
- **What the API forces, each a logged difference from his loop:** no temperature and no seed; adaptive thinking; tool choice "auto"; a fixed image order.
- **Settings:** effort "medium" for both models; `max_tokens` 64,000; 4 members per row; no fallback model.
- **Drops.** A transient error (rate limit, server error, timeout, broken stream) is retried up to 3 times. A member is dropped, and counted, only if it is refused, hits 50 turns, still fails after the retries, or its final text does not parse.
- **Rounds, so that a cap stop leaves a balanced set:** round 1 is stage 8 of the 12 runs; round 2 is stage 13; round 3 is stage 3; round 4 is the 8 Gemini rows. Within a round Haiku runs first. Before a round starts, its projected cost (rows × 4 × the measured cost per member) must fit under what is left of the model's cap; if it does not, that model stops before the round.
- **Caps:** Opus $280, Haiku $20, checked in code on settled spend.
- **Smoke test first,** on three inputs outside the frame: `dryrun2_00069_s42_filter_only_10m` stages 1 and 3, and `e1_00871_s44_official_60m` stage 17. 28 members: Haiku medium and Opus medium on all three inputs, and Opus low on the third, 4 members each; cap $30. It is scored for cost and plumbing only.
- **Balance checks:** each model's drop rate (a rate above 25% is flagged on the slide); zero requests rejected because history was edited.
- The measured cost per member goes into the freeze before round 1.

## 13. M2

Registered apart in `PREREGISTRATION_M2.md`.

## 14. The freeze

Before any Claude output is scored, one commit holds, with their sha256 in `semantic/FREEZE.sha256`: the scorer code under `tools/live_policy/semantic/`, `canon_labels.json`, the truth files, `sample_frame.txt`, the table of detectable differences, and the measured cost per member. The commit is pushed. A later change to any of them is a deviation, and the result is shown both ways.

The truth files, the label table and the sample frame are hashed before the first exploratory score as well.

## 15. Not done, and said so

- The direct probe; the Sonnet replay; Haiku on all 259 stages.
- The rendered "seen" check and yardstick (M6); the decision replay with Claude's members (H5), and with it the validity layer's fifth readout.
- Live Claude (E6).
- The uniform comparator B0 and the one-house logistic prior B3a: B3 from 179 other houses replaces them.
- B4 inside the family's p-values: it is a separate gate (§10), because its pairs are dependent.
- The member-vote likelihood-ratio test; the mass-per-region correlation.
- Changed from the plan: L1 and L2 need unmapped content (§5.5; the plan's rule is a secondary); a new room or object is told by its place alone, not by its id or flag (§7); "seen" uses every path point, not only the stops (§5.4).

## 16. How results may be worded

- A null is "no detectable difference", with the detectable difference beside it. Never "equal" and never "did as well".
- Every verdict holds for two houses, on a truth that is a proxy for what the camera saw, on static replays.
- Supported at L3 means: beats the named comparators at placing content in the right unobserved region. It does not mean the guesses reach the map.
- If M4 does not run, no thesis line applies; the DeepSeek rows are exploratory.
