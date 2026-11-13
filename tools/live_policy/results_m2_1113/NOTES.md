# M2, first pass (13 Nov 2026)

The rules are `PREREGISTRATION_M2.md`, sha256 `5b8a8400...`. This pass ran F1, F5, F6, F0, F-room and F3 with DeepSeek's error file. The Claude F3 arms (Haiku and Opus) are still to come. Every M2 verdict is provisional: the yardstick U_wall failed part of its October check.

## What ran

- Code: `m2/factorial.py` and `m2/summarise_factorial.py`, reviewed by an independent reader against §3 to §6. Both import the registered bench; neither edits it.
- Stages: the bench's 384 stages from 24 runs, whose replayed top-10 matches the log. The host rebuilt the bench first: 9,600 of 9,600 picks match. On the host's numpy, `U360` differs by 1 on 36 of 115,200 candidate values (14 stages, all 00853 seed 43). `Uwall`, `Ucone` and every pick are equal.
- Error file: `pass1/err_deepseek.json`, 1,249 distances in metres, sha256 `f85be8a6...` (same on both machines).
- The pass took 458 s on 48 workers (472 s with the summary). It holds 384 rows, none an error or a drop. It wrote its `PASS_COMPLETE` marker, which checks the row count, the error rows and every arm on every row.
- The per-stage file (`factorial_stages.jsonl`, 34 MB) stays on the host in `endsem_cpu/m2/pass1/`. Its sha256 is `7bfeb14a7352a97d04f65394ba1bca961910ac1b00405896926178ef6b0f3a50`.
- Hashes of the files in this folder match on both machines.

## Left-out stages

None. The list names a stage if the correlation is undefined for F1, either F5 set, F6, F-room or F3-DeepSeek. It was defined for all of them on all 384 stages. The list is saved in `left_out_stages.json` and the Claude pass reuses it.

## Objects per member

| Arm | Mean | Min | Max |
|---|---|---|---|
| F1 | 10.05 | 6 | 16 |
| F5 (set A, set B) | 10.14, 10.00 | 6 | 16 |
| F6 | 0 | 0 | 0 |
| F3-DeepSeek | 10.05 | 6 | 16 |
| F-room | 9.63 | 0 | 16 |
| F0 | 151.4 | 60 | 226 |

F-room has fewer than F1 because 115 of 2,841 members had no unseen typed region. Their graph equals F6. This happened in 22 stages, and in 8 of them every member was affected. No F3 member fell back to placebo objects, so no member went unmoved.

## Primary numbers

Score `ig − 0.2·d`, yardstick `Ucone`, Spearman per stage, mean over 24 runs, 95% interval from the wild cluster bootstrap over runs.

| Arm | Mean correlation |
|---|---|
| F1 | +0.284 [+0.261, +0.307] |
| F5 | +0.065 [+0.042, +0.089] |
| F6 | −0.028 [−0.048, −0.007] |
| F0 | +0.048 [+0.027, +0.069] |
| F3-DeepSeek | +0.046 [+0.028, +0.063] |
| F-room | +0.089 [+0.073, +0.106] |

| Difference | Mean and interval |
|---|---|
| A = F1 − F5 | +0.218 [+0.195, +0.241] |
| B = F3-DeepSeek − F5 | −0.020 [−0.036, −0.003] |
| C = F-room − F5 | +0.024 [+0.001, +0.047] |
| B − 0.5 A | −0.129 [−0.144, −0.113] |
| C − 0.5 A | −0.085 [−0.103, −0.068] |

Reading rule: the interval of A lies wholly above 0, so M2 is read further. B − 0.5 A and C − 0.5 A both lie wholly below 0. Verdicts for DeepSeek's F3 and for F-room: not shown sufficient, on a provisional yardstick.

## F0, the all-true anchor

F0 comes out at +0.048 [+0.027, +0.069], close to F5 (F0 − F5 = −0.017 [−0.031, −0.004]). `ig` is 0 for every candidate in 2 of 384 stages (0.5%). F6 also has 2. Most stages hold two tracks with different observed graphs, so `ig` is rarely 0 there. F0 takes no part in the reading rule.

## Secondary figures

- Median per-stage correlation: F1 0.293, F5 0.064, F6 −0.028, F0 0.045, F3-DeepSeek 0.044, F-room 0.091.
- With `ig` alone (382 stages; two stages drop because F6's `ig` is constant): A +0.244, B −0.019 [−0.040, +0.002], C +0.019 [−0.008, +0.046]. Verdicts: not shown sufficient, on a provisional yardstick, for both.
- With the audit's U_cone (no wall test): A +0.505, B +0.004 [−0.025, +0.033], C +0.162 [+0.121, +0.203]. Verdicts: not shown sufficient, on a provisional yardstick, for both.
- With U_360: A +0.318, B +0.061 [+0.030, +0.092], C +0.194 [+0.147, +0.240]. DeepSeek's F3: not shown sufficient, on a provisional yardstick. F-room: inconclusive.
- R1 regret, mean over runs. Under U_wall: F1 8.98, F5 9.66, F6 10.06, F0 10.57, F3-DeepSeek 9.40, F-room 9.59. Under U_wall_cone: F1 4.20, F5 4.52, F6 4.90, F0 5.06, F3-DeepSeek 4.59, F-room 4.62. Against F5, only F1 is clearly lower under both. F6 and F0 are higher under both.
- Official-arm stages alone (119 stages, 7 runs): A +0.232 [+0.197, +0.268], B −0.008 [−0.027, +0.011], C +0.027 [−0.003, +0.058]. Verdicts: not shown sufficient, on a provisional yardstick, for both. The U_360 repeat gives the same two verdicts as on all stages.
- Runs clustered by scene and seed (6 clusters): A +0.218 [+0.189, +0.247], B −0.020 [−0.037, −0.002], C +0.024 [−0.005, +0.052]. Verdicts as in the main reading.
- Every arm has a value on every kept stage, so the paired figures for stages where an arm is defined equal the main ones.

## Readings where the frozen file is silent

1. F0's "unmapped" is the yardstick's mask over both tracks, the same for both tracks of a stage.
2. "The track's first F1 graph" is the first id of that track in `gids` order.
3. n_T enters the draw as a proportion and is not rounded.
4. A type with an empty label pool would get weight 0. It does not occur.
5. An F3 fallback member's F-room count N is its count of placebo objects.
6. The secondary yardsticks drop their own undefined stages, paired across arms.
7. The scene-by-seed clustering has 6 clusters, so its interval comes from only 64 sign patterns.

## Files

`summary_factorial.json` and `.txt`, `left_out_stages.json`, `factorial_meta.json`, `PASS_COMPLETE`, `err_deepseek.json`, `run_log.txt`.
