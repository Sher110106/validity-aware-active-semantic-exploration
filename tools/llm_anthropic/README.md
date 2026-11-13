# llm_anthropic: the author's tool loop, on Claude

This folder replays saved scene-graph inputs through Claude Opus 5.5 (`claude-opus-5-5`) and Claude
Haiku 5.5 (`claude-haiku-5-5`). It ports the loop in
`tools/prospective_integration/overlay/pinned_reference/llm_completion.py`
(`generate_completion_response`). We did not patch his genai client. The registered rules for the replay
are in `tools/live_policy/PREREGISTRATION_SEMANTIC.md` §12.

| File | Job |
|---|---|
| `claude_loop.py` | `run_member`: one member. `prewarm`: write the cache for one input. `make_client`. |
| `author_tool.py` | The `check_collision` tool and its callback. Loads the author's `validate_feasibility`. |
| `meter.py` | Price table, cost per call, caps, the round projection, the ledger. |
| `claude_static.py` | The command line: replay many inputs. |
| `../tests/test_claude_loop.py` | Tests. A fake client, and a real SDK client over a recording transport. No network. |

## Run

    cd project
    # 1. check the requests and the round plan; spend nothing; needs no key
    .venv_offline/bin/python tools/llm_anthropic/claude_static.py INPUTS OUT --dry-run --order sample_frame.txt
    # 2. live run (the key comes from the environment; it is never printed or written)
    env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_CUSTOM_HEADERS \
      .venv_offline/bin/python tools/llm_anthropic/claude_static.py INPUTS OUT \
        --models haiku,opus --members 4 --concurrency 6 --prewarm --resume --order sample_frame.txt \
        --cap-model opus=280 --cap-model haiku=20 --cap-campaign 330 \
        --reserve opus=1.5 --reserve haiku=0.35 --admit opus=<measured> --admit haiku=<measured>
    # what the author's file needs on this machine
    .venv_offline/bin/python tools/llm_anthropic/claude_static.py x y --check-author

A live run needs `--cap-run` or `--cap-campaign`. Run it outside the container's shared Python.
Leave `ANTHROPIC_LOG` unset.

Tests: `.venv_offline/bin/python -m pytest tools/tests/test_claude_loop.py -q`

### Where the key goes

The client is built as `Anthropic(api_key=..., base_url="https://api.anthropic.com", max_retries=0)`. It never
reads `ANTHROPIC_BASE_URL` or `ANTHROPIC_AUTH_TOKEN` (this machine's shell sets both, for a local gateway).
The SDK does read `ANTHROPIC_CUSTOM_HEADERS` and we cannot switch that off, so `main` refuses to run if it is
set and non-empty, and refuses if `client.base_url` does not start with `https://api.anthropic.com`. Start live
runs with `env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_CUSTOM_HEADERS` as above.
`--ipv4` connects from `0.0.0.0` so the socket uses IPv4. It is off by default. It swaps in a custom httpx
transport, which makes httpx ignore proxy environment variables. The tests check that the client builds with
it; they cannot check the connection itself without a network.

### One process per OUT_DIR and ledger

`main` takes an exclusive lock on `OUT_DIR/.lock` and on `<ledger>.lock` for the life of the process. A second
process that meets either lock stops with a message. Runs that share a campaign cap share one ledger: pass the
same `--ledger` to each; run them one after another.

## Input format

One folder per input under `INPUTS`. The folder name is the row id.

    <id>/prompt.txt         the author's prompt, as he sends it
    <id>/graph.yaml         the YAML scene graph
    <id>/slices/*.jpg       exactly 6 JPEGs (`--expect-images 0` turns the count off)
    <id>/meta.json          {"run": .., "scene": .., "stage": .., "track": ..}

`--order FILE` has the format of `tools/live_policy/semantic/sample_frame.txt`: a comment line that starts
`# Round N` opens a round; every other non-blank line is `<row_id> <run_dir> <stage>`. The row id must be an
input; the last part of `run_dir` and the stage must match that input's `meta.json`. Other comment lines are
ignored. Inputs missing from the file do not run (a warning names them). Without `--order`, all inputs form one
round.

## Rounds and stops

Rounds run in order. Inside a round the models run in the `--models` order (Haiku first), and one model's
members all finish before the next model starts. Members of one model run in a pool of `--concurrency` workers.

- Before each (round, model), the meter computes projected cost = members still to run in that round x the
  model's `--admit` cost (the measured cost per member). If that is more than what is left under the model's
  caps (model, run, campaign), the model stops before the round, the log says so, and `summary.json` lists it
  under `round_skips`. The other model goes on. A stopped model stays stopped for the later rounds, so the
  set stays balanced. Resumed members cost nothing and are left out of the count.
- A cap of scope "model" (`--cap-model`) stops that model only. A "run" or "campaign" cap stops everything.
  A member cap (`--cap-member`, else a default per model) ends only that member.
- A new member starts only if the caps leave room for it and for every member already running. If the
  `--admit` value is lower than the real member cost, a member can start and run out of room.

## Output format

    OUT/<model>/effort_<effort>/<input>/member_<k>/record.json   the record
    OUT/<model>/effort_<effort>/<input>/member_<k>/final.txt     the final text (status ok only)
    <ledger>                                      one line per call (default OUT/usage.jsonl), kept across runs
    OUT/summary.json                              counts, round skips, stops, warnings, spend

The effort is part of the path, so a run at another effort is new work and never overwrites or resumes an old
one. `--resume` also checks the effort saved in each record. Resume key: (model, effort, input, member).
Without `--resume`, a folder that holds finished members at this effort is refused.

`record.json` holds: `status`, `final_text`, `dropped`, `turns`, `tool_rounds`, `calls` (per call: request id,
served model, stop reason, usage as input / cache write / cache read / output tokens, cost), `request_ids`,
`served_models`, `stop_reasons`, `stop_details`, `tool_calls` (name, input, result), `responses` (every raw
reply as JSON), `images` (name, bytes, sha256), `flags`, `cost_usd`, `settings`, `error`, `meta` (run, scene,
stage, track, feasibility function sha256).

### Statuses

Final (a resume does not run the member again):

| Status | Meaning |
|---|---|
| `ok` | Ended with text. Cut-off text carries the flag `stop_max_tokens`; empty text carries `empty_text`. We do not judge the text. The author's parser drops what does not parse. |
| `dropped_refusal` | The API refused (`stop_reason: refusal`). `stop_details` is logged. No fallback model. |
| `dropped_turn_limit` | 50 rounds of tool calls without a final text. |
| `dropped_error` | Still failing after 3 retries of a transient error (429, 408, 409, 5xx, timeout, broken stream); or an unexpected stop reason; or the tool callback raised (his pipeline loses the member there too). |

Unfinished (a resume runs the member again from the start):

| Status | Meaning |
|---|---|
| `cap_stopped` | A cap refused a call. This includes the member cap. Spend so far is in the ledger. |
| `error` | The API rejected our request (400, 401, 403, 404, 413, 422) or we hit an unexpected exception. These are faults of ours, not of the member, and are not billed. |

A process that is killed leaves no record, so its member is unfinished too.
`flags` may hold `served_model_mismatch:<id>`, `retry_turn_<n>`, `first_call_no_cache_read`,
`input_transformations_turn_<n>`.

## What the loop sends

- First user message: prompt text, YAML text, then the 6 JPEGs as base64 blocks, sorted by file name.
  Images go in this message only.
- Tool `check_collision` (`label`, `center_x`, `center_y`, `center_z`, `size_x`, `size_y`, `size_z`; names, order
  and description taken from the author's code), `strict: true`, `tool_choice` auto.
- `thinking: {"type": "adaptive"}`, `output_config.effort` always sent (`--effort`, default `medium`),
  `max_tokens` 64000. Thinking text is empty unless you pass `--thinking-display summarized`.
- History only grows. Each reply's blocks go back unchanged (thinking, text, tool_use). One user message
  carries one `tool_result` per `tool_use`, in order. The result is his dict as JSON text and nothing else:
  no `is_error` flag. Earlier messages are never rebuilt.
- Block binding: `thinking.block_binding.prefix_mismatch_behavior = "error"` under beta
  `thinking-binding-controls-2026-08-01`. If our history ever changed, the first call fails at once
  instead of silently losing the model's earlier reasoning. `--block-binding drop_block|off` changes it.
- Cache: one marker on the last image (covers the tool and the whole first message) and the top-level
  `cache_control` for the growing tail. Default lifetime 5 minutes (`--cache-ttl 1h` for 1 hour).
- Streaming; the final message is collected. Timeout 300 s. Retries are ours alone (the SDK's are off): any
  transient error is retried up to 3 times, waiting `retry-after` or 2, 4, 8 s; a 429 holds every worker.
  A call that breaks mid-stream is booked at the larger of its reserve and the usage seen so far.
- Pre-warm (`--prewarm`): one non-streaming request per input, `max_tokens: 0`, same tool, thinking, effort
  and first message, explicit marker only. Its members start after it ends. Each member's first call must
  read the cache; if not, the record gets `first_call_no_cache_read` and the summary warns.

## Meter

Prices are in one table in `meter.py` with source and date (claude-api skill 2.1.322, 2026-11-13; not checked
against the live price page). Haiku 5.5 has a second card above 100K prompt tokens ($0.50 / $2.50 instead of
$0.10 / $0.50). We count prompt tokens as input + cache write + cache read. The skill does not say whether
cached tokens count; this is the safe reading.

Before each call the meter reserves an amount (`--reserve`; defaults Opus $1.50, Haiku $0.35, above a bad
call). A call is refused if settled spend + held reserves + this reserve passes a cap. A call the API rejects
before it generates costs nothing. A call that breaks mid-stream is booked at the larger of the reserve and its
usage, so the ledger can overstate. The defaults for `--admit` and the member cap are placeholders ($2.00 and
$8.00 on Opus; $0.20 and $0.80 on Haiku). Replace `--admit` with the measured cost per member from the smoke
test; it also feeds the round projection.

## How this differs from the author's loop, and why

| Author | Here | Why |
|---|---|---|
| `temperature=0.2` | none | Opus 5.5 and Haiku 5.5 reject sampling parameters. |
| a `seed` argument that he stores but never sends | none | The API has no seed. |
| `thinking_budget=-1` (dynamic) | adaptive thinking, effort `medium` | A budget is a 400 on both models. Effort is the control. |
| function mode `VALIDATED` | `strict: true`, `tool_choice` auto | Forced tool choice is a 400 on Opus 5.5. |
| images in `iterdir()` order | sorted by file name | His order is the file system's. Sorting makes the cache prefix repeat. |
| no `max_tokens` | 64000 | The API needs one. |
| `response.text` | text blocks joined in order | Same meaning. |
| tool result is a dict | the same dict as JSON text, arguments passed on as sent | The API wants text. Integers stay integers; the parity test compares exactly. |
| 50 rounds, then returns `None` | 50 rounds, then `dropped_turn_limit` | Same tool calls. He makes one more call and discards it; we skip that call. |
| no refusal case | refusal drops the member; the stop details are logged | No fallback model: the plan names the model. The skill's usual advice (opt in to `fallbacks`) is not followed. Haiku 5.5 has no fallback anyway. |
| no retry | up to 3 retries of a transient error, then a counted drop | §12. |
| `eager_input_streaming` | off | The skill turns it on by default, but it also turns off the API's check of tool input, which `strict` gives us. Seven small values gain nothing from it. |
| IPv4 | an opt-in flag, `--ipv4` | See above. |

`validate_feasibility` is his code, used as written. His file does not import on a laptop (it needs
`google.genai`, `spark_dsg`, `bidict` and `scene_graph_visualize_2d` at module level). `author_tool.py` reads the
file with `ast`, takes that one function, and runs it with only numpy and json. It records the sha256 of the
function source in each record. `parse_response` lives in the same module and needs the same four imports,
so this folder does not call it; it saves the final text and stops there.

## Smoke test (28 members, cap $30 in all)

Three runs, each in its own folder, sharing one ledger so the $30 cap spans them: Haiku at `medium` (3 inputs x
4 members), Opus at `medium` (3 x 4), Opus at `low` on `smoke_00871_s44_official_st17` only (4). Put
`--dry-run` first, read the output, then run the same line without it. See the report for the exact lines.

## Not confirmed from the skill

- Image token cost for Haiku 5.5 and Opus 5.5 on our slices (each slice is about 0.7 MB; the request bodies are
  4.5 to 6 MB). The skill gives rules of thumb only (about 1 token per 28x28 patch; up to 4,784 tokens per
  image on high-resolution models). Measure it in the smoke test.
- Image size and count limits per request.
- Rate limits per tier for either model (the skill points to a page we cannot fetch offline).
- Whether the Haiku 100K step counts cached tokens, and whether 100K means 100,000.
- Whether `max_tokens: 0` is accepted with `block_binding` and the beta header. If the pre-warm fails, the
  input is skipped and the summary says why; run without `--prewarm` or with `--block-binding off` to compare.
- The default `--admit` and member caps.
