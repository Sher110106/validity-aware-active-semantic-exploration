from __future__ import annotations

import hashlib
from typing import Any, Callable, Mapping, Optional, Sequence

from .transport import GeminiTransport, RestResponse


def deterministic_seed(campaign: str, run: str, stage: str, member: str, turn: int) -> int:
    """Stable 32-bit request seed; the caller should also record the components."""
    value = "\x1f".join((campaign, run, stage, member, str(turn))).encode("utf-8")
    return int.from_bytes(hashlib.sha256(value).digest()[:4], "big")


def request_for_turn(contents: Sequence[Mapping[str, Any]], *, seed: int, max_output_tokens: int,
                    temperature: float, tools: Optional[Sequence[Mapping[str, Any]]] = None) -> dict[str, Any]:
    if not 1 <= max_output_tokens <= 65536:
        raise ValueError("max_output_tokens must be bounded to [1, 65536]")
    if not 0 <= temperature <= 2:
        raise ValueError("temperature must be in [0, 2]")
    request: dict[str, Any] = {
        "contents": list(contents),
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_output_tokens,
                              "seed": int(seed), "thinkingConfig": {"thinkingLevel": "MEDIUM"}},
    }
    if tools is not None:
        request["tools"] = list(tools)
    return request


def run_author_turns(transport: GeminiTransport, initial_contents: Sequence[Mapping[str, Any]], *,
                     seed: int, request_id: str, max_output_tokens: int, temperature: float,
                     tools: Optional[Sequence[Mapping[str, Any]]] = None,
                     execute_tool: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None,
                     max_turns: int = 8) -> RestResponse:
    """Small transport seam: preserves opaque thought signatures in the same turn only."""
    contents = list(initial_contents)
    for turn in range(max_turns):
        response = transport.generate(request_for_turn(contents, seed=seed,
            max_output_tokens=max_output_tokens, temperature=temperature, tools=tools),
            request_id=f"{request_id}:turn:{turn}")
        if not response.function_calls:
            return response
        if execute_tool is None:
            raise RuntimeError("function call returned without an injected tool executor")
        parts: list[dict[str, Any]] = []
        for index, call in enumerate(response.function_calls):
            part: dict[str, Any] = {"functionCall": dict(call)}
            if index < len(response.thought_signatures):
                part["thoughtSignature"] = response.thought_signatures[index]
            parts.append(part)
        contents.append({"role": "model", "parts": parts})
        for call in response.function_calls:
            contents.append({"role": "user", "parts": [{"functionResponse": dict(execute_tool(call))}]})
    raise TimeoutError("author tool loop exceeded max_turns")
