from __future__ import annotations

import hashlib
from typing import Any, Callable, Mapping, Optional, Sequence

from .transport import GeminiTransport, RequestContext, RestResponse, conservative_input_bound


def deterministic_seed(campaign: str, run: str, stage: str, member: str, turn: int) -> int:
    return int.from_bytes(hashlib.sha256("\x1f".join((campaign, run, stage, member, str(turn))).encode()).digest()[:4], "big")


def request_for_turn(contents: Sequence[Mapping[str, Any]], *, seed: int,
                    max_output_tokens: int, tools: Optional[Sequence[Mapping[str, Any]]] = None) -> dict[str, Any]:
    request: dict[str, Any] = {"contents": list(contents), "store": False,
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_output_tokens,
            "candidateCount": 1, "seed": seed,
            "thinkingConfig": {"thinkingLevel": "MEDIUM", "includeThoughts": False}}}
    if tools is not None:
        request["tools"] = list(tools)
    return request


def _function_response(call: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    name = call.get("name")
    if not isinstance(name, str) or not name or not isinstance(result, Mapping):
        raise ValueError("tool result must have an exact function name and structured response")
    response: dict[str, Any] = {"name": name, "response": dict(result)}
    call_id = call.get("id")
    if call_id is not None:
        # Required to correlate a FunctionResponse with its FunctionCall when
        # a turn contains more than one parallel call (google.genai.types
        # FunctionCall/FunctionResponse both carry `id`, serialized as-is).
        if not isinstance(call_id, str) or not call_id:
            raise ValueError("function call id must be a non-empty string when present")
        response["id"] = call_id
    return response


def run_author_turns(transport: GeminiTransport, initial_contents: Sequence[Mapping[str, Any]], *,
                     context: RequestContext, seed_for_turn: Callable[[int], int],
                     max_output_tokens: int, tools: Optional[Sequence[Mapping[str, Any]]] = None,
                     execute_tool: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None,
                     max_turns: int = 8,
                     input_bound_fn: Callable[[Mapping[str, Any]], int] = conservative_input_bound) -> RestResponse:
    contents = list(initial_contents)
    resolve_attempt_id = getattr(transport.broker, "resolve_attempt_id", None)
    for turn in range(max_turns):
        request = request_for_turn(contents, seed=seed_for_turn(turn), max_output_tokens=max_output_tokens, tools=tools)
        # A fixed bound from the caller would under-reserve later turns: the
        # conversation strictly grows each round trip (accumulated function
        # call/response history), so each turn needs its own bound computed
        # from what it's actually about to send, not the first turn's size.
        # input_bound_fn defaults to the byte-conservative bound (unchanged
        # behavior for any caller that doesn't pass one); a caller with a
        # trusted native counter should pass one instead -- see
        # transport.native_input_bound().
        base_attempt_id = f"{context.attempt_id}:{turn}"
        # If the broker supports it (LedgerBudgetBroker does), resolve a
        # collision-free attempt_id before reserving. Confirmed live
        # (2026-09-22): a pipeline that reruns this whole member from turn
        # 0 after any unresolved call reconstructs this exact deterministic
        # base_attempt_id again, which reserve()'s own
        # UNIQUE(campaign_id, attempt_id) constraint then rejects forever --
        # an infinite, cost-neutral (the constraint fires before any HTTP
        # call) but non-productive loop. A broker that omits this method
        # keeps today's exact behavior: the base attempt_id used verbatim,
        # retry_of always None.
        if resolve_attempt_id is not None:
            attempt_id, retry_of = resolve_attempt_id(
                campaign_id=context.campaign_id, base_attempt_id=base_attempt_id)
        else:
            attempt_id, retry_of = base_attempt_id, None
        turn_context = RequestContext(
            allocation_id=context.allocation_id, campaign_id=context.campaign_id,
            phase_id=context.phase_id, run_id=context.run_id, stage_id=context.stage_id,
            member_id=context.member_id, turn_id=f"{context.turn_id}:{turn}",
            attempt_id=attempt_id, retry_of=retry_of,
            trusted_input_token_bound=input_bound_fn(request),
        )
        response = transport.generate(request, context=turn_context)
        if not response.function_calls:
            return response
        if execute_tool is None:
            raise RuntimeError("function calls require an injected executor")
        # The complete model parts sequence is copied, never reconstructed from parallel tuples.
        contents.append({"role": "model", "parts": [dict(part) for part in response.parts]})
        for call in response.function_calls:
            result = execute_tool(call)
            contents.append({"role": "user", "parts": [{"functionResponse": _function_response(call, result)}]})
    raise TimeoutError("author tool loop exceeded max_turns")
