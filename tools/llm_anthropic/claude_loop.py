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
import httpx2
import numpy as np

from llm_anthropic.author_tool import TOOL_DEF, TOOL_NAME
from llm_anthropic.meter import CapStop, Usage, call_cost

BETA_BLOCK_BINDING = "thinking-binding-controls-2026-08-01"
EFFORTS = ("low", "medium", "high", "xhigh", "max")

# Registered rules (PREREGISTRATION_SEMANTIC §12). A member is DROPPED, and counted, only if it is refused,
# reaches 50 turns, or still fails after the retries. Whether its final text parses is decided later, by the
# author's parser, not here. A dropped member is final: resume never pays for it again.
FINAL_STATUSES = frozenset({"ok", "dropped_refusal", "dropped_turn_limit", "dropped_error"})
# Unfinished, not dropped: a cap stop, or a fault of ours (a bad request: 400, 401, 403, 404, 413, 422, or an
# unexpected exception). A resume runs the member again from the start. A killed process leaves no record.
OPEN_STATUSES = frozenset({"error", "cap_stopped"})

DIRECT_BASE_URL = "https://api.anthropic.com"


@dataclass(frozen=True)
class LoopSettings:
    effort: str = "medium"
    max_tokens: int = 64000
    max_turns: int = 50  # the author's limit: 50 rounds of tool calls
    cache_ttl: str = "5m"  # "5m" or "1h"
    thinking_display: Optional[str] = None  # None -> API default ("omitted": empty thinking text)
    block_binding: Optional[str] = "error"  # "error", "drop_block", or None (do not send)
    timeout_s: float = 300.0
    retries: int = 3  # per call, for any transient error (429, 408/409, 5xx, timeout, broken stream). §12.
    backoff_base_s: float = 2.0
    backoff_max_s: float = 120.0

    def __post_init__(self):
        if self.retries < 0:
            raise ValueError("retries must be >= 0")
        if self.effort not in EFFORTS:
            raise ValueError(f"effort must be one of {EFFORTS}")
        if self.cache_ttl not in ("5m", "1h"):
            raise ValueError("cache_ttl must be '5m' or '1h'")
        if self.block_binding not in (None, "error", "drop_block"):
            raise ValueError("block_binding must be None, 'error' or 'drop_block'")
        if self.thinking_display not in (None, "summarized", "omitted", "updates"):
            raise ValueError("thinking_display must be None, 'summarized', 'omitted' or 'updates'")


def make_client(api_key: str, settings: Optional[LoopSettings] = None, *, http_client=None, ipv4: bool = False):
    """Real client. Reads nothing from disk; makes no call.

    - base_url is pinned to the Anthropic API. The SDK would otherwise take ANTHROPIC_BASE_URL from the
      environment (this machine sets it to a local gateway).
    - the key is passed explicitly, so the SDK does not read ANTHROPIC_AUTH_TOKEN or a profile.
      (ANTHROPIC_CUSTOM_HEADERS it still reads; `claude_static.check_direct` refuses to run if that is set.)
    - max_retries is 0: every retry is ours, so the meter sees it and there are never more than `retries`.
    - ipv4=True sends from 0.0.0.0, which makes the connection use IPv4. Off by default. A custom transport
      makes httpx ignore the proxy environment variables.
    """
    s = settings or LoopSettings()
    if http_client is None and ipv4:
        http_client = anthropic.DefaultHttpxClient(transport=httpx2.HTTPTransport(local_address="0.0.0.0"))
    return anthropic.Anthropic(api_key=api_key, base_url=DIRECT_BASE_URL, timeout=s.timeout_s, max_retries=0,
                               http_client=http_client)


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
        """One model call with the §12 retry rule. Returns (reply, request_id, cost, usage).

        Transient errors (429, 408, 409, 5xx, timeout, broken stream) are retried up to `settings.retries`
        times with backoff; a worker that gets a 429 holds every worker on the same gate. A call that still
        fails raises MemberAbort("dropped_error"). A request the API rejects (400, 401, 403, 404, 413, 422)
        is not retried and raises MemberAbort("error"): that is a fault of ours, and the member stays open.
        Raises CapStop when a cap refuses the reserve.
        """
        s = self.settings
        tries = 0
        while True:
            self.gate.wait()
            res = self.meter.reserve(self.model, self.member_key, kind=self.kind) if self.meter else None
            kwargs = kwargs_fn()
            extra = {"attempt_turn": turn}
            st = None
            try:
                if stream:
                    with self.client.beta.messages.stream(**kwargs) as st_:
                        st = st_
                        reply = st.get_final_message()
                        request_id = getattr(st, "request_id", None)
                else:
                    reply = self.client.beta.messages.create(**kwargs)
                    request_id = getattr(reply, "_request_id", None)
            except anthropic.APIStatusError as e:  # includes RateLimitError and InternalServerError
                mid_stream = e.status_code == 200  # an SSE error event after the stream began: may be billed
                transient = mid_stream or e.status_code in (408, 409, 429) or e.status_code >= 500
                if res:
                    if mid_stream:
                        self.meter.settle_failed(res, repr(e), usage=self._partial_usage(st), turn=turn, extra=extra)
                    else:
                        self.meter.release(res, f"http {e.status_code}", turn=turn, extra=extra)
                if not transient:
                    raise MemberAbort("error", _err(e)) from e
                err = e
            except anthropic.APIConnectionError as e:  # includes timeouts; may have been billed
                if res:
                    self.meter.settle_failed(res, repr(e), usage=self._partial_usage(st), turn=turn, extra=extra)
                err = e
            except Exception as e:  # a bug in our code or a response we cannot read: do not retry
                if res:
                    self.meter.settle_failed(res, repr(e), usage=self._partial_usage(st), turn=turn, extra=extra)
                raise MemberAbort("error", _err(e)) from e
            else:
                usage = Usage.from_api(reply.usage, default_ttl=s.cache_ttl)
                cost = None
                if res:
                    cost = self.meter.settle(res, usage, request_id=request_id,
                                             served_model=getattr(reply, "model", None),
                                             stop_reason=getattr(reply, "stop_reason", None), turn=turn, extra=extra)
                else:
                    try:
                        cost = call_cost(self.model, usage)[0]
                    except KeyError:
                        cost = None
                return reply, request_id, cost, usage
            # a transient error: back off and go again, or give up
            if tries >= s.retries:
                raise MemberAbort("dropped_error", _err(err)) from err
            self.gate.trip(self._backoff(err, tries))
            tries += 1
            self.flags.append(f"retry_turn_{turn}")

    def _partial_usage(self, st) -> Optional[Usage]:
        """Usage the stream had accumulated when it broke, if the SDK has any."""
        if st is None:
            return None
        try:
            u = st.current_message_snapshot.usage
        except Exception:
            return None
        return Usage.from_api(u, default_ttl=self.settings.cache_ttl) if u is not None else None


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

            if stop_reason == "max_tokens" or not tool_uses:
                # A final text. We do not judge it: a cut-off or empty text is passed on with a flag, and the
                # author's parser drops what does not parse (§12).
                text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
                if stop_reason == "max_tokens":
                    flags.append("stop_max_tokens")
                elif stop_reason not in ("end_turn", "stop_sequence"):
                    rec["error"] = {"where": "stop_reason", "message": f"unexpected stop_reason {stop_reason!r}"}
                    text = None
                    raise MemberAbort("dropped_error", rec["error"])
                if not text.strip():
                    flags.append("empty_text")
                status = "ok"
                break

            results = []
            for tu in tool_uses:
                try:
                    result = tool_callback(tu["name"], tu["input"])
                except Exception as e:  # the author's pipeline loses the member here too
                    rec["error"] = {"where": "tool_callback", "type": type(e).__name__, "message": str(e)[:500],
                                    "trace": traceback.format_exc()[-1500:]}
                    raise MemberAbort("dropped_error", rec["error"]) from e
                # The author's loop sends his result dict and nothing else: no error flag.
                results.append({"type": "tool_result", "tool_use_id": tu["id"],
                                "content": json.dumps(result, default=_json_default)})
                rec["tool_calls"].append({"turn": turn, "id": tu["id"], "name": tu["name"], "input": tu["input"],
                                          "result": result})
            messages.append({"role": "user", "content": results})
            rec["tool_rounds"] += 1
            if rec["tool_rounds"] >= s.max_turns:
                # The author's loop would send round 50's answers and then drop the reply. That last call
                # can only be thrown away, so we do not make it. Same tool calls, same result (no text).
                status = "dropped_turn_limit"
                break
    except CapStop as e:  # cut short by a cap: unfinished, not dropped (a resume runs it again)
        status = "cap_stopped"
        rec["error"] = {"where": "meter", "scope": e.scope, "message": str(e)}
    except MemberAbort as e:
        status = e.status
        rec["error"] = rec["error"] or e.detail

    rec["status"] = status
    rec["final_text"] = text if status == "ok" else None
    rec["dropped"] = status.startswith("dropped")
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
