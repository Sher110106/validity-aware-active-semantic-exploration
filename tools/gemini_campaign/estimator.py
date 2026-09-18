"""Local token bounds; native count-token metadata can be supplied separately."""
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class TokenBounds:
    input_tokens: int
    max_output_tokens: int
    max_thought_tokens: int

    @property
    def input_bound(self) -> int: return self.input_tokens


def estimate_text_tokens(text: str) -> int:
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    # A deliberately conservative local estimate: one token per four UTF-8 bytes,
    # rounded up, with one token for non-empty text.
    return 0 if not text else max(1, (len(text.encode("utf-8")) + 3) // 4)


def estimate_request_tokens(text: str, max_output_tokens: int, max_thought_tokens: int) -> TokenBounds:
    if max_output_tokens < 0 or max_thought_tokens < 0:
        raise ValueError("token bounds must be non-negative")
    return TokenBounds(estimate_text_tokens(text), max_output_tokens, max_thought_tokens)


class NativeTokenCounter:
    """Adapter for operator-supplied native count metadata; never performs I/O."""
    def __init__(self, count_fn): self._count_fn = count_fn
    def count(self, request) -> int:
        value = self._count_fn(request)
        if not isinstance(value, int) or value < 0: raise ValueError("invalid native token count")
        return value
