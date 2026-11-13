# The semantic test: how to run it

Spec: `../PREREGISTRATION_SEMANTIC.md` (frozen). Points it left open: `../DEVIATIONS_NOVEMBER.md`, item 51.
Run from the repo root with `.venv_offline/bin/python`. Tests: `.venv_offline/bin/python -m pytest -q tools/tests/test_semantic_*.py`.

## What each file does

| File | Job |
|---|---|
| `model.py` | The data shapes every module passes. |
| `labels.py`, `canon_labels.json` | Label table, room types, markers, "answers to" (with a switch for `synonym_primary` alone). |
| `region_truth.py` | Truth of a scene; what the robot has seen and what is still open at a stage. |
| `extract_preds.py` | Reads graphs and completions; finds the guesses; loads any (run, stage); Claude member status. |
| `score_levels.py` | L1, L2, L3 hits, the secondary counts, L4, the placement-error sample. |
| `baselines.py` | B1 to B5, B3L, the prior and its two sensitivity forms, D. |
| `validity.py` | The validator, the votes, the four readouts of §11. |
| `room_test.py` | The paper's room test with a chance rate. |
| `stats.py` | Sign-flip test and interval, Holm, verdict, reliability helpers. |
| `run_semantic.py` | The command line. |
| `freeze.py` | Writes and checks `FREEZE.sha256`. |

## The three commands

Set the hash once. It is the first word of `../PREREGISTRATION_SEMANTIC.sha256`.

```
H=$(head -1 tools/live_policy/PREREGISTRATION_SEMANTIC.sha256 | cut -d' ' -f1)
S=tools/live_policy/semantic/run_semantic.py
```

**0. Truth-only hash** (§14: before the first exploratory score). It hashes the label table, the frame and `truth/`.

```
.venv_offline/bin/python tools/live_policy/semantic/freeze.py write --truth-only     # writes TRUTH.sha256
```

**1. Dry run.** It computes everything and writes only counts, shapes and times (about one minute).
It writes `OUT/dry_run.json` and prints the same text. It writes no score and no error sample.

```
.venv_offline/bin/python $S --models deepseek,gemini,placebo --out /tmp/dry --dry --prereg-sha256 $H
```

**2. Exploratory run** (DeepSeek, Gemini, placebo). Same line without `--dry`.

```
.venv_offline/bin/python $S --models deepseek,gemini,placebo --out RESULTS/exploratory --prereg-sha256 $H
```

**3. Freeze, then the Claude run.** The freeze lists the sha256 of every `*.py` here, `canon_labels.json`,
`sample_frame.txt`, everything in `truth/`, and the extra files you name. Check it any time.

```
.venv_offline/bin/python tools/live_policy/semantic/freeze.py write \
    --extra RESULTS/exploratory/mdd_table.json --extra tools/live_policy/m4/COST_ADDENDUM.md
.venv_offline/bin/python tools/live_policy/semantic/freeze.py check
```

The Claude run refuses unless `freeze.py check` passes; it names each file that differs. Parsed outputs sit in
`<root>/<model>/effort_medium/<row_id>/member_<k>/` (the level `effort_medium` is optional) with `parsed_graph.yaml`,
`parse.json` (`{"ok": true}`) and `record.json` (`status`). A member is **ok** when it parsed. It is **dropped**
(counted, not scored) when its status is `dropped_refusal`, `dropped_turn_limit` or `dropped_error`, or when `parse.json`
says `ok` false. It is **unfinished** when its status is `cap_stopped` or `error`, or its folder is empty; it is
**absent** with no folder. A round is finished for a model when every row of it has 4 members that are ok or dropped.
A row whose members were all dropped stays in its round and has no score. `--rounds auto` uses the rounds finished
for both models, and refuses if there is none.

```
.venv_offline/bin/python $S --models claude-opus-5-5,claude-haiku-5-5 \
    --claude-root /Users/sher/project/cvp/replay_outputs/m4 --out RESULTS/claude --prereg-sha256 $H
```

Options: `--rounds 1,2` (score only those rounds), `--runs-root`, `--frame`, `--no-room-test`, `--no-validity`,
`--room-test-runs all` (also the live runs the run table excludes).

**Where the guards live.** In the command line (`main` and `check_guards`), not in the library functions
(`run`, `run_core`, `score_model`). Tests and notebooks can call those directly without a hash or a freeze.
The command line checks the hash you give against the hash file, checks that the pre-registration text still
has that hash, and, for a Claude model, checks the freeze.

## What a real run writes (in `--out`)

| File | Holds |
|---|---|
| `results.json` | Run info (hashes, versions, times), the family (p, Holm, verdicts, wrong-house gate, thesis), the detectable-difference table, the room test, and per model: analysis on the chosen rounds and on all rows, every secondary line, the extras (L1 matched, items reaching two regions, L4 at 0.5, 1, 2, 3 m), the validity readouts, and the exploratory verdicts. |
| `records_<model>.json` | One record per row: every member's scores, every comparator, and the same for each secondary line. |
| `mdd_table.json` | The table of detectable differences (§10), from the placebo's own members: per level the number of clusters, the SD of the named contrast (B1 - B3 at L1 and L2, B5 - D at L3), the detectable difference, and the interval half-width beside the margin delta. Written by every real run; the exploratory one is the file to freeze. |
| `room_test.json` | The paper's room test: per live run and per arm (with the paper's 9 of 28), and the 1-of-4 and 2-of-4 counts on the replays. |
| `validity.json` | The four validity readouts for each model. |
| `error_sample_<model>.json` | A plain list of distances in metres for `PREREGISTRATION_M2.md` §4 (F3-m). One file per model. |

`error_sample_<model>.json`: for each new object of the model on the frame rows (raw view) with a class that is
neither "other" nor structure, the horizontal distance to the nearest reference object that answers to its
class, is not mapped, and lies in an unseen region at that row. A guess with no such object is left out; the
count is in `results.json` (`error_sample_left_out`). Distances are pooled over all rows and members.

The dry run counts the distances and the left-out guesses. It never saves them.

## Readings I chose where the spec is silent

- A new room typed dining is left out of L1 and of L3, and counted (item 51).
- The validator is called as `live_policy.track_keep_sets` calls it. A guess is kept if its node is in the
  validated graph. A rejected completion keeps no guess. A guess that reuses an observed id counts as an
  observed node: kept.
- Support is `support_scores` with 4 as the denominator. It sets `is_predicted` from the node id, because
  Gemini flags none of its new objects.
- The paper's 2-of-8 rule: at least 2 of the 8 members of a live stage hold a node of the same label near the
  guess (0.5 m for objects, 4 m for rooms, any track, no parent test). Only DeepSeek has live members.
- The room test: stage 0 holds 4 members, not 8. The result is given for all stages and for stages with all 8.
  It uses the live runs the run table counts. The members are the files on disk (after the filter, for filter_only).
- The replay count: a region not seen at stage 0 of the run counts if, at some replay row before the region
  is first seen in that run, at least t of the model's members put a new room within 2.5 m.
- B3's sensitivity lines: `B3_seen` (counts from the truly seen regions and mapped objects), `B3_size`
  (only houses in the same third by number of regions, cut at the 1/3 and 2/3 percentiles of the 179 houses),
  and `B3_seen_size` (both).
- The detector-vocabulary line has no L1 and no room items: rooms are not detector words.
- The placebo as a model has no B1 (it would be itself) and no B4. Its records feed the detectable-difference table.
- The family is always six hypotheses. A registered hypothesis that was not run takes p = 1. "The claim fails"
  needs both Claude models.

## Two facts for whoever reports results

- A guess labelled "stove" can never hit in either test house under the frozen label rules. In 00853 the
  annotation "oven and stove" answers to "oven". In 00871 "stovetop" answers to "gas stove".
- In the §11 view that leaves out `extended_sensitivity_only`, a bed answers only to "bed". No detector
  "duvet" maps a bed there.
