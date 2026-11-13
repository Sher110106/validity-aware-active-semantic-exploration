# DRAFT of Amendment 3 to PREREGISTRATION_PAPER.md (ASP on 853 to the full budget)

Not in force. This text is appended to `PREREGISTRATION_PAPER.md`, with the time and what had been seen filled in, and the file is hashed and pushed, before the dry run of §A3.5 starts. The student approved the runs on 11-13.

## Amendment 3 (date and time to be filled in, before any run below has started)

**Why.** §4 says "ASP runs stopped at 60 m, so they have no 100% value". So the paper's headline column (ASP at 100% of the budget) has no ASP value of ours beside it. Three new ASP runs on 00853 fill that cell. They are descriptive, like the rest of this file.

**What had been seen when this was written.** Every October result, among them the 853 readouts at 10% and 50% of B for ASP, the placebo and frontier (`results_paper_compare_1112/paper_compare.md`), and the frontier-to-end values at 100%. (To be completed at the time of hashing.)

**A3.1 Runs.** `e8_00853_s<seed>_official_105m`, seeds 42, 43 and 44, one at a time in container asp-noetic, in that order.
- The arm is E1's official arm, with the same files as E1 ran: the author's pipeline at f1ea141b; `live_policy.py` (sha256 6e4710cf…), `run_live_run.sh` (25cfe606…), `live_runner.py` (940be66b…) as they stand on the host; model `deepseek/deepseek-v4.1-flash-1017` on OpenRouter, pinned to DeepInfra fp8, no fallback, reasoning effort low, max_tokens 16,000. The quiet-wait option of the determinism step is left unset.
- Target path 105 m, so that navigation time passes B for 853 (632.18 s; October's official runs moved at 6.4 to 6.7 s per metre). The runner stops at the first checkpoint at or past 105 m.
- Limits: 12 h per run; $3 per run; the launcher's 3,000-call cap, unchanged (October's 60 m runs used 1,022 to 1,362 calls).
- The scheduler of October is not used. The runner is started by hand, once the rerun queue has ended, nothing else runs in the container, and at least 12 GB of GPU memory is free.

**A3.2 Which runs count.** A run counts at 100% of B if its navigation time reached B, its `logs/roslaunch.log` holds no "out of memory" line and no line saying `nvblox_node` has died, and no E1 exclusion applies (a call not served by DeepInfra with the pinned model; more than half the members dropped). A run that ends before B, whatever the reason, has no 100% value and is reported with the values it has. There is no rerun of any kind.

**A3.3 Readouts.** §4's, at 10%, 50% and 100% of B = 632.18 s (fixed on 11-12 from the five e7 runs on 853; Amendment 2 does not change it): F1 as the stage value and as the running maximum, and GED with the author's code. One row, "ASP + DeepSeek, November", with mean, min, max and n. No p-value.

**A3.4 Not pooled.** The three runs are never pooled with October's official runs, whose rows at 10% and 50% stay as they are. The slide gives n beside every cell.

**A3.5 Dry run.** One run of 5 m (`dryrun_e8_00853_s42_official_5m`, cost limit $0.30) checks the stack after the reboot of 11-11. It is not scored.

**A3.6 Not run.** 00871: its budget is not yet fixed and its runs are longer.

**Not changed.** §1 to §3, the readouts of §4, and Amendments 1 and 2.
