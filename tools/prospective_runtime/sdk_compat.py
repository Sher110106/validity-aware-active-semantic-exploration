"""Python 3.9 duck-typed bridge for google-genai 1.47-shaped objects.

The bridge deliberately does not import google-genai: the offline Mac tests use
fixtures and the pinned container supplies the real classes at deployment time.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def content_to_rest(content: Any) -> dict[str, Any]:
    role = _get(content, "role", "user")
    parts = []
    for part in (_get(content, "parts", None) or []):
        item: dict[str, Any] = {}
        text = _get(part, "text", None)
        if text is not None: item["text"] = text
        inline = _get(part, "inline_data", _get(part, "inlineData", None))
        if inline is not None:
            item["inlineData"] = {"mimeType": _get(inline, "mime_type", _get(inline, "mimeType", "")),
                                   "data": _get(inline, "data", b"")}
        call = _get(part, "function_call", _get(part, "functionCall", None))
        if call is not None:
            item["functionCall"] = {"name": _get(call, "name", ""), "args": dict(_get(call, "args", {}) or {})}
        response = _get(part, "function_response", _get(part, "functionResponse", None))
        if response is not None:
            item["functionResponse"] = {"name": _get(response, "name", ""), "response": dict(_get(response, "response", {}) or {})}
        signature = _get(part, "thought_signature", _get(part, "thoughtSignature", None))
        if signature is not None: item["thoughtSignature"] = signature
        if _get(part, "thought", False): item["thought"] = True
        parts.append(item)
    return {"role": role, "parts": parts}


def response_to_sdk_shape(response: Mapping[str, Any]) -> dict[str, Any]:
    """Return the attribute names consumed by existing Chat/LLM code."""
    candidate = response["candidates"][0]
    content = candidate["content"]
    parts = []
    for raw in content["parts"]:
        part = dict(raw)
        if "functionCall" in part:
            part["function_call"] = part.pop("functionCall")
        if "thoughtSignature" in part:
            part["thought_signature"] = part.pop("thoughtSignature")
        parts.append(part)
    usage = response["usageMetadata"]
    return {"candidates": [{"content": {"role": content.get("role", "model"), "parts": parts},
                             "finish_reason": candidate["finishReason"]}],
            "usage_metadata": {"prompt_token_count": usage["promptTokenCount"],
                                "candidates_token_count": usage["candidatesTokenCount"],
                                "thoughts_token_count": usage["thoughtsTokenCount"],
                                "cached_content_token_count": usage["cachedContentTokenCount"],
                                "total_token_count": usage["totalTokenCount"]},
            "model_version": response["modelVersion"], "response_id": response["responseId"]}
