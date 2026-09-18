"""Canonical request hashing and fail-closed token bounds."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

from .config import MODEL_ID

@dataclass(frozen=True)
class NativeCount:
    tokens: int
    request_hash: str
    model: str = MODEL_ID


def canonical_request(envelope: Any) -> bytes:
    try:
        return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("request envelope is not canonicalizable") from exc


def request_hash(envelope: Any) -> str:
    return hashlib.sha256(canonical_request(envelope)).hexdigest()


def conservative_input_bound(envelope: Any) -> int:
    """One token per serialized byte is intentionally over-conservative.

    It covers Unicode, tool schemas/arguments, chat history, and image/blob
    descriptors represented in the complete envelope. Arbitrary objects fail.
    """
    serialized = canonical_request(envelope)
    if not serialized:
        raise ValueError("empty request has no trusted bound")
    return len(serialized)


def validate_native_count(envelope: Any, count: NativeCount) -> int:
    if not isinstance(count, NativeCount) or count.model != MODEL_ID:
        raise ValueError("native count metadata is invalid")
    if count.tokens < 0 or count.request_hash != request_hash(envelope):
        raise ValueError("native count does not match request")
    return count.tokens


class NativeTokenCounter:
    """Injectable countTokens metadata adapter; it performs no external I/O."""
    def __init__(self, count_fn: Callable[[Any], int]):
        self._count_fn = count_fn

    def count(self, envelope: Any) -> NativeCount:
        value = self._count_fn(envelope)
        if not isinstance(value, int) or value < 0:
            raise ValueError("invalid native token count")
        return NativeCount(value, request_hash(envelope))
