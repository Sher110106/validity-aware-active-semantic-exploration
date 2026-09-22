"""
OpenRouter backend for the ASP exploration pipeline's LLM calls, used as a
fallback when the Gemini API key has no usable quota (see DEVIATIONS.md
deviations #20-22 on tyrone). NOT part of the pinned active_semantic_
perception checkout - loaded by _asp_llm_logger.py, which already patches
google.genai.models.Models.generate_content for logging; when
ASP_LLM_PROVIDER=openrouter is set, that same patch point calls into this
module instead of the real Gemini backend, translating the exact same
request/response shapes llm_completion.py already uses. llm_completion.py
itself is never touched - it still thinks it's talking to google.genai.

Why this shape: llm_completion.py builds its tool-calling loop entirely
against google.genai's Chat/Content/Part objects and response accessors
(response.text, response.candidates[0].content.parts[].function_call).
Rather than editing that loop to know about two providers, this module
receives the exact same REAL google.genai Content/Part objects the Chat
class constructs internally (confirmed by reading google/genai/chats.py:
Chat.send_message always calls generate_content with
contents=self._curated_history + [input_content], so this function sees
full real Content objects, not raw strings) and fabricates a response
object that duck-types as a google.genai response, so nothing downstream
needs to know a swap happened.

Model: deepseek/deepseek-v4.1-flash (confirmed via OpenRouter's /models
endpoint: text+image input, tools/tool_choice supported, $0.00000015/
prompt token - the cheapest vision-capable, non-experimental DeepSeek
model available, per the user's explicit "cheap models... support visual
input" instruction). Override via ASP_OPENROUTER_MODEL if needed.
"""
from __future__ import annotations

import base64
import inspect
import json
import os
import socket
import sys

import requests
import urllib3.util.connection as _urllib3_connection

# 2026-09-13: root-caused a large chunk of this session's "OpenRouter
# call flakiness" (ReadTimeout, ConnectionError, "Temporary failure in
# name resolution") down to tyrone's container having NO working
# outbound IPv6 route at all - `curl -6 openrouter.ai` fails instantly
# (HTTP 000) while `curl -4` succeeds in ~0.08s. openrouter.ai's DNS
# sometimes hands back an AAAA (IPv6) record, and plain `requests`/
# urllib3 has no Happy-Eyeballs-style fallback - it just tries
# whichever address family `socket.getaddrinfo` returns, so a subset of
# calls land on the broken IPv6 path and hang until timeout instead of
# ever reaching the working IPv4 one. Forcing IPv4-only here is the
# standard, minimal fix for this exact class of problem (override
# urllib3's own address-family selector) - it eliminates a whole
# category of failure at the root rather than retrying through it.
# Scoped to this module's own `requests` usage only (module-level
# monkeypatch of urllib3, which every `requests` call in this process
# goes through) - does not touch pinned code or any other process.
def _allowed_gai_family_ipv4_only():
    return socket.AF_INET


_urllib3_connection.allowed_gai_family = _allowed_gai_family_ipv4_only

OPENROUTER_MODEL = os.environ.get("ASP_OPENROUTER_MODEL", "deepseek/deepseek-v4.1-flash")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_TYPE_MAP = {str: "string", float: "number", int: "integer", bool: "boolean"}


def _function_to_openai_tool(fn):
    sig = inspect.signature(fn)
    properties = {}
    required = []
    for name, param in sig.parameters.items():
        json_type = _TYPE_MAP.get(param.annotation, "string")
        properties[name] = {"type": json_type}
        required.append(name)
    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": (fn.__doc__ or "").strip(),
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


def _part_text(part):
    if isinstance(part, str):
        return part
    return getattr(part, "text", None)


def _part_image_data_url(part):
    inline_data = getattr(part, "inline_data", None)
    if inline_data is None:
        return None
    data = getattr(inline_data, "data", None)
    if data is None:
        return None
    mime_type = getattr(inline_data, "mime_type", "image/jpeg") or "image/jpeg"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def _content_items(contents):
    """Normalize `contents` (either a list of real types.Content objects
    with .role/.parts, as Chat always sends, or a flat list of raw
    str/Part items with no Content wrapper, as the non-chat
    generate_refinement_response call sends) into a uniform list of
    (role, [parts]) tuples."""
    if not isinstance(contents, (list, tuple)):
        contents = [contents]

    # Detect the Chat case: every item has .role and .parts.
    if contents and all(hasattr(c, "role") and hasattr(c, "parts") for c in contents):
        return [(c.role, list(c.parts)) for c in contents]

    # Flat case: one synthetic "user" turn containing everything.
    return [("user", list(contents))]


def _translate_to_openai_messages(contents):
    """Walk the full contents (whole curated history each time, per
    Chat.send_message) and produce OpenAI-format messages. Tool-call IDs
    are assigned by a FIFO queue local to this one pass, not persisted
    across calls: each function_call increments a counter and enqueues
    its id, each function_response dequeues the next pending id in order
    (the real code always sends responses back in the same order calls
    were made - see llm_completion.py's tool loop). Since the full
    history is reprocessed from scratch on every generate_content call
    and walked in the same order every time, the same call/response pair
    always gets matched to the same id without needing any state to
    survive between calls.
    """
    messages = []
    pending_call_ids = []  # FIFO: ids of calls not yet matched to a response
    call_counter = [0]

    for role, parts in _content_items(contents):
        text_chunks = []
        image_urls = []
        function_calls = []
        function_responses = []

        for part in parts:
            fc = getattr(part, "function_call", None)
            if fc is not None:
                function_calls.append(fc)
                continue
            fr = getattr(part, "function_response", None)
            if fr is not None:
                function_responses.append(fr)
                continue
            img = _part_image_data_url(part)
            if img is not None:
                image_urls.append(img)
                continue
            t = _part_text(part)
            if t:
                text_chunks.append(t)

        if function_responses:
            for fr in function_responses:
                # FIFO: the real code builds parts_to_send_back by
                # iterating function_calls in order (see
                # llm_completion.py's tool-calling loop), so responses
                # always arrive in the same order their calls were made -
                # dequeuing in that order pairs each response with its
                # actual call rather than assigning a fresh id.
                call_id = pending_call_ids.pop(0) if pending_call_ids else f"call_{call_counter[0]}"
                response_payload = getattr(fr, "response", {})
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(response_payload, default=str),
                })
            continue

        if function_calls:
            tool_calls = []
            for fc in function_calls:
                call_counter[0] += 1
                call_id = f"call_{call_counter[0]}"
                pending_call_ids.append(call_id)
                name = getattr(fc, "name", "unknown")
                args = dict(getattr(fc, "args", {}) or {})
                tool_calls.append({
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(args, default=str)},
                })
            msg = {"role": "assistant", "tool_calls": tool_calls}
            if text_chunks:
                msg["content"] = "\n".join(text_chunks)
            messages.append(msg)
            continue

        openai_role = "assistant" if role == "model" else "user"
        if image_urls:
            content = []
            if text_chunks:
                content.append({"type": "text", "text": "\n".join(text_chunks)})
            for url in image_urls:
                content.append({"type": "image_url", "image_url": {"url": url}})
            messages.append({"role": openai_role, "content": content})
        elif text_chunks:
            messages.append({"role": openai_role, "content": "\n".join(text_chunks)})

    return messages


class _FakeFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class _FakePart:
    def __init__(self, text=None, function_call=None):
        self.text = text
        self.function_call = function_call


class _FakeContent:
    def __init__(self, parts, role="model"):
        self.parts = parts
        # Must be set: _content_items() detects "is this a Content-like
        # object" via hasattr(c, "role"), and Chat.send_message stores
        # this object straight into its history and passes it back on
        # the NEXT call - found by dumping the actual history structure,
        # where this object showed up with no .role at all, got
        # misdetected as a flat/non-Content item, and silently produced
        # zero translated messages downstream.
        self.role = role


class _FakeCandidate:
    def __init__(self, content):
        self.content = content


class _FakeUsage:
    def __init__(self, prompt_tokens, completion_tokens, total_tokens):
        self.prompt_token_count = prompt_tokens
        self.candidates_token_count = completion_tokens
        self.total_token_count = total_tokens


class _FakeResponse:
    def __init__(self, text, parts, usage=None):
        self._text = text
        self.candidates = [_FakeCandidate(_FakeContent(parts))]
        self.usage_metadata = usage
        # Chat.send_message (google/genai/chats.py) reads this
        # unconditionally after every call, real Gemini responses only
        # populate it when the SDK's own automatic-function-calling loop
        # ran (disabled here, per llm_completion.py's
        # AutomaticFunctionCallingConfig(disable=True)) - None either way.
        self.automatic_function_calling_history = None

    @property
    def text(self):
        return self._text


def openrouter_generate_content(contents, config, api_key, _max_retries=3):
    for attempt in range(1, _max_retries + 1):
        try:
            response = _openrouter_generate_content_once(contents, config, api_key)
        except Exception as e:
            # 2026-09-13: discovered this retry loop only ever covered
            # "HTTP 200 but semantically empty" responses - a raw
            # requests exception (connection refused, timeout, DNS
            # hiccup - all observed under tyrone's known-flaky outbound
            # connectivity) or the RuntimeError below for a non-200
            # status propagated straight out of this function on the
            # FIRST attempt, never reaching the retry logic at all. That
            # bypassed this exact retry mechanism (built for "transient
            # provider hiccup", per the comment below) and was
            # reproducibly forcing a whole ProcessPoolExecutor batch to
            # fail (DEVIATIONS.md #44 follow-up) even though the OTHER
            # 7-8 workers in the batch would have succeeded fine.
            # Treat it exactly like an empty response - so it shares
            # the same retry budget and same eventual graceful give-up.
            sys.stderr.write(
                f"[_asp_openrouter_shim] request exception on attempt "
                f"{attempt}/{_max_retries}: {e!r} - signaling retry\n"
            )
            response = None
        if response is not None:
            return response
        if attempt < _max_retries:
            sys.stderr.write(
                f"[_asp_openrouter_shim] empty/error response, attempt "
                f"{attempt}/{_max_retries}, retrying...\n"
            )
    # All retries exhausted - return the last (empty) response rather than
    # raising, so llm_completion.py's own "no function_calls -> treat as
    # final text" branch handles it the same way an ordinary empty
    # completion would, instead of crashing the whole pipeline run on a
    # transient provider hiccup.
    sys.stderr.write(
        f"[_asp_openrouter_shim] all {_max_retries} attempts returned "
        f"empty/error responses - giving up, returning empty text.\n"
    )
    return _FakeResponse(text="", parts=[_FakePart(text="")])


def _openrouter_generate_content_once(contents, config, api_key):
    messages = _translate_to_openai_messages(contents)

    if not messages:
        sys.stderr.write("[_asp_openrouter_shim] DEBUG: empty messages, dumping contents:\n")
        items = contents if isinstance(contents, (list, tuple)) else [contents]
        for i, item in enumerate(items):
            sys.stderr.write(f"  item {i}: type={type(item).__name__} role={getattr(item, 'role', '<none>')} ")
            parts = getattr(item, "parts", None)
            if parts is None:
                sys.stderr.write(f"(no .parts attr; repr={repr(item)[:200]})\n")
            else:
                sys.stderr.write(f"parts={len(parts)}:\n")
                for j, p in enumerate(parts):
                    sys.stderr.write(
                        f"    part {j}: type={type(p).__name__} "
                        f"text={getattr(p, 'text', '<none>')!r} "
                        f"function_call={getattr(p, 'function_call', '<none>')!r} "
                        f"function_response={getattr(p, 'function_response', '<none>')!r} "
                        f"inline_data={getattr(p, 'inline_data', '<none>')!r}\n"
                    )

    payload = {"model": OPENROUTER_MODEL, "messages": messages}

    tools = getattr(config, "tools", None) if config is not None else None
    if tools:
        payload["tools"] = [
            _function_to_openai_tool(t) if callable(t) else t for t in tools
        ]
        payload["tool_choice"] = "auto"

    temperature = getattr(config, "temperature", None) if config is not None else None
    if temperature is not None:
        payload["temperature"] = temperature

    # 2026-09-13: DeepSeek v4.1-flash's default "high" reasoning effort
    # once burned the entire 8000-token completion budget on chain-of-
    # thought alone for this task (finish_reason "length", 0 chars of
    # actual output) - confirmed by inspecting the raw response at the
    # time. Lowered to "low" as the fix, with a larger max_tokens ceiling
    # as margin.
    #
    # 2026-09-14: re-tested "high" against the real payload shape (multi-
    # image + tool schema, ~9.6k prompt tokens) now that the provider-
    # routing/IPv4 fixes from deviation #40/#48 are in place - it no
    # longer reproduces the original failure in an isolated test. At the
    # SAME max_tokens ceiling (16000), "high" was faster than "low"
    # (27.6s vs 48.7s) and produced MORE tool calls and content (6
    # calls/2750 chars vs 4 calls/1959 chars), not less - the original
    # failure was very likely the provider-routing problem, not
    # something inherent to "high" itself. Raising max_tokens further to
    # 65000 tested no better (more budget just goes to reasoning) and
    # routed to a much slower provider (188s vs ~30-50s).
    #
    # However: under the REAL pipeline's sustained 8-worker concurrent
    # load (not the isolated test above), "high" effort's length-limit
    # failures (finish_reason="length", the exact original failure mode)
    # still occurred at ~10% of calls at max_tokens=16000, across
    # multiple providers (DeepInfra, then Alibaba) - not eliminated by
    # the provider-routing fix after all, just less frequent than before
    # under sustained real load. The per-member drop/give-up logic
    # (deviation #42) absorbed this without crashing any batch, but a
    # ~10% silent-waste rate on a "use max reasoning" run is worth
    # reducing rather than accepting. Raised max_tokens to 24000 (a
    # deliberate middle ground - the 65000 test showed diminishing/
    # negative returns from going further) as the new default. This is
    # an empirical, load-tested choice, not a guess - re-test if the
    # length-limit rate is still high at this ceiling.
    payload["reasoning"] = {"effort": os.environ.get("ASP_OPENROUTER_REASONING_EFFORT", "high")}
    payload["max_tokens"] = int(os.environ.get("ASP_OPENROUTER_MAX_TOKENS", "24000"))

    # Diagnosed 2026-09-13: real (multi-image + tool-schema) calls under
    # concurrent ProcessPoolExecutor load were failing 100% of the time
    # with finish_reason "error" after burning several hundred-2700
    # reasoning tokens. Isolated by reproducing the exact payload shape
    # directly against OpenRouter: every reproduction landed on the
    # "Together" backing provider and succeeded; the very first (plain
    # text, no image/tools) smoke test happened to land on "Morph" and
    # also succeeded, but Morph never reproduced with image+tools
    # present, so it was the suspect for the concurrent-load failures.
    # require_parameters pins routing to providers that actually support
    # every field in this payload (tools, in particular) instead of
    # silently routing to one that mishandles the combination - this
    # alone should avoid the original bug (an incapable provider), which
    # is what actually causes finish_reason "error" on this payload
    # shape, regardless of which capable provider serves it.
    #
    # Revised same day: hard-pinning to a single provider ("order":
    # ["Together"]) turned out to trade one failure mode for another -
    # under this pipeline's REAL sustained concurrent load (repeated
    # 8-9-worker batches over many minutes, not a one-off burst), a
    # single provider started showing its own elevated error rate
    # (confirmed NOT a general network problem: a direct
    # openrouter.ai/api/v1/models request from the same host returned
    # 200 OK in 0.14s while the pin was still up). Concentrating all
    # traffic on one provider is exactly what would produce that:
    # per-provider rate limits/capacity that a load-balanced multi-
    # provider pool wouldn't hit as hard. Dropped the hard order/
    # allow_fallbacks pin; require_parameters:true alone is kept as the
    # (sufficient, per OpenRouter's own docs) fix for the original bug,
    # and now OpenRouter's own routing spreads load across every
    # capable provider instead of concentrating it.
    provider_order = os.environ.get("ASP_OPENROUTER_PROVIDER_ORDER", "")
    provider_config = {"require_parameters": True}
    if provider_order.strip():
        provider_config["order"] = [p.strip() for p in provider_order.split(",") if p.strip()]
        provider_config["allow_fallbacks"] = True
    # 2026-09-16: `order` alone doesn't keep a fallback within the same
    # quantization - confirmed live, 5 test calls with
    # order=["deepinfra/fp8"] landed DeepInfra/DeepInfra/Relace/DeepInfra/
    # Morph, and Relace serves this model at fp4, not fp8. `quantizations`
    # restricts the whole candidate pool (first choice AND any fallback)
    # to the listed levels, so pairing it with `order` keeps the fallback-
    # under-load safety net from the "Together" hard-pin lesson above
    # while still guaranteeing every call - primary or fallback - uses the
    # requested quantization.
    provider_quantizations = os.environ.get("ASP_OPENROUTER_QUANTIZATIONS", "")
    if provider_quantizations.strip():
        provider_config["quantizations"] = [
            q.strip() for q in provider_quantizations.split(",") if q.strip()
        ]
    payload["provider"] = provider_config

    resp = requests.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter {resp.status_code}: {resp.text[:500]}")
    data = resp.json()

    choice = data["choices"][0]
    message = choice["message"]
    text = message.get("content") or ""
    parts = []

    if not text and not message.get("tool_calls"):
        sys.stderr.write(
            f"[_asp_openrouter_shim] empty response, finish_reason={choice.get('finish_reason')!r} "
            f"provider={data.get('provider')!r} - signaling retry\n"
        )
        sys.stderr.write(f"[_asp_openrouter_shim] usage={json.dumps(data.get('usage', {}), default=str)}\n")
        return None

    tool_calls = message.get("tool_calls") or []
    for tc in tool_calls:
        fn = tc.get("function", {})
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        parts.append(_FakePart(function_call=_FakeFunctionCall(fn.get("name", "unknown"), args)))

    if text:
        parts.append(_FakePart(text=text))
    if not parts:
        parts.append(_FakePart(text=""))

    usage = data.get("usage")
    fake_usage = None
    if usage:
        fake_usage = _FakeUsage(
            usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("total_tokens")
        )

    return _FakeResponse(text=text, parts=parts, usage=fake_usage)
