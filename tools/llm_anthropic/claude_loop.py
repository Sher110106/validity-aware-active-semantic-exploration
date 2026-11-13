"""Native Claude port of the author's scene-graph completion tool loop (llm_completion.py).

One function, `run_member`, runs one ensemble member: it sends the author's prompt, the YAML scene graph
and the 6 slice images to a Claude model, answers `check_collision` calls with a callback, and returns the
final text with a full record (raw responses, usage, request ids, tool calls, status).

API facts (claude-api skill 2.1.322, checked 2026-11-13) that shape this file:
- Opus 5.5 and Haiku 5.5: `thinking` is `{"type": "adaptive"}` (a budget or "disabled" is a 400 on Opus 5.5);
  depth is `output_config.effort`; the default is "medium" on both, so it is always sent. No temperature, top_p,
  top_k or seed (400 or absent from the API).
- Forced `tool_choice` ("any" / "tool") is a 400 on Opus 5.5, so tool_choice is "auto" and the tool has
  `strict: true` (schema has additionalProperties false and every property required).
- Caching: one explicit `cache_control` on the last image (covers tools + the whole first message), and the
  top-level `cache_control` for the growing tail. Pre-warm: `max_tokens: 0`, no streaming, explicit marker only.
- Preserved thinking: thinking blocks are bound to the conversation. History is append-only. The block binding
  control (`thinking.block_binding.prefix_mismatch_behavior`, beta `thinking-binding-controls-2026-08-01`) is set
  explicitly; "error" by default, so any edit of history fails loudly on the first call.
- Refusals: HTTP 200 with `stop_reason: "refusal"` and `stop_details`. The skill says to opt into server-side
  `fallbacks` by default. We do NOT: the plan names the model, and a fallback would serve a different one.
  Haiku 5.5 has no fallback anyway.
- `eager_input_streaming` is left off: the skill's default turns it on for streamed client tools, but it also
  switches off the API's validation of tool input, which `strict: true` provides. Our arguments are seven small
  values, so nothing is gained.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import random
import threading
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import anthropic
import numpy as np

from llm_anthropic.author_tool import TOOL_DEF, TOOL_NAME
from llm_anthropic.meter import CapStop, Usage, call_cost

BETA_BLOCK_BINDING = "thinking-binding-controls-2026-08-01"
EFFORTS = ("low", "medium", "high", "xhigh", "max")

# A member whose record carries one of these is done; resume never pays for it again.
FINAL_STATUSES = frozenset({
    "ok", "truncated", "dropped_turn_limit", "dropped_refusal", "dropped_other_stop", "dropped_empty",
    "dropped_tool_error", "dropped_member_cap",
})
# Not final: a re-run starts the member from the beginning.
OPEN_STATUSES = frozenset({"error", "cap_stopped"})


@dataclass(frozen=True)
class LoopSettings:
    effort: str = "medium"
    max_tokens: int = 64000
    max_turns: int = 50  # the author's limit: 50 rounds of tool calls
    cache_ttl: str = "5m"  # "5m" or "1h"
    thinking_display: Optional[str] = None  # None -> API default ("omitted": empty thinking text)
    block_binding: Optional[str] = "error"  # "error", "drop_block", or None (do not send)
    timeout_s: float = 300.0
    max_retries: int = 3  # SDK-level retries (connection errors, 408, 409, 429, 5xx)
    turn_retries: int = 1  # one more try at the turn level if a stream breaks
    rate_limit_retries: int = 6  # extra tries after the SDK's own, on 429
    backoff_base_s: float = 2.0
    backoff_max_s: float = 120.0

    def __post_init__(self):
        if self.effort not in EFFORTS:
            raise ValueError(f"effort must be one of {EFFORTS}")
        if self.cache_ttl not in ("5m", "1h"):
            raise ValueError("cache_ttl must be '5m' or '1h'")
        if self.block_binding not in (None, "error", "drop_block"):
            raise ValueError("block_binding must be None, 'error' or 'drop_block'")
        if self.thinking_display not in (None, "summarized", "omitted", "updates"):
            raise ValueError("thinking_display must be None, 'summarized', 'omitted' or 'updates'")


def make_client(api_key: str, settings: Optional[LoopSettings] = None):
    """Real client. Reads nothing from disk; makes no call."""
    s = settings or LoopSettings()
    return anthropic.Anthropic(api_key=api_key, timeout=s.timeout_s, max_retries=s.max_retries)


# ---- rate gate ---------------------------------------------------------------------------------

class RateGate:
    """Shared pause. A 429 in one worker holds every worker that uses the same gate."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep):
        self._clock, self._sleep = clock, sleep
        self._lock = threading.Lock()
        self._until = 0.0
        self.trips = 0

    def trip(self, delay: float) -> None:
        with self._lock:
            self._until = max(self._until, self._clock() + delay)
            self.trips += 1

    def wait(self) -> None:
        while True:
            with self._lock:
                d = self._until - self._clock()
            if d <= 0:
                return
            self._sleep(d)


# ---- request building --------------------------------------------------------------------------

def _cache_control(settings: LoopSettings) -> dict:
    cc = {"type": "ephemeral"}
    if settings.cache_ttl == "1h":
        cc["ttl"] = "1h"
    return cc


def read_images(image_paths: Sequence) -> list[tuple[str, bytes]]:
    """(filename, bytes) in sorted filename order. JPEG only (the author sends image/jpeg)."""
    out = []
    for p in sorted((Path(x) for x in image_paths), key=lambda x: x.name):
        data = p.read_bytes()
        if data[:3] != b"\xff\xd8\xff":
            raise ValueError(f"{p} is not a JPEG")
        out.append((p.name, data))
    return out


def build_first_content(prompt_text: str, yaml_text: str, images: Sequence[tuple[str, bytes]],
                        settings: LoopSettings) -> list[dict]:
    """First user message: prompt text, YAML text, then the images. One cache marker on the last block."""
    content: list[dict] = [{"type": "text", "text": prompt_text}, {"type": "text", "text": yaml_text}]
    for _, data in images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg",
                       "data": base64.standard_b64encode(data).decode("ascii")},
        })
    content[-1]["cache_control"] = _cache_control(settings)
    return content


def build_request(model: str, messages: list, settings: LoopSettings, *, prewarm: bool = False) -> dict:
    thinking: dict[str, Any] = {"type": "adaptive"}
    if settings.thinking_display:
        thinking["display"] = settings.thinking_display
    if settings.block_binding:
        thinking["block_binding"] = {"prefix_mismatch_behavior": settings.block_binding}
    kw: dict[str, Any] = {
        "model": model,
        "max_tokens": 0 if prewarm else settings.max_tokens,
        "thinking": thinking,
        "output_config": {"effort": settings.effort},
        "tools": [copy.deepcopy(TOOL_DEF)],
        "tool_choice": {"type": "auto"},
        "messages": list(messages),
        "timeout": settings.timeout_s,
    }
    if not prewarm:
        kw["cache_control"] = _cache_control(settings)  # the tail; the pre-warm keeps only the explicit marker
    betas = []
    if settings.block_binding:
        betas.append(BETA_BLOCK_BINDING)
    if settings.thinking_display == "updates":
        betas.append("thinking-display-updates-2026-08-18")
    if betas:
        kw["betas"] = betas
    return kw


def _dump(obj) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


def _block_param(block) -> dict:
    """A reply block as a request block, once, at receipt. Never touched again."""
    return block.model_dump(mode="json", exclude_none=True) if hasattr(block, "model_dump") else dict(block)


def _json_default(o):
    if isinstance(o, np.generic):  # numpy scalars from the author's feasibility function
        return o.item()
    raise TypeError(f"not JSON serialisable: {type(o)}")


# ---- one model call, with retries, gate and meter ----------------------------------------------

class MemberAbort(Exception):
    def __init__(self, status: str, detail: dict):
        self.status, self.detail = status, detail
        super().__init__(f"{status}: {detail}")


def _retry_after(e: Exception) -> Optional[float]:
    try:
        v = e.response.headers.get("retry-after")
        return float(v) if v is not None else None
    except (AttributeError, ValueError, TypeError):
        return None


class _Caller:
    def __init__(self, client, model, settings, meter, member_key, gate, sleep, rng, flags, kind="call"):
        self.client, self.model, self.settings = client, model, settings
        self.meter, self.member_key = meter, member_key
        self.gate = gate or RateGate(sleep=sleep)
        self.rng, self.flags, self.kind = rng, flags, kind

    def _backoff(self, e, n) -> float:
        s = self.settings
        base = min(s.backoff_base_s * (2 ** n), s.backoff_max_s)
        ra = _retry_after(e)
        delay = max(ra, 0.0) if ra is not None else base
        return delay + 0.1 * delay * self.rng()

    def send(self, kwargs_fn: Callable[[], dict], *, stream: bool, turn: int):
        """Returns (reply, request_id, cost). Raises CapStop or MemberAbort."""
        s = self.settings
        turn_tries = 0
        rl_tries = 0
        while True:
            self.gate.wait()
            res = self.meter.reserve(self.model, self.member_key, kind=self.kind) if self.meter else None
            kwargs = kwargs_fn()
            extra = {"attempt_turn": turn}
            try:
                if stream:
                    with self.client.beta.messages.stream(**kwargs) as st:
                        reply = st.get_final_message()
                        request_id = getattr(st, "request_id", None)
                else:
                    reply = self.client.beta.messages.create(**kwargs)
                    request_id = getattr(reply, "_request_id", None)
            except anthropic.RateLimitError as e:
                if res:
                    self.meter.release(res, "http 429", turn=turn, extra=extra)
                if rl_tries >= s.rate_limit_retries:
                    raise MemberAbort("error", _err(e)) from e
                delay = self._backoff(e, rl_tries)
                rl_tries += 1
                self.flags.append(f"rate_limited_turn_{turn}")
                self.gate.trip(delay)
                continue
            except anthropic.APIStatusError as e:
                mid_stream = e.status_code == 200  # an SSE error event after the stream began
                if res:
                    if mid_stream:
                        self.meter.settle_failed(res, repr(e), turn=turn, extra=extra)
                    else:
                        self.meter.release(res, f"http {e.status_code}", turn=turn, extra=extra)
                if (mid_stream or e.status_code >= 500) and turn_tries < s.turn_retries:
                    turn_tries += 1
                    self.flags.append(f"turn_retry_{turn}")
                    continue
                raise MemberAbort("error", _err(e)) from e
            except anthropic.APIConnectionError as e:  # includes timeouts; may have been billed
                if res:
                    self.meter.settle_failed(res, repr(e), turn=turn, extra=extra)
                if turn_tries < s.turn_retries:
                    turn_tries += 1
                    self.flags.append(f"turn_retry_{turn}")
                    continue
                raise MemberAbort("error", _err(e)) from e
            except Exception as e:  # a bug or a bad response; do not retry
                if res:
                    self.meter.settle_failed(res, repr(e), turn=turn, extra=extra)
                raise MemberAbort("error", _err(e)) from e
            usage = Usage.from_api(reply.usage, default_ttl=s.cache_ttl)
            cost = None
            if res:
                cost = self.meter.settle(res, usage, request_id=request_id, served_model=getattr(reply, "model", None),
                                         stop_reason=getattr(reply, "stop_reason", None), turn=turn, extra=extra)
            else:
                try:
                    cost = call_cost(self.model, usage)[0]
                except KeyError:
                    cost = None
            return reply, request_id, cost, usage


def _err(e: Exception) -> dict:
    return {"type": type(e).__name__, "status_code": getattr(e, "status_code", None), "message": str(e)[:500]}


# ---- the member loop ---------------------------------------------------------------------------

def _first_message(prompt_text, yaml_text, image_paths, settings):
    images = read_images(image_paths)
    content = build_first_content(prompt_text, yaml_text, images, settings)
    meta = [{"name": n, "bytes": len(d), "sha256": hashlib.sha256(d).hexdigest()} for n, d in images]
    return {"role": "user", "content": content}, meta


def run_member(client, model: str, prompt_text: str, yaml_text: str, image_paths: Sequence,
               tool_callback: Callable[[str, dict], dict], settings: Optional[LoopSettings] = None, *,
               meter=None, member_key: Optional[str] = None, gate: Optional[RateGate] = None,
               sleep: Callable[[float], None] = time.sleep, rng: Callable[[], float] = random.random,
               meta: Optional[dict] = None) -> dict:
    """Run one member to its end. Returns the record (a plain dict, JSON-ready).

    status is one of FINAL_STATUSES or OPEN_STATUSES. `final_text` is None unless the member ended with text.
    """
    s = settings or LoopSettings()
    member_key = member_key or f"{model}|member"
    flags: list[str] = []
    t0 = time.monotonic()
    first, image_meta = _first_message(prompt_text, yaml_text, image_paths, s)
    messages: list[dict] = [first]
    caller = _Caller(client, model, s, meter, member_key, gate, sleep, rng, flags)

    rec: dict[str, Any] = {
        "schema": "claude_member_v1", "model": model, "status": None, "dropped": True, "final_text": None,
        "turns": 0, "tool_rounds": 0, "settings": asdict(s), "images": image_meta, "meta": meta or {},
        "request_ids": [], "served_models": [], "stop_reasons": [], "stop_details": None,
        "calls": [], "tool_calls": [], "responses": [], "flags": flags, "cost_usd": 0.0, "error": None,
    }
    text = None
    status = None
    try:
        while True:
            turn = rec["turns"]
            reply, request_id, cost, usage = caller.send(
                lambda: build_request(model, messages, s), stream=True, turn=turn)
            rec["turns"] += 1
            served = getattr(reply, "model", None)
            stop_reason = getattr(reply, "stop_reason", None)
            rec["request_ids"].append(request_id)
            rec["served_models"].append(served)
            rec["stop_reasons"].append(stop_reason)
            rec["responses"].append(_dump(reply))
            if cost is not None:
                rec["cost_usd"] += cost
            rec["calls"].append({
                "turn": turn, "request_id": request_id, "served_model": served, "stop_reason": stop_reason,
                "usage": usage.to_dict(), "cost_usd": cost, "messages_sent": len(messages),
            })
            if served != model:
                flag = f"served_model_mismatch:{served}"
                if flag not in flags:
                    flags.append(flag)
            if getattr(reply, "input_transformations", None):
                flags.append(f"input_transformations_turn_{turn}")

            if stop_reason == "refusal":
                sd = getattr(reply, "stop_details", None)
                rec["stop_details"] = _dump(sd)
                status = "dropped_refusal"
                break

            content = [_block_param(b) for b in reply.content]
            messages.append({"role": "assistant", "content": content})
            tool_uses = [b for b in content if b.get("type") == "tool_use"]

            if stop_reason == "max_tokens":
                text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
                status = "truncated"
                break
            if not tool_uses:
                if stop_reason in ("end_turn", "stop_sequence"):
                    text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
                    status = "ok" if text.strip() else "dropped_empty"
                else:
                    status = "dropped_other_stop"
                break

            results = []
            for tu in tool_uses:
                try:
                    result = tool_callback(tu["name"], tu["input"])
                except Exception as e:  # the author's pipeline loses the member here too
                    rec["error"] = {"where": "tool_callback", "type": type(e).__name__, "message": str(e)[:500],
                                    "trace": traceback.format_exc()[-1500:]}
                    status = "dropped_tool_error"
                    raise MemberAbort(status, rec["error"]) from e
                is_error = isinstance(result, dict) and set(result) == {"error"}
                block = {"type": "tool_result", "tool_use_id": tu["id"],
                         "content": json.dumps(result, default=_json_default)}
                if is_error:
                    block["is_error"] = True
                results.append(block)
                rec["tool_calls"].append({"turn": turn, "id": tu["id"], "name": tu["name"], "input": tu["input"],
                                          "result": result, "is_error": is_error})
            messages.append({"role": "user", "content": results})
            rec["tool_rounds"] += 1
            if rec["tool_rounds"] >= s.max_turns:
                # The author's loop would send round 50's answers and then drop the reply. That last call
                # can only be thrown away, so we do not make it. Same tool calls, same result (no text).
                status = "dropped_turn_limit"
                break
    except CapStop as e:
        status = "dropped_member_cap" if e.scope == "member" else "cap_stopped"
        rec["error"] = {"where": "meter", "scope": e.scope, "message": str(e)}
    except MemberAbort as e:
        status = e.status
        rec["error"] = rec["error"] or e.detail

    rec["status"] = status
    rec["final_text"] = text if status in ("ok", "truncated") else None
    rec["dropped"] = status not in ("ok", "truncated")
    rec["cost_usd"] = round(rec["cost_usd"], 9)
    rec["wall_s"] = round(time.monotonic() - t0, 3)
    return rec


def prewarm(client, model: str, prompt_text: str, yaml_text: str, image_paths: Sequence,
            settings: Optional[LoopSettings] = None, *, meter=None, member_key: Optional[str] = None,
            gate: Optional[RateGate] = None, sleep: Callable[[float], None] = time.sleep,
            rng: Callable[[], float] = random.random) -> dict:
    """Write the cache for one input: one non-streaming request, max_tokens 0, same tools, thinking and effort.

    Returns usage, request id and cost. Raises CapStop or MemberAbort.
    """
    s = settings or LoopSettings()
    first, image_meta = _first_message(prompt_text, yaml_text, image_paths, s)
    flags: list[str] = []
    caller = _Caller(client, model, s, meter, member_key or f"{model}|prewarm", gate, sleep, rng, flags, kind="prewarm")
    reply, request_id, cost, usage = caller.send(
        lambda: build_request(model, [first], s, prewarm=True), stream=False, turn=0)
    served = getattr(reply, "model", None)
    if served != model:
        flags.append(f"served_model_mismatch:{served}")
    return {"request_id": request_id, "served_model": served, "usage": usage.to_dict(), "cost_usd": cost,
            "stop_reason": getattr(reply, "stop_reason", None), "flags": flags,
            "cache_written": usage.cache_write > 0, "cache_read": usage.cache_read}
