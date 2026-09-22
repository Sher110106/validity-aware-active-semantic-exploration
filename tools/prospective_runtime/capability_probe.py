from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from .author import request_for_turn


def build_capability_fixtures(*, seed: int = 1, max_output_tokens: int = 1024,
                              tools: Optional[Sequence[Mapping[str, Any]]] = None) -> dict[str, dict[str, Any]]:
    base = request_for_turn([{"role": "user", "parts": [{"text": "probe"}]}], seed=seed,
                            max_output_tokens=max_output_tokens, tools=tools)
    return {"exact_model_medium": base, "function_calling": dict(base, tools=list(tools or [])),
            "structured_output": dict(base, generationConfig=dict(base["generationConfig"], responseMimeType="application/json")),
            "truncation": request_for_turn(base["contents"], seed=seed, max_output_tokens=1, tools=tools),
            "usage_fixture": {"required_fields": ["usageMetadata", "modelVersion", "responseId"]}}
