# Reading of 6 Nov

Reading of `paper_compare.md` and `paper_compare.json` in this folder, written 6 Nov 2026 (it was `docs/STANDING_2026-11-06.md`, now merged here).

**Cite `../results_paper_compare_1112/` instead.** What changed after 6 Nov:
- The budget barely moved (853: 632.13 to 632.18 s, now the median end of five frontier runs; 871: unchanged at 809.08 s, the registered fallback; PREREGISTRATION_PAPER.md §4).
- The reference. Here it is the HM3D human labels (HL) or one frontier run's final map (FM). The 12 Nov scores use the rebuilt reference, a scripted tour that follows the author's protocol (APR-a).

The FM and HL cells below equal the 12 Nov file's `frontier_made` and `hm3d` cells. 12 Nov adds the APR reference and the `frontier_end` runs. Read this page for the method, the reading of the gaps, and the open questions; read the 12 Nov folder for the scores to cite.

## What still differed from the paper (6 Nov)

| | Paper | Ours |
|---|---|---|
| Reference graph | a tour driven by hand through the same pipeline; never released | the HM3D human labels (180 objects on 853, 232 on 871), and one frontier run's final map (80 and 91 objects). A scripted tour that follows his protocol was built and waiting for the GPU. |
| Time budget | 10%, 50% and 100% of a budget whose value is not given | the end of one frontier run: 632 s on 853 and 809 s on 871. Once the new frontier runs finish, the budget becomes their median end, and every number below will move. |
| Run length | L_max not given; 25-30 steps of about 3.74 m suggest 94-112 m | ASP runs stop at 60 m, about 380 s. All of them have 10% values. Every 853 run reaches 50%, but only 2 of 12 on 871 do, and none reaches 100%. |
| Clock | not described | In his released code, frontier's clock also runs while it waits for each new path. ASP's clock starts when the path arrives (file and line references: `../results_paper_compare_1112/NOTES.md`, "Frontier clock"). Frontier stops more often (about 2.5 times as often on 871), so this charges frontier more. Our frontier logs 6.8 s per metre on 853 and 8.7 on 871; ASP logs 6.1-6.5. |
| LLM | Gemini 2.5 Pro | DeepSeek in October; Claude planned |
| Runs per scene | apparently one. His 853 numbers at 100% moved between v1 and v2 (frontier 48.3 to 58.8, ASP 59.0 to 66.7). | 2-3 per arm |
| Computer | a laptop with an RTX 4060 | a shared server; the clock is wall time, so speed can differ |

## Are our graphs like his?
Probably in kind and roughly in size, but this is not proven.
- **His reference behaves like a mapper-made graph.** His GED falls as his runs go on (853 frontier: 279 to 177). Ours does the same against our frontier map. Against the human labels, ours rises (552 to 836), because the labels hold many objects the detector never finds.
- **Size (empty-graph GED scale).** An empty graph scores 285 and 318 against our frontier map (gmatch4py counts nodes plus twice the edges), and 552 and 712 against the human labels. His frontier's 10% values, 279 and 292, sit near the first pair. A 10% map is not empty, so this is only a rough guide.
- **What settles it.** Only his files can. Our tours give a closer copy, not proof.

## The numbers, matched by time (F1 × 100)
FM means scored against our frontier-made map. It favours frontier, and it stood in for his reference until the tours ran. HL means scored against the human labels, which are fair to every arm but much harder. Cells are means; brackets show how many runs reached that time when not all did.

| Scene, time | Paper: ASP / frontier | Ours, FM: ASP / ASP + filter / random guesses / frontier | Ours, HL: same order |
|---|---|---|---|
| 853, 10% | 34.4 / 18.6 | 17.6 / 19.8 / 16.3 / 19.7 | 8.0 / 7.6 / 6.4 / 9.7 |
| 853, 50% | 60.8 / 46.5 | 39.9 / 52.6 / 49.2 / 55.1 | 21.6 / 24.1 / 23.1 / 26.7 |
| 871, 10% | 30.5 / 29.2 | 33.3 / 34.2 / 30.1 / 37.6 | 7.6 / 8.4 / 6.3 / 7.1 |
| 871, 50% | 62.4 / 55.7 | none / 61.4 (1 of 3) / 38.6 (1 of 3) / 47.1 | none / 21.1 (1 of 3) / 9.8 (1 of 3) / 10.4 |
| 871, 50% of a 20% shorter budget | no paper value | 59.5 / 47.4 (2 of 3) / 34.3 (2 of 3) / 45.3 | 18.3 / 13.5 (2 of 3) / 9.5 (2 of 3) / 10.2 |

What the table says:
- **The paper's margin.** At 50%, the paper's ASP leads frontier by 14.3 points on 853 and 6.7 on 871.
- **853 at 50%.** Our frontier's mean is above both ASP arms: by 2.5-15.2 points on FM, and by 2.6-5.2 on HL, where the ranges overlap.
  - Frontier leads even though it had walked less by then (39-42 m, against 45-49 m for ASP).
  - Random guesses land between the two ASP arms.
  - Frontier stays on top at a 20% shorter and a 20% longer budget.
- **871.** At 50% of the budget most ASP runs had already stopped. At 50% of a 20% shorter budget all three ASP runs reach it, and they lead frontier by 14.2 points (FM) and 8.0 (HL). They also lead random guesses.
  - By then ASP had walked farther (46-55 m against 33-37 m), probably in part because frontier's clock includes its path waits.
  - So part of this lead may be the clock, not better exploration.
- **10%.**
  - On 853 his ASP starts 15.8 points above his frontier. Ours starts level with or just below our frontier.
  - On 871 our ASP is close to his (33.3-34.2 against 30.5), and our frontier is higher than his (37.6 against 29.2).
- **Spread.**
  - On 853 at 50%, our two DeepSeek arms, which differ only in the filter, sit 12.7 points apart on FM, with no overlap. On HL they sit 2.5 apart.
  - Our pre-registered test of these arms (E2: area under the curve to 60 m, on HL) found no detectable difference.
  - With 2-3 runs per arm we cannot tell spread from a real effect at one time point.

## So where did we stand (6 Nov)?
- **Method parity: nearly done.** Each stage is scored with his F1 and GED code. Two things were still open: which label file each scene used, and how Fig. 4 reads a value at each time.
- **Graph parity: likely, not proven.**
- **Result parity: split, and descriptive only (2-3 runs).**
  - On 853 we do not get his ASP lead. This fits our pre-registered frontier test from 30 Oct, which found no detectable difference by path length against human labels.
  - On 871 his direction appears at matched times, but his clock charges frontier for path waits that ASP never pays.
- **The fair statement.** We cannot say his numbers are wrong. We can say his 853 result does not hold in our runs, and that his released code times the two explorers differently, in ASP's favour, in a way the paper does not mention.

## How this was checked
Two independent Opus reviewers checked the 6 Nov page: one checked every number, and one checked every inference. The scorer `paper_compare.py` was checked by an independent recompute, which matched every number to within 0.0005.

## Sources
- `paper_compare.md` and `paper_compare.json` in this folder; the GED files in `ged/`.
- The rules in `../PREREGISTRATION_PAPER.md`, sha256 `fee16733…`, retaken at 17:59 on 6 Nov after a time-stamp fix, before any new data.
- The paper, arXiv 2510.05430v2, §IV-A and Fig. 4.

## Replaying the 6 Nov command
`paper_compare.json` `meta.argv` holds the command that produced these files. It has no `--out-dir`, which `paper_compare.py` now requires. Add `--out-dir <new directory>` when you replay it, so the frozen files here stay untouched.
