# M2, the whole study (13 Nov 2026)

The rules are `PREREGISTRATION_M2.md`, sha256 `5b8a8400...`. Two passes ran. Pass 1 ran F1, F5, F6, F0, F-room and F3 with DeepSeek's error file. Pass 2 ran F3 with Haiku's and Opus's error files, on pass 1's saved left-out list. The tables below come from pass 2's summary, which holds all arms.

Every verdict is provisional. The yardstick U_wall failed part of its October check, and the rendered check that would test it (M6) is cut. No correction was made for running F3 for three models.

## What ran

- Code: `m2/factorial.py`, `m2/summarise_factorial.py`, `m2/passcheck.py`, `m2/run_m2_pass.sh`. An independent reader checked the code against §3 to §6. Both scripts import the registered bench and do not edit it.
- Stages: the bench's 384 stages from 24 runs, whose replayed top-10 matches the log. The host rebuilt the bench first: 9,600 of 9,600 picks match. On the host's numpy, `U360` differs by 1 on 36 of 115,200 candidate values (14 stages, all 00853 seed 43). `Uwall`, `Ucone` and every pick are equal.
- Pass 1: 458 s for the study on 48 workers (472 s with the summary). Pass 2: 252 s in total. Each pass holds 384 rows, none an error or a drop, and wrote its `PASS_COMPLETE` marker. The marker checks the row count, the error rows and every asked-for arm on every row. The summary and the later runner refuse a pass without it.
- Seed codes: F-room 11; F3 with DeepSeek 21, Haiku 22, Opus 23.

## Error samples (F3)

| Model | Distances | Median (m) | sha256 |
|---|---|---|---|
| DeepSeek | 1,249 | 7.67 | `f85be8a6...` |
| Haiku | 617 | 7.13 | `fe490032...` |
| Opus | 800 | 8.12 | `0bc62b40...` |

Each file is a JSON list of distances in metres. The medians come from the files and nothing else.

## Left-out stages

None. A stage leaves the study if the correlation is undefined for F1, either F5 set, F6, F-room or F3-DeepSeek. It was defined for all of them on all 384 stages. The list is `pass1/left_out_stages.json`, and pass 2 read it as it stands.

## Kept stages that lack a value

Zero, for every arm, including F3 with Haiku and Opus. So X − 0.5·A on the stages where both are defined equals the main figure for every model and for F-room.

## Objects per member

| Arm | Mean | Min | Max |
|---|---|---|---|
| F1 | 10.05 | 6 | 16 |
| F5 (set A, set B) | 10.14, 10.00 | 6 | 16 |
| F6 | 0 | 0 | 0 |
| F3 (DeepSeek, Haiku, Opus) | 10.05 each | 6 | 16 |
| F-room | 9.63 | 0 | 16 |
| F0 | 151.4 | 60 | 226 |

F-room has fewer than F1 because 115 of 2,841 members had no unseen typed region. Their graph equals F6. This happened in 22 stages, and in 8 of them every member was affected. No F3 member fell back to placebo objects, so no member went unmoved.

## Primary numbers

Score `ig − 0.2·d`, yardstick `Ucone` (U_wall inside the camera cone), Spearman per stage, mean over 24 runs, 95% interval from the wild cluster bootstrap over runs.

| Arm | Mean correlation | Median per stage |
|---|---|---|
| F1 | +0.284 [+0.261, +0.307] | 0.293 |
| F5 | +0.065 [+0.042, +0.089] | 0.064 |
| F6 | −0.028 [−0.048, −0.007] | −0.028 |
| F0 | +0.048 [+0.027, +0.069] | 0.045 |
| F3-DeepSeek | +0.046 [+0.028, +0.063] | 0.044 |
| F3-Haiku | +0.060 [+0.041, +0.078] | 0.050 |
| F3-Opus | +0.036 [+0.019, +0.054] | 0.034 |
| F-room | +0.089 [+0.073, +0.106] | 0.091 |

A = F1 − F5 = **+0.218 [+0.195, +0.241]**. It lies wholly above 0, so the reading rule goes on to its second step.

| Arm X | X − F5 | X − 0.5·A | Verdict |
|---|---|---|---|
| F3-DeepSeek (B) | −0.020 [−0.036, −0.003] | −0.129 [−0.144, −0.113] | not shown sufficient, on a provisional yardstick |
| F3-Haiku (B) | −0.006 [−0.020, +0.009] | −0.115 [−0.130, −0.099] | not shown sufficient, on a provisional yardstick |
| F3-Opus (B) | −0.029 [−0.043, −0.015] | −0.138 [−0.154, −0.123] | not shown sufficient, on a provisional yardstick |
| F-room (C) | +0.024 [+0.001, +0.047] | −0.085 [−0.103, −0.068] | not shown sufficient, on a provisional yardstick |

No arm comes near the half of A that the rule asks for. F3 with Haiku or Opus does no better than the placebo, and Opus does worse. F-room does slightly better than the placebo.

## F0, the all-true anchor

F0 comes out at +0.048 [+0.027, +0.069], close to F5 (F0 − F5 = −0.017 [−0.031, −0.004]). `ig` is 0 for every candidate in 2 of 384 stages (0.5%). F6 also has 2. Most stages hold two tracks with different observed graphs, so `ig` is rarely 0 there. F0 takes no part in the reading rule.

## Secondary figures

The verdict wording is the same everywhere: where a row says "not shown", read "not shown sufficient, on a provisional yardstick".

| Repeat | A | B DeepSeek | B Haiku | B Opus | C | Verdicts |
|---|---|---|---|---|---|---|
| `ig` alone (382 stages) | +0.244 [+0.221, +0.268] | −0.019 [−0.040, +0.002] | −0.005 [−0.024, +0.014] | −0.032 [−0.050, −0.013] | +0.019 [−0.008, +0.046] | all not shown |
| Audit's U_cone (no wall test) | +0.505 [+0.467, +0.544] | +0.004 [−0.025, +0.033] | +0.007 [−0.026, +0.040] | −0.026 [−0.060, +0.008] | +0.162 [+0.121, +0.203] | all not shown |
| U_360 | +0.318 [+0.289, +0.346] | +0.061 [+0.030, +0.092] | +0.060 [+0.028, +0.092] | +0.026 [−0.016, +0.070] | +0.194 [+0.147, +0.240] | B not shown; C inconclusive (C − 0.5·A = +0.035 [−0.004, +0.074]) |
| Official-arm stages (119 stages, 7 runs) | +0.232 [+0.197, +0.268] | −0.008 [−0.027, +0.011] | −0.005 [−0.019, +0.008] | −0.027 [−0.048, −0.007] | +0.027 [−0.003, +0.058] | all not shown |
| Runs clustered by scene and seed (6 clusters) | +0.218 [+0.189, +0.247] | −0.020 [−0.037, −0.002] | −0.006 [−0.018, +0.006] | −0.029 [−0.040, −0.019] | +0.024 [−0.005, +0.052] | all not shown |

- `ig` alone drops two stages because F6's `ig` is constant there.
- The official-arm stages give the same verdicts under `ig` alone and under the audit's U_cone. Under U_360 they give the same split as on all stages: B not shown, C inconclusive.
- The clustered B − 0.5·A values are −0.129 [−0.145, −0.112] (DeepSeek), −0.115 [−0.127, −0.102] (Haiku), −0.138 [−0.151, −0.125] (Opus) and −0.085 [−0.105, −0.065] (F-room).
- R1 regret, mean over runs. Under U_wall: F1 8.98, F5 9.66, F6 10.06, F0 10.57, F3-DeepSeek 9.40, F3-Haiku 9.61, F3-Opus 9.87, F-room 9.59. Under U_wall_cone: F1 4.20, F5 4.52, F6 4.90, F0 5.06, F3-DeepSeek 4.59, F3-Haiku 4.68, F3-Opus 4.71, F-room 4.62. Against F5, only F1 is clearly lower under both. F6 and F0 are clearly higher under both. No F3 arm and not F-room differs clearly from F5.

## Readings where the frozen file is silent

1. F0's "unmapped" is the yardstick's mask over both tracks, the same for both tracks of a stage.
2. "The track's first F1 graph" is the first id of that track in `gids` order.
3. n_T enters the draw as a proportion and is not rounded.
4. A type with an empty label pool would get weight 0. It does not occur.
5. An F3 fallback member's F-room count N is its count of placebo objects.
6. The secondary yardsticks drop their own undefined stages, paired across arms.
7. The scene-by-seed clustering has 6 clusters, so its interval comes from only 64 sign patterns.

## Files

- `pass1/`: summary (json and txt), `left_out_stages.json`, `factorial_meta.json`, `PASS_COMPLETE`, `err_deepseek.json`, `run_log.txt`. The per-stage file (34 MB) stays on the host; its sha256 is `7bfeb14a7352a97d04f65394ba1bca961910ac1b00405896926178ef6b0f3a50`.
- `pass2/`: summary (json and txt), `factorial_meta.json`, `PASS_COMPLETE`, `err_haiku.json`, `err_opus.json`, `run_log.txt`, and the per-stage file `factorial_stages.jsonl` (13 MB, under the 20 MB limit).
- Hashes match on both machines for every file in both folders, except pass 1's per-stage file, which stays on the host. Pass 2: summary json `dea2d0e4...`, summary txt `eeae223f...`, meta `9a92aaaa...`, marker `872b877b...`, run log `59ed013a...`, per-stage file `63db1fbd65add6a5251ea791803634365656e57278c90d9408b35d58dc1ecbd4` (the value its marker records).
