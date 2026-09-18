from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Protocol


class BudgetBroker(Protocol):
    def reserve(self, *, request_id: str) -> None: ...


@dataclass(frozen=True)
class UsageMetadata:
    prompt_tokens: int = 0
    candidates_tokens: int = 0
    thoughts_tokens: int = 0
    cached_content_tokens: int = 0
    model_version: str = ""
    response_id: str = ""


@dataclass(frozen=True)
class RestResponse:
    text: str = ""
    function_calls: tuple[Mapping[str, Any], ...] = ()
    thought_signatures: tuple[str, ...] = ()
    finish_reason: str = ""
    usage: UsageMetadata = field(default_factory=UsageMetadata)


class GeminiTransport:
    """Direct generateContent transport. No SDK, retries, query key, or raw logging."""

    def __init__(self, api_key: str, *, http: Optional[Callable[..., Any]] = None,
                 broker: Optional[BudgetBroker] = None, timeout_s: float = 120.0) -> None:
        if not api_key or any(c in api_key for c in "\r\n"):
            raise ValueError("an API key is required and must be a single line")
        self._api_key, self._http, self._broker, self._timeout = api_key, http, broker, timeout_s

    def generate(self, request: Mapping[str, Any], *, request_id: str) -> RestResponse:
        if self._broker is not None:
            self._broker.reserve(request_id=request_id)  # reservation precedes every physical attempt
        body = json.dumps(request, separators=(",", ":")).encode()
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
        if self._http is not None:
            raw = self._http(url, body=body, headers={"x-goog-api-key": self._api_key,
                                                       "content-type": "application/json"},
                             timeout=self._timeout)
            payload = raw if isinstance(raw, Mapping) else json.loads(raw)
        else:
            req = urllib.request.Request(url, data=body, method="POST",
                headers={"x-goog-api-key": self._api_key, "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=self._timeout) as response:  # no retry
                payload = json.load(response)
        return self._parse(payload)

    @staticmethod
    def _parse(payload: Mapping[str, Any]) -> RestResponse:
        model_version = str(payload.get("modelVersion", ""))
        if model_version and not model_version.startswith("gemini-3.8-flash"):
            raise ValueError("response model does not match gemini-3.8-flash")
        candidates = payload.get("candidates", [])
        if not isinstance(candidates, list) or len(candidates) != 1:
            raise ValueError("Gemini response must contain exactly one candidate")
        candidate = candidates[0]
        parts = ((candidate.get("content") or {}).get("parts") or [])
        text, calls, signatures = [], [], []
        for part in parts:
            if isinstance(part.get("text"), str): text.append(part["text"])
            if isinstance(part.get("functionCall"), Mapping): calls.append(part["functionCall"])
            if isinstance(part.get("thoughtSignature"), str): signatures.append(part["thoughtSignature"])
        usage = payload.get("usageMetadata") or {}
        return RestResponse("".join(text), tuple(calls), tuple(signatures),
            str(candidate.get("finishReason", "")), UsageMetadata(
                int(usage.get("promptTokenCount", 0)), int(usage.get("candidatesTokenCount", 0)),
                int(usage.get("thoughtsTokenCount", 0)), int(usage.get("cachedContentTokenCount", 0)),
                model_version, str(payload.get("responseId", ""))))
