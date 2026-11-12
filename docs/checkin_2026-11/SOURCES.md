# Sources for check-in 2

Build: `uv run --with python-pptx python build_checkin2_pptx.py`. It reads the chart values from the files below. Render check: `soffice --headless --convert-to pdf ASP_Checkin2.pptx`.

Reviewed on 11-12 by an independent Opus reader against these files. Its findings were applied:
- the filter's sign;
- the unbounded exact-object interval;
- the old-figure correction;
- the titles and readings;
- the reference and budget caveats;
- the plan rows and costs.

| Slide | Number | Source |
|---|---|---|
| 2 | +0.013 (−0.012 to +0.040) | `tools/live_policy/results_2026-10-31/numbers.csv`: `E1:hm3d:60m:statistic`, `permutation_lo/hi` |
| 2 | −0.003 (−0.047 to +0.037), filter vs LLM | `numbers.csv` `E2:hm3d:60m:*`, sign flipped: E2 is registered as official − filter_only (`analysis/E2_hm3d_60m.json` `contrast`) |
| 2 | −0.012 (−0.053 to +0.029) | `numbers.csv`: `frontier_seeds:official:d60`, `ci60_lo/hi` |
| 2 | −0.025 (−0.050 to +0.002) | `numbers.csv`: `frontier_seeds:placebo:*` |
| 2 | +0.034, p 0.10, interval unbounded, all 3 beat all 3 | `numbers.csv` `E3:hm3d:60m:statistic`; WRITEUP §3 E3 table (per-run AUCs; "unbounded at this n") |
| 2 | +0.043, p 0.015, 0.09 after correction | WRITEUP §1 (E1 secondary, Holm over six) |
| 2 | LLM arm has 2 runs on 853 | `run_table.md` (e1_00853_s44_official excluded twice) |
| 2 | 3.0%, 0.5%, 76% beyond 2 m, about 6× | `numbers.csv`: `precision_pooled:official:final:0.5m` and `:2m`, `precision_pooled:placebo:final:0.5m` |
| 2 | 1.7% vs 1.5%; 2.1% vs 1.4% on 8 matched inputs | `docs/checkin/ASP_Checkin_Script.md` slide 2; WRITEUP §9 erratum 1; `docs/checkin/FABLE_REVIEW_2026-10-28.md` |
| 3 | every chart mark | `tools/live_policy/results_paper_compare_1112/paper_compare.json`, cells with reference `apr`, variant `B` (stage value); paper values from Fig. 4 left of arXiv 2510.05430v2 |
| 3 | 632 s and 809 s | `paper_compare.json` `meta.budgets` and `budget_sources`; rule in `PREREGISTRATION_PAPER.md` §4 |
| 3 | 85 and 66 stops; 32% and 21% | `apr_0085x_a/config/tour_summary.json`; `results_paper_compare_1112/c_checks.json` C3 |
| 3 | 5 of 5 on 853, 1 of 5 on 871; crashed twice | `results_paper_compare_1112/NOTES.md`; plan §B7 |
| 3 | 14 points; 38.7, 39.5, 43.9; 3 to 13; 14 to 16; 4 points | `paper_compare.json` apr cells for 00853 and 00871 (official, frontier_end, placebo) and paper values |
| 4 | "may contain more than one bedroom" | host `exploration/config/pipeline_config.yaml:101` |
| 4 | agreed guesses add nothing to the view score | `tools/live_policy/live_policy.py:18-22` |
| 4 | 44 inputs; about $320, cap $460 | `docs/ENDSEM_PLAN_2026-11-03.md` M0b item 4 and §5 |
| 5 | run `e1_00853_s42_official_60m`, stage 3, 8 members, home 853 | `figures/slices_numbers.json` (`run`, `stage`, `members`, `scene`), from `/Users/sher/cvp_live_campaign_copy/runs/live_campaign/<run>/stages/3/` |
| 5 | 10 mapped objects; the slices (panel 1) | `habitat_scene_graph_original_graph0.yaml` of that stage; `figures/make_slices.py`, z band 0.5 to 1.5 m, x/y top-down |
| 5 | 90 new guesses; 4 within 0.5 m; 20 within 2 m | `slices_numbers.json` (`new_guesses`, `within_0.5m`, `within_2m`); `habitat_scene_graph_new_graph_0..7.yaml` (`is_predicted` objects more than 0.5 m, x/y, from every observed object) against `hm3d_refs_work/00853_hm3d_reference.yaml` (same lower-case name, nearest, x/y). Counts are (member, guess) instances |
| 5 | 46 of 90 with no same-name real object in the house | `slices_numbers.json` `no_same_name_object_in_house`; exact name match only, no synonyms |
| 5 | toilet 0.4 m, nightstand 3.1 m, lamp 0.8 m | `slices_numbers.json` `examples`; picked by rule (first of each kind, common furniture first; the far example needs 3 to 6 m and a real object inside the frame) |
| 5 | 30 of 1230 within 0.5 m, 307 within 2 m, 15 stage-runs | `slices_numbers.json` `all_sample_stages`: stages 3, 8, 13 of the 5 counted DeepSeek runs (853 s42, s43; 871 s42, s43, s44), same rule |
| 5 | why this stage | first project sample stage of a run with a partial map (10 of 180 real objects) and visible guesses. Its 4 hits sit within the spread of the 15 stage-runs (0 to 5 within 0.5 m; `per_stage_run` in the JSON), so it is typical, not the best |

Rebuild the figures: `cd figures && uv run --with matplotlib --with pyyaml --with numpy python make_slices.py`.
