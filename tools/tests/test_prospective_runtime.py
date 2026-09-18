from __future__ import annotations

import copy, json, tempfile, unittest
from pathlib import Path

from asp_offline.models import Node
from prospective_runtime.author import deterministic_seed, request_for_turn, run_author_turns
from prospective_runtime.manifest import RuntimeManifest
from prospective_runtime.passive_nav import PassiveNavAudit
from prospective_runtime.policy import apply_unanimity_policy
from prospective_runtime.transport import GeminiTransport


OBSERVED = {"nodes": [{"id": "room0", "type": "room", "label": "room", "center": [0, 0, 0]}], "edges": []}

def member(name: str, *, observed=OBSERVED):
    label = "chair" if name == "chair" else name
    return {"nodes": observed["nodes"] + [{"id": name, "type": "object", "label": label, "center": [1, 0, 0], "dimensions": [1, 1, 1], "room_id": "room0"}], "edges": []}


class Broker:
    def __init__(self): self.ids = []
    def reserve(self, *, request_id): self.ids.append(request_id)


class TransportTests(unittest.TestCase):
    def test_rest_fields_and_reservation_without_raw_logging(self):
        broker = Broker()
        def fake(url, *, body, headers, timeout):
            self.assertNotIn("secret", url); self.assertEqual(headers["x-goog-api-key"], "secret")
            return {"responseId": "r", "modelVersion": "gemini-3.8-flash-001", "usageMetadata": {"promptTokenCount": 2, "candidatesTokenCount": 3, "thoughtsTokenCount": 4, "cachedContentTokenCount": 5}, "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "ok"}, {"functionCall": {"name": "x", "args": {}}, "thoughtSignature": "opaque"}]}}]}
        result = GeminiTransport("secret", http=fake, broker=broker).generate({}, request_id="a")
        self.assertEqual(result.usage.thoughts_tokens, 4); self.assertEqual(result.thought_signatures, ("opaque",)); self.assertEqual(broker.ids, ["a"])

    def test_model_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            GeminiTransport._parse({"modelVersion": "other", "candidates": [{"content": {"parts": []}}]})

    def test_seed_and_reasoning_are_explicit_and_bounded(self):
        request = request_for_turn([], seed=42, max_output_tokens=100, temperature=0.4)
        self.assertEqual(request["generationConfig"]["seed"], 42)
        self.assertEqual(request["generationConfig"]["thinkingConfig"]["thinkingLevel"], "MEDIUM")
        with self.assertRaises(ValueError): request_for_turn([], seed=1, max_output_tokens=0, temperature=0)
        self.assertEqual(deterministic_seed("c", "r", "s", "m", 1), deterministic_seed("c", "r", "s", "m", 1))


class PolicyTests(unittest.TestCase):
    def test_unanimity_preserves_observed_and_filters_unsupported(self):
        result = apply_unanimity_policy(OBSERVED, [member("chair")] * 4, track_id="graph0")
        self.assertEqual({n["id"] for n in result["nodes"]}, {"room0", "chair"})
        self.assertEqual(result["prospective_policy"]["denominator"], 4)
        result = apply_unanimity_policy(OBSERVED, [member("chair"), member("chair"), member("chair"), member("other")], track_id="graph0")
        self.assertNotIn("chair", {n["id"] for n in result["nodes"]})
        self.assertIn("room0", {n["id"] for n in result["nodes"]})

    def test_missing_member_fails_closed_and_does_not_mutate_source(self):
        source = [member("chair") for _ in range(3)]; before = copy.deepcopy(source)
        with self.assertRaises(ValueError): apply_unanimity_policy(OBSERVED, source, track_id="graph1")
        self.assertEqual(source, before)

    def test_duplicate_member_identity_fails_closed(self):
        with self.assertRaises(ValueError):
            apply_unanimity_policy(OBSERVED, [member("chair")] * 4, track_id="graph0", member_ids=["a", "a", "c", "d"])


class NavTests(unittest.TestCase):
    def test_passive_audit_is_pose_and_observation_identical(self):
        class Fake:
            def __init__(self): self.commands=[]
            def set_pose(self, pose): self.commands.append(pose); return pose
            def observe(self): return b"observation"
        fake, records = Fake(), []
        audit = PassiveNavAudit(fake, logger=records.append)
        self.assertEqual(audit.command([1, 0, 0], stage="0", segment="s", command_id="c"), [1, 0, 0])
        self.assertEqual(audit.observe(), b"observation"); self.assertEqual(fake.commands, [[1, 0, 0]])
        self.assertFalse(records[0]["contact"])


class ManifestTests(unittest.TestCase):
    def test_exact_model_and_meter_budget(self):
        with tempfile.TemporaryDirectory() as d:
            m = RuntimeManifest("gemini-3.8-flash", "medium", "official_asp", 42, f"{d}/start", f"{d}/out", f"{d}/ledger", 120)
            m.validate(); self.assertEqual(m.path_budget_m, 120)
            with self.assertRaises(ValueError): RuntimeManifest("other", "medium", "official_asp", 1, f"{d}/s", f"{d}/o", f"{d}/l").validate()
