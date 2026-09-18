from __future__ import annotations

import copy
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

from asp_offline.models import Node

from prospective_runtime.author import deterministic_seed, request_for_turn, run_author_turns
from prospective_runtime.capability_probe import build_capability_fixtures
from prospective_runtime.deploy import deploy
from prospective_runtime.ledger import AppendOnlyRuntimeLog
from prospective_runtime.manifest import RuntimeManifest, file_sha256
from prospective_runtime.passive_nav import HabitatPassiveAdapter
from prospective_runtime.policy import apply_unanimity_policy, equivalent_graph, process_cards
from prospective_runtime.sdk_compat import content_to_rest, response_to_sdk_shape
from prospective_runtime.transport import GeminiTransport, RequestContext, canonical_json, request_hash


OBSERVED = {"nodes": [{"id": "room0", "type": "room", "label": "room", "center": [0, 0, 0]}], "edges": []}
ZERO_HASH = "0" * 64


def member(name: str, *, observed=OBSERVED):
    return {"nodes": observed["nodes"] + [{"id": name, "type": "object", "label": name,
            "center": [1, 0, 0], "dimensions": [1, 1, 1], "room_id": "room0"}], "edges": []}


def make_context(**overrides) -> RequestContext:
    values = dict(allocation_id="alloc", campaign_id="campaign", phase_id="engineering",
                  run_id="run", stage_id="stage", member_id="member", turn_id="turn",
                  attempt_id="attempt", trusted_input_token_bound=10)
    values.update(overrides)
    return RequestContext(**values)


class RecordingBroker:
    def __init__(self):
        self.calls: list[str] = []
        self.reservation_id = "reservation-1"

    def reserve(self, *, context, request_hash, max_output_tokens):
        self.calls.append("reserve")
        self.last_max_output_tokens = max_output_tokens
        self.contexts = getattr(self, "contexts", []) + [context]
        return types.SimpleNamespace(reservation_id=self.reservation_id, request_hash=request_hash)

    def dispatch(self, *, reservation, receipt):
        self.calls.append("dispatch")
        assert reservation.reservation_id == self.reservation_id
        assert receipt.request_hash == reservation.request_hash

    def settle(self, *, reservation, usage, finish_reason):
        self.calls.append("settle")
        self.settled_usage = usage
        self.settled_finish_reason = finish_reason

    def unresolved(self, *, reservation, reason):
        self.calls.append("unresolved")
        self.unresolved_reason = reason


def gemini_payload(**overrides):
    payload = {
        "responseId": "response-1",
        "modelVersion": "gemini-3.8-flash-001",
        "serviceTier": "STANDARD",
        "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2,
                           "thoughtsTokenCount": 3, "cachedContentTokenCount": 0,
                           "totalTokenCount": 10},
        "candidates": [{
            "finishReason": "STOP",
            "content": {"role": "model", "parts": [
                {"text": "thinking", "thought": True},
                {"functionCall": {"name": "move", "args": {"x": 1}}, "thoughtSignature": "opaque-sig"},
                {"text": "final answer"},
            ]},
        }],
    }
    payload.update(overrides)
    return payload


def make_request(max_output_tokens: int = 10) -> dict:
    return request_for_turn([{"role": "user", "parts": [{"text": "hello"}]}],
                            seed=1, max_output_tokens=max_output_tokens)


class TransportTests(unittest.TestCase):
    def test_generate_reserves_dispatches_then_settles_in_order(self):
        broker = RecordingBroker()
        seen = {}

        def http(url, *, body, headers, timeout, allow_redirects):
            seen["url"], seen["headers"], seen["allow_redirects"] = url, headers, allow_redirects
            return gemini_payload()

        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=http)
        result = transport.generate(make_request(), context=make_context())

        self.assertEqual(broker.calls, ["reserve", "dispatch", "settle"])
        self.assertEqual(broker.settled_finish_reason, "STOP")
        self.assertEqual(broker.settled_usage.thoughts_tokens, 3)
        self.assertEqual(seen["headers"]["x-goog-api-key"], "secret-key")
        self.assertFalse(seen["allow_redirects"])
        self.assertEqual(result.text, "final answer")

    def test_thought_signature_stays_attached_to_its_own_part_in_order(self):
        broker = RecordingBroker()
        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: gemini_payload())
        result = transport.generate(make_request(), context=make_context())

        self.assertEqual(len(result.parts), 3)
        self.assertNotIn("thoughtSignature", result.parts[0])
        self.assertEqual(result.parts[1]["thoughtSignature"], "opaque-sig")
        self.assertEqual(result.parts[1]["functionCall"]["name"], "move")
        self.assertNotIn("thoughtSignature", result.parts[2])
        self.assertEqual(result.function_calls, ({"name": "move", "args": {"x": 1}},))

    def test_thought_parts_are_excluded_from_visible_text(self):
        broker = RecordingBroker()
        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: gemini_payload())
        result = transport.generate(make_request(), context=make_context())
        self.assertNotIn("thinking", result.text)
        self.assertEqual(result.text, "final answer")

    def test_transport_failure_reports_unresolved_and_never_leaks_detail(self):
        broker = RecordingBroker()

        def failing_http(*args, **kwargs):
            raise RuntimeError("leaked-secret-detail")

        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=failing_http)
        with self.assertRaises(RuntimeError) as caught:
            transport.generate(make_request(), context=make_context())
        self.assertNotIn("leaked-secret-detail", str(caught.exception))
        self.assertEqual(broker.calls, ["reserve", "dispatch", "unresolved"])
        self.assertEqual(broker.unresolved_reason, "RuntimeError")

    def test_malformed_response_is_unresolved_not_settled(self):
        broker = RecordingBroker()
        transport = GeminiTransport(lambda: "secret-key", broker=broker,
                                    http=lambda *a, **k: gemini_payload(modelVersion="other-model"))
        with self.assertRaises(RuntimeError):
            transport.generate(make_request(), context=make_context())
        self.assertEqual(broker.calls, ["reserve", "dispatch", "unresolved"])

    def test_reservation_hash_mismatch_is_rejected(self):
        class MismatchedBroker(RecordingBroker):
            def reserve(self, *, context, request_hash, max_output_tokens):
                super().reserve(context=context, request_hash=request_hash, max_output_tokens=max_output_tokens)
                return types.SimpleNamespace(reservation_id=self.reservation_id, request_hash="wrong")

        broker = MismatchedBroker()
        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: gemini_payload())
        with self.assertRaises(RuntimeError):
            transport.generate(make_request(), context=make_context())

    def test_invalid_credential_from_loader_is_rejected(self):
        broker = RecordingBroker()
        transport = GeminiTransport(lambda: "bad\nkey", broker=broker, http=lambda *a, **k: gemini_payload())
        with self.assertRaises(RuntimeError):
            transport.generate(make_request(), context=make_context())
        self.assertEqual(broker.calls, ["reserve", "dispatch", "unresolved"])

    def test_context_validation_rejects_empty_or_negative_fields(self):
        with self.assertRaises(ValueError):
            make_context(run_id="").validate()
        with self.assertRaises(ValueError):
            make_context(campaign_id="").validate()
        with self.assertRaises(ValueError):
            make_context(attempt_id="").validate()
        with self.assertRaises(ValueError):
            make_context(trusted_input_token_bound=-1).validate()
        with self.assertRaises(ValueError):
            make_context(retry_of="").validate()
        make_context().validate()
        make_context(retry_of="attempt-0").validate()

    def test_broker_reserve_receives_the_exact_max_output_tokens(self):
        broker = RecordingBroker()
        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: gemini_payload())
        transport.generate(make_request(max_output_tokens=42), context=make_context())
        self.assertEqual(broker.last_max_output_tokens, 42)

    def test_request_shape_is_strictly_author_faithful(self):
        broker = RecordingBroker()
        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: gemini_payload())
        loose = dict(make_request())
        loose["generationConfig"] = dict(loose["generationConfig"], extra_field=True)
        with self.assertRaises(ValueError):
            transport.generate(loose, context=make_context())
        self.assertEqual(broker.calls, [])

    def test_broker_none_is_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            GeminiTransport(lambda: "secret-key", broker=None)

    def test_candidate_and_thought_tokens_over_cap_are_rejected(self):
        broker = RecordingBroker()
        oversized = gemini_payload(usageMetadata={"promptTokenCount": 1, "candidatesTokenCount": 20,
                                                   "thoughtsTokenCount": 20, "cachedContentTokenCount": 0,
                                                   "totalTokenCount": 41})
        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: oversized)
        with self.assertRaises(RuntimeError):
            transport.generate(make_request(max_output_tokens=10), context=make_context())

    def test_canonical_json_and_hash_are_stable_and_order_independent(self):
        first, second = {"a": 1, "b": 2}, {"b": 2, "a": 1}
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(request_hash(first), request_hash(second))


class AuthorTests(unittest.TestCase):
    def test_deterministic_seed_is_pure_and_stable(self):
        first = deterministic_seed("campaign", "run", "stage", "member", 0)
        second = deterministic_seed("campaign", "run", "stage", "member", 0)
        third = deterministic_seed("campaign", "run", "stage", "member", 1)
        self.assertEqual(first, second)
        self.assertNotEqual(first, third)

    def test_request_for_turn_is_author_faithful_and_bounded(self):
        request = request_for_turn([{"role": "user", "parts": [{"text": "hi"}]}], seed=7, max_output_tokens=50)
        config = request["generationConfig"]
        self.assertEqual(config["temperature"], 0.2)
        self.assertEqual(config["seed"], 7)
        self.assertEqual(config["thinkingConfig"], {"thinkingLevel": "MEDIUM", "includeThoughts": False})
        self.assertFalse(request["store"])

    def test_run_author_turns_executes_tools_and_preserves_part_order(self):
        broker = RecordingBroker()

        responses = [gemini_payload(), gemini_payload(candidates=[{
            "finishReason": "STOP",
            "content": {"role": "model", "parts": [{"text": "done"}]},
        }])]

        def http(*args, **kwargs):
            return responses.pop(0)

        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=http)
        executed = []

        def execute_tool(call):
            executed.append(call["name"])
            return {"ok": True}

        result = run_author_turns(
            transport, [{"role": "user", "parts": [{"text": "start"}]}],
            context=make_context(), seed_for_turn=lambda turn: turn,
            max_output_tokens=10, execute_tool=execute_tool,
        )
        self.assertEqual(result.text, "done")
        self.assertEqual(executed, ["move"])

    def test_run_author_turns_gives_every_turn_a_unique_attempt_and_turn_id(self):
        # attempt_id feeds the real ledger's UNIQUE(campaign_id, attempt_id)
        # constraint -- a repeated attempt_id across turns would make the
        # second turn's reservation collide with the first's.
        broker = RecordingBroker()
        responses = [gemini_payload(), gemini_payload(), gemini_payload(candidates=[{
            "finishReason": "STOP", "content": {"role": "model", "parts": [{"text": "done"}]},
        }])]
        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: responses.pop(0))
        run_author_turns(
            transport, [{"role": "user", "parts": [{"text": "start"}]}],
            context=make_context(), seed_for_turn=lambda turn: turn,
            max_output_tokens=10, execute_tool=lambda call: {"ok": True},
        )
        attempt_ids = [c.attempt_id for c in broker.contexts]
        turn_ids = [c.turn_id for c in broker.contexts]
        self.assertEqual(len(attempt_ids), len(set(attempt_ids)))
        self.assertEqual(len(turn_ids), len(set(turn_ids)))

    def test_run_author_turns_echoes_the_function_call_id_in_its_response(self):
        # google.genai.types.FunctionCall/FunctionResponse both carry `id`,
        # required to correlate a response when a turn has more than one
        # parallel call (verified against the real SDK's field shape).
        broker = RecordingBroker()
        responses = [gemini_payload(candidates=[{"finishReason": "STOP", "content": {"role": "model", "parts": [
            {"functionCall": {"name": "move", "args": {"x": 1}, "id": "call-1"}},
        ]}}]), gemini_payload(candidates=[{"finishReason": "STOP", "content": {"role": "model", "parts": [
            {"text": "done"},
        ]}}])]
        captured_bodies = []

        def http(*args, **kwargs):
            captured_bodies.append(json.loads(kwargs["body"]))
            return responses.pop(0)

        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=http)
        run_author_turns(
            transport, [{"role": "user", "parts": [{"text": "start"}]}],
            context=make_context(), seed_for_turn=lambda turn: turn,
            max_output_tokens=10, execute_tool=lambda call: {"ok": True},
        )
        second_request_contents = captured_bodies[1]["contents"]
        function_response_part = second_request_contents[-1]["parts"][0]["functionResponse"]
        self.assertEqual(function_response_part["id"], "call-1")

    def test_run_author_turns_requires_executor_for_function_calls(self):
        broker = RecordingBroker()
        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: gemini_payload())
        with self.assertRaises(RuntimeError):
            run_author_turns(transport, [{"role": "user", "parts": [{"text": "start"}]}],
                             context=make_context(), seed_for_turn=lambda turn: turn, max_output_tokens=10)

    def test_run_author_turns_halts_on_turn_budget(self):
        broker = RecordingBroker()
        transport = GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: gemini_payload())
        with self.assertRaises(TimeoutError):
            run_author_turns(transport, [{"role": "user", "parts": [{"text": "start"}]}],
                             context=make_context(), seed_for_turn=lambda turn: turn,
                             max_output_tokens=10, execute_tool=lambda call: {"ok": True}, max_turns=2)


class CapabilityProbeTests(unittest.TestCase):
    def test_fixtures_cover_every_documented_probe(self):
        fixtures = build_capability_fixtures(tools=[{"name": "move"}])
        self.assertEqual(set(fixtures), {"exact_model_medium", "function_calling",
                                          "structured_output", "truncation", "usage_fixture"})
        self.assertEqual(fixtures["exact_model_medium"]["generationConfig"]["thinkingConfig"]["thinkingLevel"], "MEDIUM")
        self.assertEqual(fixtures["truncation"]["generationConfig"]["maxOutputTokens"], 1)
        self.assertEqual(fixtures["function_calling"]["tools"], [{"name": "move"}])


class SdkCompatTests(unittest.TestCase):
    def test_content_to_rest_maps_snake_case_parts(self):
        content = types.SimpleNamespace(role="model", parts=[
            types.SimpleNamespace(text=None, inline_data=None,
                                  function_call=types.SimpleNamespace(name="move", args={"x": 1}),
                                  function_response=None, thought_signature="sig", thought=False),
        ])
        rest = content_to_rest(content)
        self.assertEqual(rest["parts"][0]["functionCall"], {"name": "move", "args": {"x": 1}})
        self.assertEqual(rest["parts"][0]["thoughtSignature"], "sig")

    def test_response_to_sdk_shape_round_trips_usage_and_parts(self):
        payload = gemini_payload()
        sdk = response_to_sdk_shape(payload)
        self.assertEqual(sdk["usage_metadata"]["thoughts_token_count"], 3)
        self.assertEqual(sdk["candidates"][0]["content"]["parts"][1]["function_call"]["name"], "move")
        self.assertEqual(sdk["candidates"][0]["content"]["parts"][1]["thought_signature"], "opaque-sig")
        self.assertEqual(sdk["response_id"], "response-1")


class PolicyTests(unittest.TestCase):
    def test_unanimity_preserves_observed_and_filters_unsupported(self):
        result = apply_unanimity_policy(OBSERVED, [member("chair")] * 4,
                                        track_id="graph0", member_ids=["a", "b", "c", "d"])
        self.assertEqual({n["id"] for n in result["nodes"]}, {"room0", "chair"})
        self.assertEqual(result["prospective_policy"]["denominator"], 4)
        mixed = apply_unanimity_policy(
            OBSERVED, [member("chair"), member("chair"), member("chair"), member("other")],
            track_id="graph0", member_ids=["a", "b", "c", "d"],
        )
        self.assertNotIn("chair", {n["id"] for n in mixed["nodes"]})
        self.assertIn("room0", {n["id"] for n in mixed["nodes"]})

    def test_wrong_completion_or_member_count_fails_closed_without_mutation(self):
        source = [member("chair") for _ in range(3)]
        before = copy.deepcopy(source)
        with self.assertRaises(ValueError):
            apply_unanimity_policy(OBSERVED, source, track_id="graph1", member_ids=["a", "b", "c"])
        self.assertEqual(source, before)

    def test_duplicate_member_identity_fails_closed(self):
        with self.assertRaises(ValueError):
            apply_unanimity_policy(OBSERVED, [member("chair")] * 4, track_id="graph0",
                                   member_ids=["a", "a", "c", "d"])

    def test_rejected_completion_fails_closed(self):
        bad = {"nodes": [{"id": "chair", "type": "object", "label": "chair"}], "edges": []}
        with self.assertRaises(ValueError):
            apply_unanimity_policy(OBSERVED, [bad, bad, bad, bad], track_id="graph0",
                                   member_ids=["a", "b", "c", "d"])

    def test_output_path_writes_yaml_once_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "graph0.yaml"
            apply_unanimity_policy(OBSERVED, [member("chair")] * 4, track_id="graph0",
                                   member_ids=["a", "b", "c", "d"], output_path=target)
            text = target.read_text()
            self.assertNotIn("{", text)
            self.assertIn("prospective_policy:", text)
            with self.assertRaises(ValueError):
                apply_unanimity_policy(OBSERVED, [member("chair")] * 4, track_id="graph0",
                                       member_ids=["a", "b", "c", "d"], output_path=target)

    def _cards(self):
        cards = []
        for track in range(4):
            for member_index in range(4):
                cards.append({
                    "track_id": f"graph{track}", "member_id": f"member{member_index}",
                    "source_path": f"habitat_scene_graph_new_graph_{track * 4 + member_index}.yaml",
                    "source_order": track * 4 + member_index, "observed": OBSERVED,
                    "completion": member("chair"),
                })
        return cards

    def test_process_cards_writes_all_sixteen_as_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "policy_out"
            results = process_cards(self._cards(), output_dir)
            self.assertEqual(len(results), 16)
            for item in results:
                text = Path(item["output_path"]).read_text()
                self.assertNotIn("{", text)
                json_parse_should_fail = True
                try:
                    json.loads(text)
                    json_parse_should_fail = False
                except json.JSONDecodeError:
                    pass
                self.assertTrue(json_parse_should_fail, "policy output must be YAML, not JSON")

    def test_process_cards_rejects_wrong_card_count(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                process_cards(self._cards()[:15], Path(directory) / "short")

    def test_equivalent_graph_compares_nodes_and_edges_only(self):
        left = {"nodes": [1], "edges": [], "prospective_policy": {"track_id": "a"}}
        right = {"nodes": [1], "edges": [], "prospective_policy": {"track_id": "b"}}
        self.assertTrue(equivalent_graph(left, right))
        self.assertFalse(equivalent_graph(left, {"nodes": [2], "edges": []}))


class PassiveNavTests(unittest.TestCase):
    def setUp(self):
        self._real_habitat_sim = sys.modules.get("habitat_sim")
        fake_module = types.ModuleType("habitat_sim")

        class FakeShortestPath:
            def __init__(self):
                self.requested_start = None
                self.requested_end = None
                self.geodesic_distance = 0.0

        fake_module.ShortestPath = FakeShortestPath
        sys.modules["habitat_sim"] = fake_module

    def tearDown(self):
        if self._real_habitat_sim is None:
            sys.modules.pop("habitat_sim", None)
        else:
            sys.modules["habitat_sim"] = self._real_habitat_sim

    def _agent_and_simulator(self, positions):
        state = types.SimpleNamespace(position=positions[0])

        class Agent:
            def get_state(self):
                return state

            def set_state(self, requested):
                state.position = tuple(requested["position"])
                return state

            def observe(self):
                return b"observation"

        class Pathfinder:
            def find_path(self, path):
                path.geodesic_distance = sum(abs(a - b) for a, b in zip(path.requested_start, path.requested_end))
                return True

        simulator = types.SimpleNamespace(pathfinder=Pathfinder())
        return Agent(), simulator

    def test_command_accumulates_realized_and_requested_geodesic_distance(self):
        agent, simulator = self._agent_and_simulator([(0.0, 0.0, 0.0)])
        records = []
        adapter = HabitatPassiveAdapter(agent, simulator, logger=records.append)

        adapter.command({"position": (1.0, 0.0, 0.0)}, stage="0", segment="s0", command_id="c0")
        adapter.command({"position": (3.0, 0.0, 0.0)}, stage="0", segment="s1", command_id="c1")

        self.assertAlmostEqual(adapter.requested_m, 3.0)
        self.assertAlmostEqual(adapter.realized_m, 3.0)
        self.assertEqual(records[0]["planner_outcome"], "delegated")
        self.assertIsNone(records[0]["contact"])
        self.assertAlmostEqual(records[1]["realized_cumulative_path_m"], 3.0)

    def test_command_never_sets_contact_true_from_a_passive_audit(self):
        agent, simulator = self._agent_and_simulator([(0.0, 0.0, 0.0)])
        records = []
        adapter = HabitatPassiveAdapter(agent, simulator, logger=records.append)
        adapter.command({"position": (1.0, 0.0, 0.0)}, stage="0", segment="s0", command_id="c0")
        self.assertIsNone(records[0]["contact"])

    def test_missing_habitat_sim_fails_soft_to_none_without_crashing(self):
        # sys.modules[name] = None is the documented way to force ImportError
        # regardless of whether a real habitat_sim is actually installed and
        # importable elsewhere on sys.path (as it is in the real deployment
        # container) -- a plain .pop() only fakes absence when nothing else
        # can satisfy the import, which isn't true there.
        sys.modules["habitat_sim"] = None
        agent, simulator = self._agent_and_simulator([(0.0, 0.0, 0.0)])
        records = []
        adapter = HabitatPassiveAdapter(agent, simulator, logger=records.append)
        adapter.command({"position": (1.0, 0.0, 0.0)}, stage="0", segment="s0", command_id="c0")
        self.assertIsNone(records[0]["shortest_path_length"])
        self.assertEqual(adapter.requested_m, 0.0)

    def test_lifecycle_event_rejects_unsupported_names(self):
        agent, simulator = self._agent_and_simulator([(0.0, 0.0, 0.0)])
        adapter = HabitatPassiveAdapter(agent, simulator)
        with self.assertRaises(ValueError):
            adapter.lifecycle_event("collision", stage="0", command_id="c0")
        adapter.lifecycle_event("reset", stage="0", command_id="c0")


class ManifestTests(unittest.TestCase):
    def _fields(self, directory, **overrides):
        outside = Path(tempfile.mkdtemp())
        start = outside / "start.json"
        start.write_text("{}")
        fields = dict(
            model="gemini-3.8-flash", reasoning="medium", policy="official_asp",
            scene="00069", seed=42, run_id="run-1", attempt_id="attempt-1",
            start_state_ref=str(start), start_state_sha256=file_sha256(start),
            output_root=str(outside / "out"), ledger_root=str(outside / "ledger"),
            path_budget_m=25, wall_clock_limit_s=3600.0,
            approved_source_sha256="a" * 64, approved_prompt_sha256="b" * 64,
            approved_policy_sha256="c" * 64, approved_navmesh_sha256="d" * 64,
            approved_reference_sha256="e" * 64, broker_allocation_id="alloc-1",
            broker_ledger_id="ledger-1",
        )
        fields.update(overrides)
        return fields

    def test_valid_manifest_round_trips_through_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = RuntimeManifest(**self._fields(directory))
            manifest.validate(repo_root=directory)
            reloaded = RuntimeManifest.from_mapping(manifest.as_dict())
            self.assertEqual(reloaded, manifest)

    def test_rejects_non_gemini_model_or_non_medium_reasoning(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                RuntimeManifest(**self._fields(directory, model="gpt-4")).validate()
            with self.assertRaises(ValueError):
                RuntimeManifest(**self._fields(directory, reasoning="high")).validate()

    def test_path_budget_must_be_an_exact_meter_value(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                RuntimeManifest(**self._fields(directory, path_budget_m=120.0)).validate()
            with self.assertRaises(ValueError):
                RuntimeManifest(**self._fields(directory, path_budget_m=100)).validate()

    def test_path_fields_must_be_absolute_outside_repo_and_not_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                RuntimeManifest(**self._fields(directory, output_root="relative/out")).validate(repo_root=directory)
            inside = str(Path(directory) / "inside_out")
            with self.assertRaises(ValueError):
                RuntimeManifest(**self._fields(directory, output_root=inside)).validate(repo_root=directory)
            real = Path(tempfile.mkdtemp())
            link = Path(directory) / "linked_ledger"
            link.symlink_to(real)
            with self.assertRaises(ValueError):
                RuntimeManifest(**self._fields(directory, ledger_root=str(link))).validate(repo_root=directory)

    def test_sha256_fields_are_validated_by_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                RuntimeManifest(**self._fields(directory, approved_source_sha256="not-a-hash")).validate()

    def test_from_mapping_rejects_unknown_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = RuntimeManifest(**self._fields(directory)).as_dict()
            raw["unexpected_field"] = "x"
            with self.assertRaises(ValueError):
                RuntimeManifest.from_mapping(raw)

    def test_load_reads_manifest_json_from_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            fields = self._fields(directory)
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(fields))
            manifest = RuntimeManifest.load(path)
            self.assertEqual(manifest.scene, "00069")


class RuntimeLedgerTests(unittest.TestCase):
    def test_append_and_verify_round_trip_and_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            log = AppendOnlyRuntimeLog(Path(directory) / "log.jsonl")
            first = log.append("attempt_started", {"run_id": "run", "attempt_id": "attempt"})
            second = log.append("request_dispatched", {"run_id": "run", "stage_id": "s",
                                                        "member_id": "m", "turn_id": "t",
                                                        "request_hash": "h" * 64})
            self.assertNotEqual(first, second)
            self.assertTrue(log.verify())

    def test_wrong_schema_or_non_string_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            log = AppendOnlyRuntimeLog(Path(directory) / "log.jsonl")
            with self.assertRaises(ValueError):
                log.append("attempt_started", {"run_id": "run"})
            with self.assertRaises(ValueError):
                log.append("attempt_started", {"run_id": "run", "attempt_id": "https://leak"})

    def test_tampered_log_fails_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log.jsonl"
            log = AppendOnlyRuntimeLog(path)
            log.append("attempt_started", {"run_id": "run", "attempt_id": "attempt"})
            log.append("attempt_started", {"run_id": "run", "attempt_id": "attempt-2"})
            lines = path.read_text().splitlines()
            tampered = json.loads(lines[0])
            tampered["data"]["attempt_id"] = "tampered"
            lines[0] = json.dumps(tampered)
            path.write_text("\n".join(lines) + "\n")
            self.assertFalse(AppendOnlyRuntimeLog(path).verify())

    def test_refuses_symlinked_log_path(self):
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / "real.jsonl"
            real.write_text("")
            link = Path(directory) / "link.jsonl"
            link.symlink_to(real)
            with self.assertRaises(ValueError):
                AppendOnlyRuntimeLog(link)


class DeployTests(unittest.TestCase):
    def _tree(self, directory, name, content=b"payload"):
        path = Path(directory) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_dry_run_verifies_hash_without_copying(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            destination = Path(directory) / "destination"
            src_file = self._tree(source, "a/file.txt")
            expected = {"a/file.txt": file_sha256(src_file)}
            deploy(source, destination, ["a/file.txt"], expected, dry_run=True)
            self.assertFalse((destination / "a/file.txt").exists())

    def test_apply_copies_only_after_hash_check_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            destination = Path(directory) / "destination"
            src_file = self._tree(source, "a/file.txt")
            expected = {"a/file.txt": file_sha256(src_file)}
            deploy(source, destination, ["a/file.txt"], expected, dry_run=False)
            self.assertEqual((destination / "a/file.txt").read_bytes(), b"payload")

    def test_hash_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            destination = Path(directory) / "destination"
            self._tree(source, "a/file.txt")
            with self.assertRaises(ValueError):
                deploy(source, destination, ["a/file.txt"], {"a/file.txt": "0" * 64}, dry_run=True)

    def test_destination_inside_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            src_file = self._tree(source, "a/file.txt")
            expected = {"a/file.txt": file_sha256(src_file)}
            with self.assertRaises(ValueError):
                deploy(source, source / "nested", ["a/file.txt"], expected, dry_run=True)

    def test_source_path_escaping_via_traversal_or_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            destination = Path(directory) / "destination"
            source.mkdir()
            outside = self._tree(directory, "outside/secret.txt")
            link = source / "escape.txt"
            link.symlink_to(outside)
            with self.assertRaises(ValueError):
                deploy(source, destination, ["escape.txt"], {"escape.txt": file_sha256(outside)}, dry_run=True)
            with self.assertRaises(ValueError):
                deploy(source, destination, ["../outside/secret.txt"], {"../outside/secret.txt": file_sha256(outside)}, dry_run=True)

    def test_preexisting_destination_file_or_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            destination = Path(directory) / "destination"
            src_file = self._tree(source, "a/file.txt")
            expected = {"a/file.txt": file_sha256(src_file)}
            self._tree(destination, "a/file.txt", b"already-there")
            with self.assertRaises(ValueError):
                deploy(source, destination, ["a/file.txt"], expected, dry_run=True)

            destination2 = Path(directory) / "destination2"
            elsewhere = self._tree(directory, "elsewhere/file.txt")
            destination2.mkdir()
            (destination2 / "a").mkdir()
            (destination2 / "a" / "file.txt").symlink_to(elsewhere)
            with self.assertRaises(ValueError):
                deploy(source, destination2, ["a/file.txt"], expected, dry_run=True)


if __name__ == "__main__":
    unittest.main()
