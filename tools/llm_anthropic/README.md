# llm_anthropic: the author's tool loop, on Claude

This folder replays saved scene-graph inputs through Claude Opus 5.5 (`claude-opus-5-5`) and Claude
Haiku 5.5 (`claude-haiku-5-5`). It ports the loop in
`tools/prospective_integration/overlay/pinned_reference/llm_completion.py`
(`generate_completion_response`). We did not patch his genai client.

| File | Job |
|---|---|
| `claude_loop.py` | `run_member`: one member. `prewarm`: write the cache for one input. |
| `author_tool.py` | The `check_collision` tool and its callback. Loads the author's `validate_feasibility`. |
| `meter.py` | Price table, cost per call, caps, `usage.jsonl`. |
| `claude_static.py` | The command line: replay many inputs. |
| `../tests/test_claude_loop.py` | Tests. A fake client; no network. |

## Run

    cd project
    # 1. check the requests, spend nothing (needs no key)
    .venv_offline/bin/python tools/llm_anthropic/claude_static.py INPUTS OUT --dry-run --order order.txt
    # 2. live run
    export ANTHROPIC_API_KEY=...        # read at run time; never printed, never written
    .venv_offline/bin/python tools/llm_anthropic/claude_static.py INPUTS OUT \
        --models haiku,opus --members 4 --concurrency 6 --prewarm --resume \
        --cap-model opus=280 --cap-model haiku=20 --cap-campaign 330 \
        --reserve opus=0.80 --reserve haiku=0.10 --admit opus=2.0 --admit haiku=0.15
    # what the author's file needs on this machine
    .venv_offline/bin/python tools/llm_anthropic/claude_static.py x y --check-author

A live run needs `--cap-run` or `--cap-campaign`. Run it outside the container's shared Python.
Do not set `ANTHROPIC_LOG`; leave debug logging off.

Tests: `.venv_offline/bin/python -m pytest tools/tests/test_claude_loop.py -q`

## Input format

One folder per input under `INPUTS`. The folder name is the input id.

    <id>/prompt.txt         the author's prompt, as he sends it
    <id>/graph.yaml         the YAML scene graph
    <id>/slices/*.jpg       exactly 6 JPEGs (`--expect-images 0` turns the count off)
    <id>/meta.json          {"run": .., "scene": .., "stage": .., "track": ..}

`--order FILE`: one input id per line, `#` starts a comment, a blank line ends a round. Inside a round,
models run in the `--models` order (Haiku first), and each round ends before the next starts, so a cap stop
leaves earlier rounds whole. Inputs missing from the file do not run (a warning names them).

## Output format

    OUT/<model>/<input>/member_<k>/record.json   the record
    OUT/<model>/<input>/member_<k>/final.txt     the final text (only if the member ended with text)
    OUT/usage.jsonl                              one line per call, kept across runs
    OUT/summary.json                             counts, warnings, spend

`record.json` holds: `status`, `final_text`, `dropped`, `turns`, `tool_rounds`, `calls` (per call: request id,
served model, stop reason, usage as input / cache write / cache read / output tokens, cost),
`request_ids`, `served_models`, `stop_reasons`, `stop_details`, `tool_calls` (name, input, result),
`responses` (every raw reply as JSON), `images` (name, bytes, sha256), `flags`, `cost_usd`, `settings`,
`meta` (run, scene, stage, track, feasibility function sha256).

Status. Final (resume skips it): `ok`, `truncated` (hit `max_tokens`; text kept), `dropped_turn_limit`,
`dropped_refusal`, `dropped_other_stop`, `dropped_empty`, `dropped_tool_error`, `dropped_member_cap`.
Open (resume runs it again from the start): `error`, `cap_stopped`.
`flags` includes `served_model_mismatch:<id>` when the API serves another model than we asked for.

`--resume` key: (model, input, member). Without `--resume`, a folder that holds finished members is refused.

## What the loop sends

- First user message: prompt text, YAML text, then the 6 JPEGs as base64 blocks, sorted by file name.
  Images go in this message only.
- Tool `check_collision` (`label`, `center_x`, `center_y`, `center_z`, `size_x`, `size_y`, `size_z`; names, order
  and description taken from the author's code), `strict: true`, `tool_choice` auto.
- `thinking: {"type": "adaptive"}`, `output_config.effort` always sent (default `medium`), `max_tokens` 64000.
  Thinking text is empty unless you pass `--thinking-display summarized`.
- History only grows. Each reply's blocks go back unchanged (thinking, text, tool_use). One user message
  carries one `tool_result` per `tool_use`, in order. Earlier messages are never rebuilt.
- Block binding: `thinking.block_binding.prefix_mismatch_behavior = "error"` under beta
  `thinking-binding-controls-2026-08-01`. If our history ever changed, the first call fails at once
  instead of silently losing the model's earlier reasoning. `--block-binding drop_block|off` changes it.
- Cache: one marker on the last image (covers the tool and the whole first message) and the top-level
  `cache_control` for the growing tail. Default lifetime 5 minutes (`--cache-ttl 1h` for 1 hour).
- Streaming; the final message is collected. Timeout 300 s, `max_retries` 3, one more try per turn if a
  stream breaks, and on 429 a wait of `retry-after` (or 2, 4, 8 ... s) that holds every worker.
- Pre-warm (`--prewarm`): one non-streaming request per input, `max_tokens: 0`, same tool, thinking, effort
  and first message, explicit marker only. Its members start after it ends. Each member's first call must
  read the cache; if not, the record gets `first_call_no_cache_read` and the summary warns.

## Meter and caps

Prices are in one table in `meter.py` with source and date (claude-api skill 2.1.322, 2026-11-13; not checked
against the live price page). Haiku 5.5 has a second card above 100K prompt tokens ($0.50 / $2.50 instead of
$0.10 / $0.50). We count prompt tokens as input + cache write + cache read. The skill does not say whether
cached tokens count; this is the safe reading.

Before each call the meter reserves an amount (`--reserve`, the measured p99 call cost). A call is refused
if settled spend + held reserves + this reserve passes a cap. Caps: member (`--cap-member`, else a default per
model), run (`--cap-run`), model (`--cap-model`, whole ledger) and campaign (`--cap-campaign`, whole ledger).
A call that breaks after the stream may have started is booked at its reserve, so the ledger can overstate.
A call the API rejects before it generates (429, 400) costs nothing.

A new member starts only if the caps leave room for it and for every member already running
(`--admit`, the expected cost of one member). A cap stop then falls between whole members. **Set `--admit` at
or above the real member cost.** If it is lower, a member can start and run out of room; it ends as
`cap_stopped`, its spend is booked, and resume runs it again.

The defaults for `--reserve`, `--admit` and the member cap are placeholders. Replace them with the numbers
from the smoke test.

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
| tool result is a dict | the same dict as JSON text; `is_error` set for his two `{"error": ..}` answers | The API wants text. Numbers go through `float()` as he gets floats from genai. |
| 50 rounds, then returns `None` | 50 rounds, then `dropped_turn_limit` | Same tool calls. He makes one more call and discards it; we skip that call. |
| no refusal case | refusal drops the member; the stop details are logged | No fallback model: the plan names the model. The skill's usual advice (opt in to `fallbacks`) is not followed. Haiku 5.5 has no fallback anyway. |
| `eager_input_streaming` | off | The skill turns it on by default, but it also turns off the API's check of tool input, which `strict` gives us. Seven small values gain nothing from it. |

`validate_feasibility` is his code, used as written. His file does not import on a laptop (it needs
`google.genai`, `spark_dsg`, `bidict` and `scene_graph_visualize_2d` at module level). `author_tool.py` reads the
file with `ast`, takes that one function, and runs it with only numpy and json. It records the sha256 of the
function source in each record. `parse_response` lives in the same module and needs the same four imports,
so this folder does not call it; it saves the final text and stops there.

## Not confirmed from the skill

- Image token cost for Haiku 5.5 and Opus 5.5 on our slices. The skill gives rules of thumb only
  (about 1 token per 28x28 patch; up to 4,784 tokens per image on high-resolution models). Measure it with
  `count_tokens` or the smoke test.
- Image size and count limits per request.
- Rate limits per tier for either model (the skill points to a page we cannot fetch offline).
- Whether the Haiku 100K step counts cached tokens, and whether 100K means 100,000.
- Whether `max_tokens: 0` is accepted with `block_binding` and the beta header. If the pre-warm fails, the
  input is skipped and the summary says why; run without `--prewarm` or with `--block-binding off` to compare.
- The default `reserve`, `admit` and member caps.
