"""Injectable native-shaped broker; paid transport is intentionally external."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .config import CONTEXT_LIMIT, MODEL_ID, OUTPUT_LIMIT, THINKING_LEVEL, cost_microdollars
from .errors import AccountingHalt, PolicyError, BrokerError
from .estimator import NativeCount, conservative_input_bound, validate_native_count
from .ledger import Ledger

class TransportFailure(BrokerError):
    """A generic transport failure whose detail is never exposed or logged."""

@dataclass(frozen=True)
class FunctionCall:
    name: str
    args: dict[str, Any]

@dataclass(frozen=True)
class ParsedResponse:
    text: str
    function_calls: tuple[FunctionCall, ...]
    thought_signatures: tuple[str, ...]
    finish_reason: str
    truncated: bool
    usage: dict[str, int]
    model: str
    response_id: str


def parse_response(raw: dict[str, Any]) -> ParsedResponse:
    if not isinstance(raw, dict):
        raise AccountingHalt("response is not an object")
    model = raw.get("model")
    if model != MODEL_ID or ("model_version" in raw and raw["model_version"] != MODEL_ID):
        raise AccountingHalt("response model is not allowlisted")
    response_id = raw.get("response_id")
    if not isinstance(response_id, str) or not response_id:
        raise AccountingHalt("response identifier is missing")
    usage = raw.get("usage")
    if not isinstance(usage, dict):
        raise AccountingHalt("response usage is missing")
    names = ("prompt_tokens", "candidate_tokens", "thought_tokens", "cached_tokens", "total_tokens")
    if any(not isinstance(usage.get(name), int) or usage[name] < 0 for name in names):
        raise AccountingHalt("response usage is incomplete")
    if usage["total_tokens"] != usage["prompt_tokens"] + usage["candidate_tokens"] + usage["thought_tokens"]:
        raise AccountingHalt("response usage totals are inconsistent")
    if usage["cached_tokens"] > usage["prompt_tokens"]:
        raise AccountingHalt("response cached usage is invalid")
    finish = raw.get("finish_reason")
    if finish not in {"STOP", "MAX_TOKENS", "LENGTH", "SAFETY", "OTHER"}:
        raise AccountingHalt("response finish reason is invalid")
    if raw.get("service_tier") != "standard":
        raise AccountingHalt("response service tier is invalid")
    text = raw.get("text", "")
    if not isinstance(text, str):
        raise AccountingHalt("response text is invalid")
    calls: list[FunctionCall] = []
    for item in raw.get("function_calls", ()):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("args"), dict):
            raise AccountingHalt("response function call is invalid")
        calls.append(FunctionCall(item["name"], item["args"]))
    signatures = raw.get("thought_signatures", ())
    if any(not isinstance(signature, str) for signature in signatures):
        raise AccountingHalt("response thought signature is invalid")
    return ParsedResponse(text, tuple(calls), tuple(signatures), finish,
                          finish in {"MAX_TOKENS", "LENGTH"},
                          {name: usage[name] for name in names}, model, response_id)


class Broker:
    def __init__(self, ledger: Ledger, transport: Callable[..., dict[str, Any]]):
        self.ledger = ledger
        self.transport = transport

    def request(self, *, envelope: Any, allocation_id: str, metadata: dict[str, str],
                max_output_tokens: int, native_count: NativeCount | None = None,
                model: str = MODEL_ID, thinking_level: str = THINKING_LEVEL,
                retry_of: str | None = None) -> ParsedResponse:
        if model != MODEL_ID or thinking_level != THINKING_LEVEL:
            raise PolicyError("model or thinking policy rejected")
        if not isinstance(max_output_tokens, int) or not 0 < max_output_tokens <= OUTPUT_LIMIT:
            raise PolicyError("explicit output cap rejected")
        try:
            input_bound = validate_native_count(envelope, native_count) if native_count is not None else conservative_input_bound(envelope)
        except (TypeError, ValueError):
            raise PolicyError("trusted input bound is unavailable")
        if input_bound + max_output_tokens > CONTEXT_LIMIT:
            raise PolicyError("context bound rejected")
        reservation_record = self.ledger.reserve(
            allocation_id=allocation_id, max_output_tokens=max_output_tokens,
            input_bound=input_bound, model=model, thinking_level=thinking_level,
            retry_of=retry_of, **metadata,
        )
        dispatch_id = self.ledger.mark_dispatched(reservation_record.request_id)
        request_metadata = {
            "model": MODEL_ID,
            "thinking_level": THINKING_LEVEL,
            "max_output_tokens": max_output_tokens,
            "maxOutputTokens": max_output_tokens,
            "dispatch_id": dispatch_id,
        }
        try:
            raw = self.transport(envelope=envelope, metadata=request_metadata)
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise TransportFailure("transport failed; reservation retained") from None
        parsed = parse_response(raw)
        if parsed.usage["candidate_tokens"] + parsed.usage["thought_tokens"] > max_output_tokens:
            raise AccountingHalt("generated tokens exceed explicit cap; reservation retained")
        self.ledger.settle(
            reservation_record.request_id, model=parsed.model, service_tier=raw["service_tier"],
            input_tokens=parsed.usage["prompt_tokens"], candidate_tokens=parsed.usage["candidate_tokens"],
            thought_tokens=parsed.usage["thought_tokens"], cached_tokens=parsed.usage["cached_tokens"],
            total_tokens=parsed.usage["total_tokens"], provider_response_id=parsed.response_id,
            finish_reason=parsed.finish_reason,
        )
        return parsed
