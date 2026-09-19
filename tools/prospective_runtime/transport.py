from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence, Tuple

MODEL = "gemini-3.8-flash"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
MAX_OUTPUT_TOKENS = 65536
ALLOWED_FINISH_REASONS = frozenset(("STOP", "MAX_TOKENS", "SAFETY", "RECITATION", "OTHER"))


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def request_hash(request: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(request)).hexdigest()


def conservative_input_bound(request: Mapping[str, Any]) -> int:
    """One token per serialized byte -- intentionally over-conservative,
    covering Unicode, tool schemas, and inline image data. A caller with a
    trusted native token count should use that instead; this is the
    fail-closed fallback when none is available."""
    return len(canonical_json(request))


@dataclass(frozen=True)
class RequestContext:
    allocation_id: str
    campaign_id: str
    phase_id: str
    run_id: str
    stage_id: str
    member_id: str
    turn_id: str
    attempt_id: str
    trusted_input_token_bound: int
    retry_of: Optional[str] = None

    def validate(self) -> None:
        values = (self.allocation_id, self.campaign_id, self.phase_id, self.run_id,
                  self.stage_id, self.member_id, self.turn_id, self.attempt_id)
        if any(not isinstance(value, str) or not value or len(value) > 200 for value in values):
            raise ValueError("broker context IDs must be non-empty bounded strings")
        if self.retry_of is not None and (not isinstance(self.retry_of, str) or not self.retry_of or len(self.retry_of) > 200):
            raise ValueError("retry_of must be a non-empty bounded string when given")
        if not isinstance(self.trusted_input_token_bound, int) or self.trusted_input_token_bound < 0:
            raise ValueError("trusted_input_token_bound must be a non-negative integer")


@dataclass(frozen=True)
class Reservation:
    reservation_id: str
    request_hash: str


@dataclass(frozen=True)
class DispatchReceipt:
    reservation_id: str
    request_hash: str
    dispatched: bool = True


@dataclass(frozen=True)
class UsageMetadata:
    prompt_tokens: int
    candidates_tokens: int
    thoughts_tokens: int
    cached_content_tokens: int
    total_tokens: int
    model_version: str
    response_id: str
    service_tier: str


@dataclass(frozen=True)
class RestResponse:
    text: str
    parts: Tuple[Mapping[str, Any], ...]
    function_calls: Tuple[Mapping[str, Any], ...]
    finish_reason: str
    usage: UsageMetadata
    max_output_tokens: int


class BudgetBroker(Protocol):
    def reserve(self, *, context: RequestContext, request_hash: str,
               max_output_tokens: int) -> Reservation: ...
    def dispatch(self, *, reservation: Reservation, receipt: DispatchReceipt) -> None: ...
    def settle(self, *, reservation: Reservation, usage: UsageMetadata,
               finish_reason: str) -> None: ...
    def unresolved(self, *, reservation: Reservation, reason: str) -> None: ...


class GeminiTransport:
    """Strict, single-attempt REST transport. A broker is mandatory."""

    def __init__(self, credential_loader: Callable[[], str], *, broker: BudgetBroker,
                 http: Optional[Callable[..., Any]] = None, timeout_s: float = 120.0) -> None:
        if broker is None:
            raise ValueError("a hardened budget broker is required")
        if timeout_s <= 0:
            raise ValueError("timeout must be positive")
        self._load_key, self._http, self._broker, self._timeout = credential_loader, http, broker, timeout_s

    def generate(self, request: Mapping[str, Any], *, context: RequestContext) -> RestResponse:
        context.validate()
        _validate_request(request)
        digest = request_hash(request)
        max_output_tokens = request["generationConfig"]["maxOutputTokens"]
        reservation = self._broker.reserve(context=context, request_hash=digest,
                                           max_output_tokens=max_output_tokens)
        if reservation.request_hash != digest:
            raise RuntimeError("broker returned a mismatched request hash")
        receipt = DispatchReceipt(reservation.reservation_id, digest)
        try:
            self._broker.dispatch(reservation=reservation, receipt=receipt)
            key = self._load_key()
            if not isinstance(key, str) or not key or any(char in key for char in "\r\n"):
                raise RuntimeError("credential loader did not return a valid key")
            headers = {"x-goog-api-key": key, "content-type": "application/json"}
            body = canonical_json(request)
            if self._http is not None:
                raw = self._http(ENDPOINT, body=body, headers=headers, timeout=self._timeout,
                                 allow_redirects=False)
                payload = raw if isinstance(raw, Mapping) else json.loads(raw)
            else:
                req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers=headers)
                with urllib.request.urlopen(req, timeout=self._timeout) as response:
                    if response.geturl() != ENDPOINT:
                        raise RuntimeError("unexpected redirect")
                    payload = json.load(response)
            result = self._parse(payload, request)
            self._broker.settle(reservation=reservation, usage=result.usage,
                                finish_reason=result.finish_reason)
            return result
        except Exception as exc:
            try:
                self._broker.unresolved(reservation=reservation, reason=type(exc).__name__)
            except Exception:
                pass
            raise RuntimeError("Gemini attempt unresolved") from None

    @staticmethod
    def _parse(payload: Mapping[str, Any], request: Mapping[str, Any]) -> RestResponse:
        try:
            model_version = payload["modelVersion"]
            response_id = payload["responseId"]
            usage = payload["usageMetadata"]
            candidates = payload["candidates"]
            if not isinstance(usage, Mapping):
                raise ValueError("missing usage metadata")
            # The real API returns the bare model name with no version
            # suffix at all (confirmed live, capability probe 2026-09-19),
            # not always a "-NNN"-suffixed version as first assumed.
            if not isinstance(model_version, str) or not (
                model_version == MODEL or model_version.startswith(MODEL + "-")
            ):
                raise ValueError("model mismatch")
            if not isinstance(response_id, str) or not response_id:
                raise ValueError("responseId missing")
            # serviceTier lives inside usageMetadata, lowercase ("standard"),
            # not at the payload top level as "STANDARD" -- also confirmed
            # live; the earlier assumption came from generic REST examples,
            # never checked against this model's actual response.
            service_tier = usage.get("serviceTier")
            if service_tier != "standard":
                raise ValueError("non-standard or missing service metadata")
            counts = [_nonnegative_int(usage[name]) for name in
                      ("promptTokenCount", "candidatesTokenCount", "thoughtsTokenCount")]
            # cachedContentTokenCount is omitted entirely (not sent as 0)
            # when there is no cached content -- also confirmed live.
            counts.append(_nonnegative_int(usage.get("cachedContentTokenCount", 0)))
            counts.append(_nonnegative_int(usage["totalTokenCount"]))
            prompt, candidate_tokens, thoughts, cached, total = counts
            if total != prompt + candidate_tokens + thoughts:
                raise ValueError("inconsistent token totals")
            if len(candidates) != 1 or not isinstance(candidates[0], Mapping):
                raise ValueError("exactly one candidate is required")
            candidate = candidates[0]
            finish = candidate["finishReason"]
            if finish not in ALLOWED_FINISH_REASONS:
                raise ValueError("unsupported finish reason")
            parts = candidate["content"]["parts"]
            if not isinstance(parts, list):
                raise ValueError("candidate parts are missing")
            max_output = request["generationConfig"]["maxOutputTokens"]
            if candidate_tokens + thoughts > max_output:
                raise ValueError("candidate and thought tokens exceed maxOutputTokens")
            calls = tuple(dict(part["functionCall"]) for part in parts
                          if isinstance(part, Mapping) and isinstance(part.get("functionCall"), Mapping))
            text = "".join(part["text"] for part in parts if isinstance(part, Mapping)
                           and isinstance(part.get("text"), str) and not part.get("thought", False))
            copied_parts = tuple(json.loads(json.dumps(part, sort_keys=True)) for part in parts)
            metadata = UsageMetadata(prompt, candidate_tokens, thoughts, cached, total,
                                     model_version, response_id, service_tier)
            return RestResponse(text, copied_parts, calls, finish, metadata, max_output)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("invalid Gemini response metadata") from None


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("token counts must be non-negative integers")
    return value


def _validate_request(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping) or set(request) - {"contents", "generationConfig", "tools", "store"}:
        raise ValueError("request contains unsupported fields")
    if request.get("store") is not False or not isinstance(request.get("contents"), list):
        raise ValueError("contents and store=false are required")
    config = request.get("generationConfig")
    required = {"temperature", "maxOutputTokens", "candidateCount", "seed", "thinkingConfig"}
    if not isinstance(config, Mapping) or set(config) != required:
        raise ValueError("generationConfig is not the approved exact shape")
    if config["temperature"] != 0.2 or config["candidateCount"] != 1:
        raise ValueError("temperature and candidate count are not author-faithful")
    if isinstance(config["maxOutputTokens"], bool) or not isinstance(config["maxOutputTokens"], int) or not 1 <= config["maxOutputTokens"] <= MAX_OUTPUT_TOKENS:
        raise ValueError("maxOutputTokens is out of bounds")
    if isinstance(config["seed"], bool) or not isinstance(config["seed"], int) or not 0 <= config["seed"] <= 2147483647:
        raise ValueError("seed must be an explicit deterministic integer")
    thinking = config["thinkingConfig"]
    if thinking != {"thinkingLevel": "MEDIUM", "includeThoughts": False}:
        raise ValueError("thinkingConfig must explicitly request medium without thought summaries")
    if "tools" in request and not isinstance(request["tools"], list):
        raise ValueError("tools must be a list")
