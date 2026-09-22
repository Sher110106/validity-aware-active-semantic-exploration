# Prospective author overlay

This is a historical, hash-checked deployment surface. The campaign that used
it is frozen; the instructions below document provenance only and do not
authorize another run.

Routes the pinned `active_semantic_perception` pipeline's two Gemini-calling
methods (`LLMCompletion.generate_completion_response`,
`generate_refinement_response`) through the real, audited
`gemini_campaign` ledger via `prospective_runtime`, instead of an
unaccounted direct `google.genai` call reading `GOOGLE_API_KEY` straight
from the environment.

**The pinned checkout is never touched.** This overlay only ever gets
applied to a *sibling* checkout of the same pinned commit
(`f1ea141b1886d33ab8f4e4b791db4d3c92150b27`):

```sh
AC=/home/sher/active-semantic-perception-workspace/catkin_ws/src/active_semantic_perception
SIB=/home/sher/active-semantic-perception-workspace/catkin_ws/src/active_semantic_perception_prospective
git clone "$AC" "$SIB"
cd "$SIB" && git checkout f1ea141b1886d33ab8f4e4b791db4d3c92150b27
```

**A plain `git clone` + `checkout` is not enough by itself.** The pinned
checkout carries its own uncommitted, documented working-tree deviations
(`DEVIATIONS.md` #41/#42 and others -- crash fixes applied directly to the
live checkout, deliberately never committed, so the git commit stays a
clean provenance reference) -- that is the actual operative baseline the
pipeline runs with day to day, not `git show <pinned commit>` in
isolation. Before treating a fresh sibling clone as ready: `git status`/
`git diff HEAD` in the *pinned* checkout to see what's currently
uncommitted there, and copy those same files into the sibling (as of this
writing: `exploration/config/frontier_config.yaml`,
`exploration/config/pipeline_config.yaml`,
`mapping/clio/clio_ros/launch/realsense.launch` -- see
`PROSPECTIVE_SIBLING_NOTES.md` in the sibling itself for exactly when this
was last done and what was copied). `exploration/scripts/llm_completion.py`
does **not** need this same manual sync -- `pinned_reference/llm_completion.py`
in this overlay directory was already captured from that same live
working tree (hash `029d0413...`), not from the bare git commit, so it
already reflects those deviations; the overlay is built on top of it.

## What changed, and why only this

`tools/prospective_integration/overlay/exploration/scripts/llm_completion.py`
is the pinned file with five precise, mechanical edits (see
`pinned_reference/llm_completion.py` for the exact byte-for-byte pinned
baseline to diff against):

1. `LLMCompletion.__init__` gains three optional kwargs
   (`scene_index`, `ensemble_index`, `ledger_context`), defaulting to
   `None` so the non-LLM preprocessing use (`_preprocess_dsg`) is
   unaffected.
2. `generate_completion_response` builds the exact same prompt/YAML/image
   content the pinned code already assembled, then routes it through
   `prospective_runtime`'s `GeminiTransport` + `run_author_turns` (the
   `check_collision` tool loop, with the *same* `validate_feasibility`
   logic) via `LedgerBudgetBroker` backed by the real `gemini_campaign.Ledger`.
   Fails closed (`AccountingHalt`) if the overlay isn't configured --
   never silently falls back to an unaccounted call.
3. `generate_refinement_response` gets the same treatment for its single,
   tool-free call.
4. `LLMManager.complete_scene_graph`'s per-worker exception handling now
   recognizes `AccountingHalt`/`LedgerError` specifically and re-raises
   (cancelling any not-yet-started workers) instead of treating a ledger
   halt as "just another dropped ensemble member" -- the existing
   fail-soft per-member-drop behavior for every other exception type is
   unchanged.
5. `LLMManager._run_single_ensemble_member` passes `scene_index`/
   `ensemble_index` through to `LLMCompletion(...)`, and reads
   `LedgerContext.from_env()` fresh in that worker process (a `Ledger`'s
   sqlite3 connection can't be pickled across the `ProcessPoolExecutor`'s
   `spawn` boundary, so each worker opens its own connection to the same
   on-disk ledger file -- already proven safe for exactly this by
   `gemini_campaign`'s own concurrency tests).

Nothing else changes: `preprocess_file`, `search_nearest_room_node`,
`validate_feasibility`, `parse_response`, `FlowList`, and everything in
`_run_single_ensemble_member` besides the `LLMCompletion(...)` call are
byte-identical to the pinned commit.

## Deploying it

Dry-run first (hash-verifies only, copies nothing):

```sh
python3 -m prospective_runtime.deploy \
  --source tools/prospective_integration/overlay \
  --destination /home/sher/active-semantic-perception-workspace/catkin_ws/src/active_semantic_perception_prospective \
  --files exploration/scripts/llm_completion.py \
  --hashes tools/prospective_integration/overlay/manifest.json
```

Add `--apply` to actually copy once the dry run is clean. `deploy()`
refuses a destination that already exists (or is a symlink), and refuses
if the source file's hash doesn't match `manifest.json` -- re-run the hash
computation and update the manifest if `llm_completion.py` is edited.

## Required environment

Set once by whatever launches the pipeline for one prospective attempt
(same convention as `_asp_llm_logger.py`'s `ASP_LLM_LOG_DIR`):

| Variable | Meaning |
|---|---|
| `ASP_PROSPECTIVE_TOOLS_PATH` | Path to this checkout's `tools/` directory (defensive fallback if `PYTHONPATH` doesn't already include it) |
| `ASP_PROSPECTIVE_LEDGER_PATH` | Path to the run's isolated SQLite ledger file |
| `ASP_PROSPECTIVE_CREDENTIAL_PATH` | Path to the owner-only Gemini credential file |
| `ASP_PROSPECTIVE_CAMPAIGN_ID` | Campaign id for `gemini_campaign.Ledger.allocate()` |
| `ASP_PROSPECTIVE_ALLOCATION_ID` | The pre-registered block/pair allocation id |
| `ASP_PROSPECTIVE_RUN_ID` | This run's id |
| `ASP_PROSPECTIVE_PHASE_ID` | Optional, defaults to `engineering` |
| `ASP_PROSPECTIVE_MAX_OUTPUT_TOKENS` | Optional, defaults to `8192` |

If `ASP_PROSPECTIVE_LEDGER_PATH` is unset, the overlay's two Gemini methods
raise `AccountingHalt` immediately rather than making an unaccounted call.
If it's set but any other required variable is missing,
`LedgerContext.from_env()` raises `RuntimeError` at construction time --
also loud, never a silent fallback.

## What this does not cover yet

No live Gemini call has been made through this overlay. Before one is:
run the no-cost `countTokens`/request-shape checks, then the brokered
paid capability probe (<= $2), per the campaign's preregistered sequence.
