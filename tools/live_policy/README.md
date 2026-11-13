# tools/live_policy

Code, pre-registrations and results for the October-November live test of ASP (arXiv 2510.05430) and for the paper-scale comparison that followed. For the result, read `results_2026-10-31/WRITEUP.md` (E1-E3 and plan steps 6-8) and `results_paper_compare_1112/` (paper-scale scores). For current state, read `docs/STATUS_2026-11-12.md`.

## Folder map

| Path | What it holds |
|---|---|
| `live_policy.py`, `live_runner.py`, `run_live_run.sh` | The live arms (official, placebo, filter_only, oracle_visible) and the runner. |
| `build_oracle_sets.py`, `oracle_positive_control.py`, `oracle_sets.json`, `placebo_calibration.json` | E3 support and the placebo calibration. |
| `live_score.py`, `e1_analysis.py`, `stage_precision.py`, `stage_diagnostics.py`, `covariates.py`, `later_found.py`, `static_three_way.py`, `gemini_static*.py` | Scoring and analysis of E1-E3. |
| `build_results.py`, `extra_numbers.py`, `post_campaign_numbers.py`, `run_final_analysis.sh`, `reproduce.sh` | Build of the `results_2026-10-31/` package and its regeneration check. |
| `frontier_seeds_analysis.sh`, `determinism_check.py` | Plan steps 7 and 8. |
| `paper_compare.py`, `paper_ged.py` | Paper-scale scoring (F1 on the author's rules) and the GED run on the host. |
| `PREREGISTRATION_*.md`, `PREREGISTRATION_*.sha256` | Pre-registrations. Never edit them. See below. |
| `host/` | Scripts that ran on the GPU host, and `host/patches/` (opt-in patches to the author's code). Host runbook below. |
| `results_2026-10-31/` | The frozen E1-E3 package: `WRITEUP.md`, `DEVIATIONS.md`, `numbers.csv`, manifests, analysis, figures. Pinned by hash. |
| `review_2026-10-29/` | Review scripts and outputs for the same work. Cited by the package. Keep it beside `results_2026-10-31/`. |
| `results_paper_compare/` | The 6 Nov paper-scale scores and their reading (`NOTES.md`). Superseded by the folder below. |
| `results_paper_compare_1112/` | The 12 Nov paper-scale scores against the rebuilt reference: `paper_compare.md`, `.json`, `c_checks.json`, `ged/`, and `NOTES.md` (nine disclosures plus the frontier-clock note). Current. |
| `FINAL_PLAN_2026-10-29.md`, `OVERNIGHT_REPORT_2026-10-28.md`, `results_snapshot_2026-10-28.html` | The plan the campaign ran under, an overnight report and a snapshot page. Historical. |

`results_2026-10-31/` and `review_2026-10-29/` must stay side by side. The package cites files in the review folder (for example `review_2026-10-29/audit/tables/e3_ceiling_exact.json`, `review_2026-10-29/A/paths_pairs.json`), and its `scripts/` snapshot is a copy of code that sits here.

## Pre-registrations

Do not edit these files or their hashes. sha256 values below were computed on 12 Nov 2026 from the files in this folder.

| File | sha256 | Where it is pinned |
|---|---|---|
| `PREREGISTRATION_E1.md` | `19382f74483bab5bc059d6ce6b527349c7acb1e362b1764cc91f9130f3e062e1` | `results_2026-10-31/COPY_MANIFEST.sha256` (with its registration-time `.sha256`, kept off-host) and `results_2026-10-31/WRITEUP.md` §10 |
| `PREREGISTRATION_E2.md` | `2ef524028e51c14170389fc5ccea04e37f8b848c591c85298c04b3e57ae6dc15` | same |
| `PREREGISTRATION_E3.md` | `360d5d0357a1d55f052c944d756ab5da36af0ab9b948619e45e3dc7a78d63a85` | same |
| `PREREGISTRATION_BENCH.md` | `2571a7ef15f7a3bef974ef37f8fddcb964bfa2954d91f08d9a581d24af842f22` | `PREREGISTRATION_BENCH.sha256` (in this folder; written 29 Oct 22:28 IST) |
| `PREREGISTRATION_FRONTIER_SEEDS.md` | `c7ca42a198768f932ca53ab9395d33e4d73b7cf9ae33d679fff90c8e0dc9503d` | `results_2026-10-31/DEVIATIONS.md` item 36(b), which says it was frozen with its `.sha256`. That `.sha256` stayed on the host. |
| `PREREGISTRATION_DETERMINISM.md` | `56d69fb6971f16038e723dca33adea4ca0daf1f91eaf59477089ea41fec72e78` | `results_2026-10-31/DEVIATIONS.md` item 36(c), same wording. That `.sha256` stayed on the host. |
| `PREREGISTRATION_PAPER.md` | `1286c2c58f1019519dc16f4ab3ce02422f0ab30b73133482e8ddf62b06a05717` | `PREREGISTRATION_PAPER.sha256` (in this folder; retaken 13 Nov 17:54 IST with Amendment 2, before any third e7 871 attempt started. Before the amendment the hash was `fee16733…`, taken 6 Nov 17:59 IST) |

The hashes of the two `.sha256` files themselves are `0d56e166…` (BENCH) and `69bfa386…` (PAPER, after Amendment 2; `445d5e19…` before it). The E1-E3 `.sha256` files are listed in `results_2026-10-31/COPY_MANIFEST.sha256` as `runs/live_campaign/PREREGISTRATION_E{1,2,3}.sha256`; they exist only in the off-host copy of the campaign, not in this repository. Hashes of the host-only FRONTIER_SEEDS and DETERMINISM `.sha256` files: not verifiable from the repo.

## Deviation logs

Three logs. The first two are numbered separately; the third continues the first. An item number means nothing until you know which log it is in.

| Log | Items | Covers |
|---|---|---|
| `results_2026-10-31/DEVIATIONS.md` | 1-39 | Departures from the E1-E3 and step 6-8 pre-registrations. Hashed in `POST_CAMPAIGN_MANIFEST.sha256`. |
| `tyrone_mirror/DEVIATIONS.md` (repository root) | 1-93 | Departures from the author's documented setup (Sept to 9 Oct). November paper-scale departures are in `results_paper_compare_1112/NOTES.md` and end-sem plan §B7. |
| `DEVIATIONS_NOVEMBER.md` | 40 onward | Continues the first log's numbering. Departures from `PREREGISTRATION_PAPER.md`, the end-sem plan and `PREREGISTRATION_SEMANTIC.md`. |


## Host runbook

For the shared GPU host, where the pipeline ran. Facts here come from the host sessions of 3-12 Nov. Anything the repo cannot show is marked so. Never commit host names, addresses or credentials.

### Rules that held on 9-12 Nov
- A tour that hits the 4 h cap is a normal end (pre-registration §2b). The 80% waypoint rule decides later whether the tour is used. It must not stop the queue.
- `zstd` was approved after an apt dry run: it adds only `zstd` 1.4.4, matches the installed `libzstd1`, and upgrades nothing else. It is now installed in the container (12 Nov). Scoring reads only the YAML files, never the DSG JSON.

### Move a running process into its own scope
A queue started inside an agent session dies with it. This moves the oldest matching process into its own systemd scope. `pgrep -o` picks the oldest match because the queue's short-lived subshells carry the same command line.

```bash
PID=$(pgrep -o -u "$USER" -f '^bash paper_queue\.sh'); echo "pid: $PID"; cat /proc/$PID/cgroup
busctl --user status >/dev/null && echo user-bus-ok
busctl --user call org.freedesktop.systemd1 /org/freedesktop/systemd1 org.freedesktop.systemd1.Manager \
  StartTransientUnit 'ssa(sv)a(sa(sv))' paper-queue.scope fail 1 PIDs au 1 "$PID" 0
sleep 2; grep -q '/paper-queue\.scope$' /proc/$PID/cgroup && echo MOVED || echo NOT-MOVED
```

- Run the block only once. On `NOT-MOVED` or a `busctl` error, stop and report.
- Only the queue's own process moves. A `sleep` it had already started stays in the old scope until it ends (at most 5 minutes). Children started later land in the new scope.

### Traps (from `docs/STATUS_2026-11-12.md` §5)
- Run docker commands from a fresh ssh login (`ssh -o ControlPath=none <host>`), because older sessions lacked the docker group.
- Start long jobs with `systemd-run --user --scope`, not a plain `systemd-run --user` service. A service inherits the user manager's groups, which lack docker since the 11 Nov reboot. A scope keeps the caller's groups and still survives the session.
- The queue moves each old run folder aside as `*_FAILED_ATTEMPT_HHMM` before it reruns that job.
- `rospy.loginfo` output goes to the container's `/root/.ros/log/<uuid>/rosout.log`, not the run's `exploration_pipeline.log`.
- Run directories, `hm3d_refs_work/` and the old ledgers are root-owned (containers wrote them). Run host-side analysis inside `asp-noetic` with `/workspace/environments/semantic_perception/bin/python` and write through the container; check syntax with `ast.parse`, not `py_compile`.
- An unanchored `pgrep -f` inside `ssh '...'` matches the remote shell itself; anchor the pattern.
- The OpenRouter shim has two copies (the venv's site-packages copy is the one imported); update both. Stopping a run means killing every process in the container except PID 1, or workers keep calling the paid LLM. A failed `docker exec` must read as "unknown", never "gone".
- Host memory: the mapper grows about 4.5-8 GB per hour per run, so at most two runs fit at once (October DEVIATIONS items 7-10).
- Run the reruns with the reviewed queue's 12 GB GPU gate, so a returning vLLM server makes the queue wait rather than crash the runs. After each run, check its log for "out of memory" and check that its final graph differs from its first.

### State of the host (from the 3 Nov handoff; not verifiable from the repo)
- The host's `DEVIATIONS.md` matches the package (items 1-39). The off-host copy stops at item 35.
- The step 7 and step 8 DSG dumps on the host have no manifest. `HOST_MANIFEST.sha256` covers only the E1-E3 runs.
- The opt-in host patches stay applied: `ASP_START_JITTER_SEED` in `frontier_baseline.py`, and `ASP_DSG_QUIESCENT_S` and `ASP_DSG_QUIESCENT_MAX_S` in `exploration_pipeline.py`. With the variables unset, the author's behaviour is unchanged. The diffs are in `host/patches/`.
- DeepSeek on OpenRouter: $14.60 spent of a $40 allowance (per the runners' stop lines). Nothing enforces the rest. The key's $40 limit resets monthly. The runner's own cap (`CAP = 30` in `host/campaign_sched.py`) counts every run directory, so it leaves only about $15 for new paid runs. Raising it is a logged deviation. Check the spend by hand and ask before any paid call.
- `host/campaign_sched.py` still has `MAX_ACTIVE = 3`, a `POOL` naming containers that were deleted, a default `max_hours` of 7.5 and `CAP = 30.0`. Fix these before any reuse.

### Which scripts ran
| Script | Version | Where it is |
|---|---|---|
| `paper_queue_ctl.sh` v2 | sha256 `2b71ee2035eb10f755ff62f2aa8aa8bcca1efc1c1ce09bb7d7973f12439be83f`. Ran on 9 Nov (the handover at 17:52). | `host/paper_queue_ctl_v2_2b71ee20.sh` |
| `paper_queue_ctl.sh` v3 | sha256 `1fef22f7076838238aafc9f94821b7b08ae139eef1307c85c0d625ba79fd2c74`. Never run on the host. Adds: a tour at the 4 h cap counts as a normal end; `restart` uses `systemd-run --user --scope` and refuses to start without `zstd`. | `host/paper_queue_ctl.sh` (tests in `tools/tests/test_paper_queue_ctl.py`) |
| `paper_queue.sh`, old | sha256 `46f4d0d30a9db26fe51c5d98faf6c75405b7c4e6461ddeae91919d99da656468`. Ran before the 9 Nov fix. | Not in the repo. |
| `paper_queue.sh`, fixed | sha256 `6ffb56015253a361e1c4baf082a17364ae43bb8b9d75bff92bb2d1551848e253`. Ran after the 9 Nov fix: unbuffered Python output; only e7 jobs stop at 250 m; 12 GB GPU gate. | `host/paper_queue.sh` |
| `paper_queue.sh`, 5 GB gate | A variant used from 9 Nov 19:46, beside another user's vLLM server. It exists only on the host: the live `paper_queue.sh` there, which the rerun commands in `docs/STATUS_2026-11-12.md` §5 save as `paper_queue.sh.gate5gb` before they restore the reviewed 12 GB copy. Its hash is not verifiable from the repo. | Host only. |

The tour and frontier scripts that `paper_queue_ctl.sh` pins by hash (`coverage_tour.py`, `run_coverage_tour.sh`, `stop_coverage_tour.sh`, `run_frontier_seed.sh`, `tour_waypoints.py`) sit in `host/`. Do not edit them.

### Why the review scripts do not run from a clone
- Scripts in `review_2026-10-29/` read inputs from `/tmp/cvp_*` paths and from the off-host copy of the campaign. The `/tmp` files were lost when the laptop rebooted on 1 Nov (20:47). The off-host copy is a private 334 MB tree of maps, stats and logs, not in this repository.
- What was lost: the closeout-error checks, the stage-0 contamination check, the Astra and judge files, and the token and smoke scripts. Copies survive only in `review_2026-10-29/` and in `hm3d_refs_work/` on the host.
- Treat these scripts and their outputs as the record of how the review was done, not as a rerunnable pipeline. To rerun the main analysis, use `reproduce.sh` (needs the off-host copy).

## Reproduce

See `docs/REPRODUCE.md`, tier "October-November".
