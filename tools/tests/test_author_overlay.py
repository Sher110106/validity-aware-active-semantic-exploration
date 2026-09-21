from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from prospective_integration.author_overlay import (
    CHECK_COLLISION_TOOL,
    build_completion_contents,
    build_refinement_contents,
    make_check_collision_executor,
    run_completion_turns,
    run_single_turn,
)
from prospective_runtime.transport import GeminiTransport, RequestContext


def make_context(**overrides) -> RequestContext:
    values = dict(allocation_id="alloc", campaign_id="campaign", phase_id="engineering",
                  run_id="run", stage_id="stage", member_id="member", turn_id="turn",
                  attempt_id="attempt", trusted_input_token_bound=1000)
    values.update(overrides)
    return RequestContext(**values)


class RecordingBroker:
    def __init__(self):
        self.calls = []
        self.contexts = []

    def reserve(self, *, context, request_hash, max_output_tokens):
        self.calls.append("reserve")
        self.contexts.append(context)
        return type("R", (), {"reservation_id": "r", "request_hash": request_hash})()

    def dispatch(self, *, reservation, receipt):
        self.calls.append("dispatch")

    def settle(self, *, reservation, usage, finish_reason):
        self.calls.append("settle")

    def unresolved(self, *, reservation, reason):
        self.calls.append("unresolved")


def gemini_payload(**overrides):
    # Shape confirmed against a real live response (capability probe, 2026-09-19).
    payload = {
        "responseId": "response-1", "modelVersion": "gemini-3.8-flash",
        "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2, "thoughtsTokenCount": 3,
                          "cachedContentTokenCount": 0, "totalTokenCount": 10, "serviceTier": "standard"},
        "candidates": [{"finishReason": "STOP",
                       "content": {"role": "model", "parts": [{"text": "final answer"}]}}],
    }
    payload.update(overrides)
    return payload


class ContentBuildingTests(unittest.TestCase):
    def test_completion_contents_include_prompt_yaml_and_base64_images(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "a.jpg"
            image_path.write_bytes(b"fake-jpeg-bytes")
            contents = build_completion_contents("prompt-text", "nodes: []", directory)
            self.assertEqual(len(contents), 1)
            self.assertEqual(contents[0]["role"], "user")
            parts = contents[0]["parts"]
            self.assertEqual(parts[0], {"text": "prompt-text"})
            self.assertEqual(parts[1], {"text": "nodes: []"})
            self.assertEqual(parts[2]["inlineData"]["mimeType"], "image/jpeg")
            decoded = base64.b64decode(parts[2]["inlineData"]["data"])
            self.assertEqual(decoded, b"fake-jpeg-bytes")

    def test_refinement_contents_assemble_the_structured_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            contents = build_refinement_contents("prompt", "new-items-yaml", "original-yaml", directory)
            text = contents[0]["parts"][0]["text"]
            self.assertIn("## new_items:", text)
            self.assertIn("new-items-yaml", text)
            self.assertIn("## original_scene:", text)
            self.assertIn("original-yaml", text)


class CheckCollisionExecutorTests(unittest.TestCase):
    def test_valid_call_forwards_exact_positional_arguments(self):
        seen = {}

        def check_collision(label, cx, cy, cz, sx, sy, sz):
            seen.update(label=label, cx=cx, cy=cy, cz=cz, sx=sx, sy=sy, sz=sz)
            return {"valid": True}

        execute = make_check_collision_executor(check_collision)
        result = execute({"name": "check_collision", "args": {
            "label": "chair", "center_x": 1, "center_y": 2, "center_z": 3,
            "size_x": 4, "size_y": 5, "size_z": 6,
        }})
        self.assertEqual(result, {"valid": True})
        self.assertEqual(seen, {"label": "chair", "cx": 1, "cy": 2, "cz": 3, "sx": 4, "sy": 5, "sz": 6})

    def test_missing_argument_is_reported_without_calling_through(self):
        called = []
        execute = make_check_collision_executor(lambda *a: called.append(a) or {})
        result = execute({"name": "check_collision", "args": {"label": "chair"}})
        self.assertIn("missing argument", result["error"])
        self.assertEqual(called, [])

    def test_unknown_function_name_is_reported(self):
        execute = make_check_collision_executor(lambda *a: {})
        result = execute({"name": "other_fn", "args": {}})
        self.assertEqual(result, {"error": "Unknown function other_fn"})


class RunTurnsTests(unittest.TestCase):
    def test_run_completion_turns_executes_check_collision_and_returns_text(self):
        broker = RecordingBroker()
        responses = [
            gemini_payload(candidates=[{"finishReason": "STOP", "content": {"role": "model", "parts": [
                {"functionCall": {"name": "check_collision", "args": {
                    "label": "chair", "center_x": 1, "center_y": 2, "center_z": 3,
                    "size_x": 1, "size_y": 1, "size_z": 1,
                }}},
            ]}}]),
            gemini_payload(candidates=[{"finishReason": "STOP", "content": {"role": "model", "parts": [
                {"text": "```yaml\nnodes: []\nedges: []\n```"},
            ]}}]),
        ]
        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: responses.pop(0))
        execute_tool = make_check_collision_executor(lambda *a: {"valid": True, "collision_count": 0})

        text = run_completion_turns(
            transport, [{"role": "user", "parts": [{"text": "hi"}]}],
            context=make_context(), seed_for_turn=lambda turn: turn,
            max_output_tokens=100, execute_tool=execute_tool,
        )
        self.assertIn("nodes: []", text)

    def test_run_completion_turns_returns_none_on_turn_budget_timeout(self):
        broker = RecordingBroker()
        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: gemini_payload(
            candidates=[{"finishReason": "STOP", "content": {"role": "model", "parts": [
                {"functionCall": {"name": "check_collision", "args": {
                    "label": "x", "center_x": 0, "center_y": 0, "center_z": 0,
                    "size_x": 1, "size_y": 1, "size_z": 1,
                }}},
            ]}}]))
        execute_tool = make_check_collision_executor(lambda *a: {"valid": True})
        result = run_completion_turns(
            transport, [{"role": "user", "parts": [{"text": "hi"}]}],
            context=make_context(), seed_for_turn=lambda turn: turn,
            max_output_tokens=10, execute_tool=execute_tool, max_turns=2,
        )
        self.assertIsNone(result)

    def test_run_single_turn_returns_plain_text_with_no_tools(self):
        broker = RecordingBroker()
        seen_requests = []

        def http(*args, **kwargs):
            import json
            seen_requests.append(json.loads(kwargs["body"]))
            return gemini_payload()

        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=http)
        text = run_single_turn(
            transport, [{"role": "user", "parts": [{"text": "refine this"}]}],
            context=make_context(), seed=42, max_output_tokens=50,
        )
        self.assertEqual(text, "final answer")
        self.assertNotIn("tools", seen_requests[0])

    def test_run_single_turn_uses_a_caller_supplied_input_bound_fn(self):
        broker = RecordingBroker()
        transport = GeminiTransport(lambda: "secret-key", broker=broker,
                                    http=lambda *a, **k: gemini_payload())
        run_single_turn(
            transport, [{"role": "user", "parts": [{"text": "refine this"}]}],
            context=make_context(), seed=42, max_output_tokens=50,
            input_bound_fn=lambda request: 999,
        )
        self.assertEqual(broker.contexts[0].trusted_input_token_bound, 999)

    def test_run_completion_turns_uses_a_caller_supplied_input_bound_fn(self):
        broker = RecordingBroker()
        transport = GeminiTransport(lambda: "secret-key", broker=broker,
                                    http=lambda *a, **k: gemini_payload(candidates=[{
                                        "finishReason": "STOP",
                                        "content": {"role": "model", "parts": [{"text": "done"}]},
                                    }]))
        run_completion_turns(
            transport, [{"role": "user", "parts": [{"text": "start"}]}],
            context=make_context(), seed_for_turn=lambda turn: turn,
            max_output_tokens=10, execute_tool=lambda call: {"ok": True},
            input_bound_fn=lambda request: 555,
        )
        self.assertEqual(broker.contexts[0].trusted_input_token_bound, 555)


if __name__ == "__main__":
    unittest.main()
