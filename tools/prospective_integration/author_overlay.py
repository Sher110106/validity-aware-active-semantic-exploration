"""Reusable pieces of the Gemini-routing overlay for the pinned author
checkout's llm_completion.py.

llm_completion.py's only two Gemini-calling methods
(generate_completion_response, generate_refinement_response) are replaced
in a SIBLING checkout (never the pinned one) to build a REST envelope from
the exact same prompt/YAML/image content the pinned code already
assembles, run it through the real, audited gemini_campaign ledger via
prospective_runtime's transport and author tool-loop, and hand back a
plain string -- the only thing the pinned parse_response()/caller ever
consumed from the original response object. Nothing about the author's
own preprocessing, validate_feasibility, or response parsing changes.

Built and tested here, offline, so the patch actually applied to the
sibling's llm_completion.py stays as small and mechanical as possible.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence, Union

from dataclasses import replace

from prospective_runtime.author import request_for_turn, run_author_turns
from prospective_runtime.transport import GeminiTransport, RequestContext, conservative_input_bound

InputBoundFn = Callable[[Mapping[str, Any]], int]

CHECK_COLLISION_TOOL = {
    "functionDeclarations": [{
        "name": "check_collision",
        "description": "Checks collision for a box centered at (center_x, center_y, center_z).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "label": {"type": "STRING"},
                "center_x": {"type": "NUMBER"},
                "center_y": {"type": "NUMBER"},
                "center_z": {"type": "NUMBER"},
                "size_x": {"type": "NUMBER"},
                "size_y": {"type": "NUMBER"},
                "size_z": {"type": "NUMBER"},
            },
            "required": ["label", "center_x", "center_y", "center_z", "size_x", "size_y", "size_z"],
        },
    }],
}

_REQUIRED_COLLISION_ARGS = ("label", "center_x", "center_y", "center_z", "size_x", "size_y", "size_z")


def _image_part(image_path: Union[str, Path]) -> dict:
    data = Path(image_path).read_bytes()
    return {"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(data).decode("ascii")}}


def build_completion_contents(user_prompt: str, yaml_content: str, image_dir: Union[str, Path]) -> list[dict]:
    """The same content the pinned code sends: prompt text, the YAML scene
    graph as text, then every image in image_dir, all in one user turn."""
    parts: list[dict] = [{"text": user_prompt}, {"text": yaml_content}]
    for image_path in sorted(Path(image_dir).iterdir()):
        parts.append(_image_part(image_path))
    return [{"role": "user", "parts": parts}]


def build_refinement_contents(user_prompt: str, new_items_yaml: str, original_scene_content: str,
                              image_dir: Union[str, Path]) -> list[dict]:
    text = "\n".join([user_prompt, "## new_items:", new_items_yaml, "---",
                      "## original_scene:", original_scene_content])
    parts: list[dict] = [{"text": text}]
    for image_path in sorted(Path(image_dir).iterdir()):
        parts.append(_image_part(image_path))
    return [{"role": "user", "parts": parts}]


def make_check_collision_executor(
    check_collision: Callable[[str, float, float, float, float, float, float], Mapping[str, Any]],
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    """Same argument validation the pinned tool-calling loop already does,
    now driven by our REST-shaped function_call dict instead of a
    google.genai FunctionCall object."""

    def execute_tool(call: Mapping[str, Any]) -> Mapping[str, Any]:
        name = call.get("name")
        args = call.get("args") or {}
        if name != "check_collision":
            return {"error": f"Unknown function {name}"}
        missing = [n for n in _REQUIRED_COLLISION_ARGS if n not in args]
        if missing:
            return {"error": "check_collision missing argument(s): " + ", ".join(missing)}
        return dict(check_collision(
            args["label"], args["center_x"], args["center_y"], args["center_z"],
            args["size_x"], args["size_y"], args["size_z"],
        ))

    return execute_tool


def run_completion_turns(transport: GeminiTransport, initial_contents: Sequence[Mapping[str, Any]], *,
                         context: RequestContext, seed_for_turn: Callable[[int], int],
                         max_output_tokens: int, execute_tool: Callable[[Mapping[str, Any]], Mapping[str, Any]],
                         max_turns: int = 50,
                         input_bound_fn: InputBoundFn = conservative_input_bound) -> Optional[str]:
    """Drives the check_collision tool loop; returns None on a turn-budget
    timeout, matching the pinned code's own implicit `return None` when its
    while loop exhausts max_turns without a final text-only response --
    the caller (parse_response, then the per-member drop logic in
    complete_scene_graph) already handles a None/unparseable result.
    input_bound_fn defaults to the byte-conservative bound (unchanged
    behavior); pass overlay_runtime.build_input_bound_fn(...)'s result to
    use the real, measured token count instead."""
    try:
        result = run_author_turns(
            transport, initial_contents, context=context, seed_for_turn=seed_for_turn,
            max_output_tokens=max_output_tokens, tools=[CHECK_COLLISION_TOOL],
            execute_tool=execute_tool, max_turns=max_turns, input_bound_fn=input_bound_fn,
        )
    except TimeoutError:
        return None
    return result.text


def run_single_turn(transport: GeminiTransport, initial_contents: Sequence[Mapping[str, Any]], *,
                    context: RequestContext, seed: int, max_output_tokens: int,
                    input_bound_fn: InputBoundFn = conservative_input_bound) -> str:
    """For generate_refinement_response: one plain call, no tools. The
    caller's context.trusted_input_token_bound is overridden with a bound
    computed from this exact request (images included), the same way
    run_author_turns computes one fresh per turn -- a caller-supplied
    guess could easily under-reserve once images are in the request.
    input_bound_fn defaults to the byte-conservative bound (unchanged
    behavior); pass overlay_runtime.build_input_bound_fn(...)'s result to
    use the real, measured token count instead."""
    request = request_for_turn(initial_contents, seed=seed, max_output_tokens=max_output_tokens)
    accurate_context = replace(context, trusted_input_token_bound=input_bound_fn(request))
    result = transport.generate(request, context=accurate_context)
    return result.text
