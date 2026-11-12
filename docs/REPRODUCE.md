# Reproduce and inspect

"Offline" below means no simulation run and no provider call after setup. Installing dependencies may still use a package index.

Use one interpreter consistently: `.venv_offline/bin/python`. Scripts need `PYTHONPATH=tools`; pytest gets it from `pytest.ini` (`pythonpath = tools`).

## Environment

The offline tools require Python 3.10+ and the packages in
`tools/asp_offline/requirements.txt`. `networkx`, `scipy` and `requests` must be installed: without `scipy` and `requests`, some test files fail at import (`test_decision_replay.py`, `test_openrouter_shim_metering.py`). A local setup is:

```sh
python3 -m venv .venv_offline
.venv_offline/bin/python -m pip install -r tools/asp_offline/requirements.txt pytest
```

## Tier 1: inspect published results (no code needed)

Read the frozen numbers and their provenance:

- `docs/RESULTS.md` for the run inventory and per-scene sources.
- `tyrone_mirror/runs/matrix120m_scoring/STATIC_REPLAY_SHA256SUMS` for the matrix replay digests.
- `docs/audit/2026-09-26-ledger-summary.json` for sanitized cost aggregates.
- `docs/ARCHITECTURE.md` for which evaluator each table uses.
- `docs/audit/2026-09-27-input-manifest.json` and `2026-09-27-input-SHA256SUMS` for file-level input provenance and local/host availability.

## Tier 2: run the fixture test suite

From the repository root:

```sh
.venv_offline/bin/python -m pytest
.venv_offline/bin/python -m compileall -q tools
```

`pytest.ini` collects every test under `tools/`: 470 tests with `requests` installed, of which 453 pass and 17 skip (checked 12 Nov 2026); without it, collection stops at `test_openrouter_shim_metering.py`. Tests use local fixtures and mocks; they start no pipeline and call no provider. The September run of 27 Sep (286 tests, six suites) predates the October-November tests and is out of date.

Caveats:

- `tools/gemini_campaign` summary/export/checksum commands open the ledger database, which can create, initialize, or chmod the file and enable WAL. They are offline but not filesystem-read-only. Point them at a copy if the original must stay untouched.
- The matrix supervisor `--check` and `--once --dry-run` modes inspect a host; plain `--once` and `--daemon` can act on processes and containers. Do not run them against a live host as a "test".
- `tools/prospective_runtime/run_campaign.py` refuses live mode without audited contracts; default invocation is a dry run.

## Tier 3: replay locally included artifacts

These commands read cached graphs and write new output files beside them. They need the referenced inputs to exist locally; the mirror does not contain every host-side corpus (see `docs/RESULTS.md`, input availability).

```sh
PYTHONPATH=tools .venv_offline/bin/python tools/evaluator/evaluate_run.py \
  --run <run>/stages \
  --gt <reference>/stages/<checkpoint>/habitat_scene_graph_original_graph0.yaml \
  --out eval_results.json
```

This scores the tracked graph produced by the author pipeline. It does not merge LLM completions into the tracked graph. It emits per-stage metrics, not its own AUC summary.

```sh
PYTHONPATH=tools .venv_offline/bin/python tools/extension_policy_replay.py \
  --run <run>/stages \
  --reference <reference>/stages/<checkpoint>/habitat_scene_graph_original_graph0.yaml \
  --budget-m 120 \
  --output extension_policy_replay.json
```

The four-member denominator is explicit. Read `calibration.status` before interpreting calibrated rows. References outside the four known `/workspace/...` calibration paths yield `UNCALIBRATED_PROVISIONAL`.

```sh
PYTHONPATH=tools .venv_offline/bin/python tools/decision_replay.py \
  --scene-id 00069 \
  --run <run>/stages \
  --reference <reference>/stages/<checkpoint>/habitat_scene_graph_original_graph0.yaml \
  --out-dir <new-output-dir> \
  --out-filename decision_replay.json

PYTHONPATH=tools .venv_offline/bin/python tools/phase13_diagnostics.py \
  --workspace-root <workspace> \
  --output-dir <new-output-dir>
```

Decision replay is a fixed-pose approximation. It does not claim reachability, detour, path-length, or collision outcomes. It also needs the four-scene calibration corpus, not just `--run`. Phase 13 requires the fixed workspace layout and refuses existing designated outputs.

## Tier 4: host-only regeneration

Full DeepSeek Phase 13 regeneration needs the four calibration corpora, three matrix run directories, frontier references, and frozen static/decision results. Its request-count and timing diagnostics also read host-private `prompts/prompts_responses.jsonl` files, whose contents are not exported here. Gemini v6 rescoring separately needs its own stage graph corpus. These inputs are not all in the mirror.

The [file-level manifest](audit/2026-09-27-input-manifest.json) records relative paths, sizes, SHA-256 hashes, missing graph slots, and local-copy status. The [checksum list](audit/2026-09-27-input-SHA256SUMS) uses paths relative to the original workspace root. On an existing exported workspace, this checks bytes without invoking an evaluator:

```sh
cd <exported-workspace-root>
sha256sum --check <repository-root>/docs/audit/2026-09-27-input-SHA256SUMS
```

Missing host-only files will fail this check in a partial export. Three host source files differ from the local repository; both digests are recorded. Preserve the chosen source version before any future reproduction rather than treating the two trees as interchangeable. This closeout generated hashes only, not new analysis results.

## Tier 5: October-November work (live policy and paper scale)

Code and results are in `tools/live_policy/`; read `tools/live_policy/README.md` first.

1. **Regenerate the E1-E3 package** (needs the off-host copy of the campaign, which is not in this repository; see the README):
   ```sh
   tools/live_policy/reproduce.sh [copy_dir] [expected_dir] [out_dir]
   ```
   It rebuilds `all_scores.json` and the E1-E3 analysis JSONs and compares them with `results_2026-10-31/analysis/`.
2. **Check the manifests.** `results_2026-10-31/COPY_MANIFEST.sha256`, `POST_CAMPAIGN_MANIFEST.sha256` and `HOST_MANIFEST.sha256` list sha256 values. Lines that start with `runs/` need the off-host copy or the host. The 12 package lines of `POST_CAMPAIGN_MANIFEST.sha256` check from `results_2026-10-31/`. `numbers.csv` has CRLF line endings; its hash only holds if git does not convert them. Check `PREREGISTRATION_BENCH.sha256` and `PREREGISTRATION_PAPER.sha256` from `tools/live_policy/`.
3. **Rescore paper-scale runs.** `paper_compare.py` needs an explicit `--out-dir`, so a rerun never overwrites a frozen results folder:
   ```sh
   PYTHONPATH=tools .venv_offline/bin/python tools/live_policy/paper_compare.py \
     --out-dir <new directory> --no-default-runs \
     --add-run frontier_end=00853=<run dir> --apr 00853=<apr dir> --budget 00853=<seconds>
   ```
   The exact argument list of each published table is in `meta.argv` of its `paper_compare.json`. Add `--out-dir` when you replay the 6 Nov one (`results_paper_compare/`), which predates the flag, and replace the 12 Nov argv's `--out-dir` with a new directory so the frozen folder is not overwritten.
4. **GED runs on the host only.** `tools/live_policy/paper_ged.py` calls the author's `ged_score_plot.py` and gmatch4py, which are not in `.venv_offline`. Its output (`ged/*.json`) is passed to `paper_compare.py` with `--ged-json`. Without it every `ged` field is null.
5. **Live-policy tests.** `tools/tests/test_live_policy.py`, `test_e1_analysis.py`, `test_live_runner.py`, `test_paper_compare.py` and `test_paper_queue_ctl.py` run under the plain pytest command above. `test_coverage_tour.py` reads the author's scripts from `/tmp/asp_author_scripts` or from the path in `ASP_AUTHOR_SCRIPTS`. Without them its 17 tests skip.
6. **Step 7 rerun.** `bash tools/live_policy/frontier_seeds_analysis.sh <copy> /tmp/fc; diff -rq /tmp/fc tools/live_policy/results_2026-10-31/frontier_seeds` (the script is not executable and does not compare by itself); expect only `wall_cells.json` to differ.
7. **Host steps** (queue, tours, zstd, systemd scopes) are in the "Host runbook" of `tools/live_policy/README.md`. They need the GPU host.

## Evidence policy

Do not commit credentials, live ledgers, raw provider request bodies, or machine-specific paths. Keep new results in a unique evidence directory, add a row to `docs/RESULTS.md`, and record material deviations in `tyrone_mirror/DEVIATIONS.md`.
