from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence, Tuple

MODEL = "gemini-3.8-flash"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
COUNT_TOKENS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:countTokens"
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


# Confirmed live (2026-09-21) that generationConfig's five approved fields
# never affect tokenization (temperature/candidateCount/seed are sampling
# params, maxOutputTokens/thinkingConfig bound generation, not input) --
# _validate_request() below pins the request to exactly this set. countTokens
# omits generationConfig entirely (it rejects an unwrapped "tools" field, and
# generationConfig is not part of its documented shape); if a future field is
# ever added to that approved set, it must be re-checked against this
# assumption before being silently excluded here.
_TOKEN_IRRELEVANT_CONFIG_KEYS = frozenset(
    {"temperature", "maxOutputTokens", "candidateCount", "seed", "thinkingConfig"})


def count_tokens(request: Mapping[str, Any], *, credential_loader: Callable[[], str],
                 http: Optional[Callable[..., Any]] = None, timeout_s: float = 30.0) -> int:
    """Real per-request input token count via the free, read-only
    countTokens endpoint. Never touches a ledger or broker and never
    settles anything -- callers must decide what to do with the result.
    Raises on ANY failure (bad credential, network error, malformed
    response, or an unrecognized generationConfig field); the caller's
    fallback direction matters: falling back to conservative_input_bound()
    only ever over-reserves, so that is the correct fail-closed behavior,
    never a silent under-reservation.

    Confirmed live (2026-09-21) that countTokens rejects a bare
    {"contents": ..., "tools": ...} body ("Unknown name \"tools\"") but
    accepts the same fields wrapped in {"generateContentRequest": {...}}."""
    config_keys = set(request.get("generationConfig") or {})
    if config_keys - _TOKEN_IRRELEVANT_CONFIG_KEYS:
        raise ValueError("generationConfig has fields not known to be token-irrelevant; "
                         "refusing to silently omit it from countTokens")
    body: dict[str, Any] = {"generateContentRequest": {
        "model": "models/" + MODEL, "contents": request["contents"],
    }}
    if "tools" in request:
        body["generateContentRequest"]["tools"] = request["tools"]
    key = credential_loader()
    if not isinstance(key, str) or not key or any(char in key for char in "\r\n"):
        raise RuntimeError("credential loader did not return a valid key")
    headers = {"x-goog-api-key": key, "content-type": "application/json"}
    data = canonical_json(body)
    if http is not None:
        raw = http(COUNT_TOKENS_ENDPOINT, body=data, headers=headers, timeout=timeout_s,
                   allow_redirects=False)
        payload = raw if isinstance(raw, Mapping) else json.loads(raw)
    else:
        req = urllib.request.Request(COUNT_TOKENS_ENDPOINT, data=data, method="POST", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_s) as response:
            if response.geturl() != COUNT_TOKENS_ENDPOINT:
                raise RuntimeError("unexpected redirect")
            payload = json.load(response)
    total = payload["totalTokens"]
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ValueError("invalid countTokens response")
    return total


def native_input_bound(request: Mapping[str, Any], *, credential_loader: Callable[[], str],
                       http: Optional[Callable[..., Any]] = None, timeout_s: float = 30.0,
                       on_count: Optional[Callable[..., None]] = None) -> int:
    """The real token count, with a safety margin, when the free countTokens
    call succeeds; the conservative byte bound on ANY failure.

    Advisor review (2026-09-21/22): countTokens is a provider estimate, not
    a guarantee of matching the real generateContent promptTokenCount --
    unlike the byte bound, an under-count here is NOT proven safe.
    Ledger.settle() (gemini_campaign/ledger.py) refuses to settle when the
    real cost exceeds the reservation, which would leave real spend
    DISPATCHED and never priced -- the exact failure this whole campaign
    exists to prevent. A truncated response (finishReason=MAX_TOKENS) has
    zero spare output-token slack to absorb an input under-count, so the
    margin below is not optional. The margin is capped by the byte bound,
    which is already known to always be >= the real count.

    on_count, if given, is called exactly once per invocation with
    keyword args (real_count, byte_bound, used, error) -- error is None on
    success, the caught exception otherwise. A failing hook must never
    break the caller; this is a diagnostic aid, same pattern as
    GeminiTransport's on_raw_response."""
    byte_bound = conservative_input_bound(request)
    try:
        real_count = count_tokens(request, credential_loader=credential_loader, http=http,
                                  timeout_s=timeout_s)
        used = min(real_count + max(256, real_count // 8), byte_bound)
        error = None
    except Exception as exc:
        real_count = None
        used = byte_bound
        error = exc
    if on_count is not None:
        try:
            on_count(real_count=real_count, byte_bound=byte_bound, used=used, error=error)
        except Exception:
            pass
    return used


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
                 http: Optional[Callable[..., Any]] = None, timeout_s: float = 120.0,
                 on_raw_response: Optional[Callable[..., None]] = None) -> None:
        if broker is None:
            raise ValueError("a hardened budget broker is required")
        if timeout_s <= 0:
            raise ValueError("timeout must be positive")
        self._load_key, self._http, self._broker, self._timeout = credential_loader, http, broker, timeout_s
        # Optional archival hook, called with (request=, payload=, context=)
        # right after a raw HTTP response is received, before parsing --
        # so even a response that fails to parse gets archived. Never
        # receives the credential (only ever in the request header, never
        # the body/payload this hook sees). A failing hook must never break
        # a real call; see the try/except around its invocation below.
        self._on_raw_response = on_raw_response

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
            if self._on_raw_response is not None:
                try:
                    self._on_raw_response(request=request, payload=payload, context=context)
                except Exception:
                    pass  # archival is a diagnostic aid, never a call blocker
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
            # promptTokenCount and totalTokenCount are the only usage fields
            # required to always be present; every other per-category count
            # is omitted entirely (not sent as 0) whenever its value would
            # be zero -- confirmed live independently for thoughtsTokenCount
            # (a heavily truncated max_output_tokens=5 call spent zero
            # thinking tokens) and cachedContentTokenCount (an uncached
            # call). candidatesTokenCount is defaulted the same way on the
            # same principle, even though not yet observed omitted, rather
            # than waiting to hit it as a third occurrence of this bug.
            prompt = _nonnegative_int(usage["promptTokenCount"])
            candidate_tokens = _nonnegative_int(usage.get("candidatesTokenCount", 0))
            thoughts = _nonnegative_int(usage.get("thoughtsTokenCount", 0))
            cached = _nonnegative_int(usage.get("cachedContentTokenCount", 0))
            total = _nonnegative_int(usage["totalTokenCount"])
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
