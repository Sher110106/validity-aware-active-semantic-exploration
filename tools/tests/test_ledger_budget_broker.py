"""LedgerBudgetBroker against a REAL gemini_campaign.Ledger (not a fake) --
the bridge deferred when the four prospective branches were first merged."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gemini_campaign.config import cost_microdollars
from gemini_campaign.errors import AccountingHalt

from prospective_integration.ledger_budget_broker import LedgerBudgetBroker

from prospective_runtime.author import run_author_turns
from prospective_runtime.transport import GeminiTransport, RequestContext

from gemini_campaign.ledger import Ledger


def make_context(ledger: Ledger, *, allocation_id: str, attempt_id: str = "attempt",
                 phase_id: str = "engineering", **overrides) -> RequestContext:
    values = dict(allocation_id=allocation_id, campaign_id="campaign", phase_id=phase_id,
                  run_id="run", stage_id="stage", member_id="member", turn_id="turn",
                  attempt_id=attempt_id, trusted_input_token_bound=10)
    values.update(overrides)
    return RequestContext(**values)


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


class LedgerBudgetBrokerTests(unittest.TestCase):
    def _ledger_and_allocation(self, tmp: str, *, amount=1_000_000, phase="engineering"):
        ledger = Ledger(str(Path(tmp) / "ledger.sqlite"))
        allocation = ledger.allocate(campaign_id="campaign", phase_id=phase, amount_microusd=amount)
        return ledger, allocation

    def test_happy_path_settles_the_real_ledger_at_the_campaign_price(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger, allocation = self._ledger_and_allocation(tmp)
            broker = LedgerBudgetBroker(ledger)
            transport = GeminiTransport(lambda: "secret-key", broker=broker,
                                        http=lambda *a, **k: gemini_payload())
            request = {"contents": [{"role": "user", "parts": [{"text": "hi"}]}], "store": False,
                      "generationConfig": {"temperature": 0.2, "maxOutputTokens": 10,
                          "candidateCount": 1, "seed": 1,
                          "thinkingConfig": {"thinkingLevel": "MEDIUM", "includeThoughts": False}}}
            context = make_context(ledger, allocation_id=allocation.allocation_id)
            result = transport.generate(request, context=context)
            self.assertEqual(result.text, "final answer")

            summary = ledger.summary()
            self.assertEqual(summary["unresolved_requests"], 0)
            expected = cost_microdollars(5, 2 + 3)  # prompt tokens, candidate+thought tokens
            self.assertEqual(summary["settled_microusd"], expected)
            ledger.close()

    def test_multi_turn_function_calls_settle_each_turn_uniquely_in_the_real_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger, allocation = self._ledger_and_allocation(tmp)
            broker = LedgerBudgetBroker(ledger)
            responses = [
                gemini_payload(responseId="response-1", candidates=[{"finishReason": "STOP", "content": {"role": "model", "parts": [
                    {"functionCall": {"name": "move", "args": {"x": 1}}, "thoughtSignature": "sig"},
                ]}}]),
                gemini_payload(responseId="response-2"),
            ]
            transport = GeminiTransport(lambda: "secret-key", broker=broker,
                                        http=lambda *a, **k: responses.pop(0))
            context = make_context(ledger, allocation_id=allocation.allocation_id, attempt_id="author-attempt")
            result = run_author_turns(
                transport, [{"role": "user", "parts": [{"text": "start"}]}], context=context,
                seed_for_turn=lambda turn: turn, max_output_tokens=10,
                execute_tool=lambda call: {"ok": True},
            )
            self.assertEqual(result.text, "final answer")
            export = ledger.export()
            self.assertEqual(len(export["requests"]), 2)
            self.assertEqual({r["attempt_id"] for r in export["requests"]},
                             {"author-attempt:0", "author-attempt:1"})
            self.assertTrue(all(r["state"] == "SETTLED" for r in export["requests"]))
            ledger.close()

    def test_transport_failure_leaves_the_reservation_unresolved_in_the_real_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger, allocation = self._ledger_and_allocation(tmp)
            broker = LedgerBudgetBroker(ledger)

            def failing_http(*args, **kwargs):
                raise RuntimeError("network detail that must never leak")

            transport = GeminiTransport(lambda: "secret-key", broker=broker, http=failing_http)
            request = {"contents": [{"role": "user", "parts": [{"text": "hi"}]}], "store": False,
                      "generationConfig": {"temperature": 0.2, "maxOutputTokens": 10,
                          "candidateCount": 1, "seed": 1,
                          "thinkingConfig": {"thinkingLevel": "MEDIUM", "includeThoughts": False}}}
            context = make_context(ledger, allocation_id=allocation.allocation_id)
            with self.assertRaises(RuntimeError) as caught:
                transport.generate(request, context=context)
            self.assertNotIn("network detail", str(caught.exception))

            summary = ledger.summary()
            self.assertEqual(summary["unresolved_requests"], 1)
            self.assertGreater(summary["reserved_microusd"], 0)
            ledger.close()

    def test_insufficient_allocation_raises_accounting_halt_not_a_generic_failure(self):
        # reserve() runs BEFORE generate()'s try/except, so a budget refusal
        # must surface as the real ledger's own AccountingHalt, never
        # disguised as the generic "Gemini attempt unresolved" transport
        # failure -- callers need to tell the two apart.
        with tempfile.TemporaryDirectory() as tmp:
            ledger, allocation = self._ledger_and_allocation(tmp, amount=1)
            broker = LedgerBudgetBroker(ledger)
            transport = GeminiTransport(lambda: "secret-key", broker=broker,
                                        http=lambda *a, **k: gemini_payload())
            request = {"contents": [{"role": "user", "parts": [{"text": "hi"}]}], "store": False,
                      "generationConfig": {"temperature": 0.2, "maxOutputTokens": 65536,
                          "candidateCount": 1, "seed": 1,
                          "thinkingConfig": {"thinkingLevel": "MEDIUM", "includeThoughts": False}}}
            context = make_context(ledger, allocation_id=allocation.allocation_id,
                                   trusted_input_token_bound=1)
            with self.assertRaises(AccountingHalt):
                transport.generate(request, context=context)
            self.assertEqual(ledger.summary()["unresolved_requests"], 0)  # never reserved at all
            ledger.close()

    def test_a_pipeline_style_retry_with_the_same_deterministic_attempt_id_no_longer_loops_forever(self):
        # End-to-end regression for the live 2026-09-22 failure: a pipeline
        # that reruns a whole ensemble member from turn 0 after any
        # unresolved call reconstructs the exact same deterministic
        # attempt_id/turn sequence. Before resolve_attempt_id was wired in,
        # the second run_author_turns call below raised AccountingHalt
        # ("request identity is already used") on its very first turn,
        # every time, forever. It must now succeed.
        with tempfile.TemporaryDirectory() as tmp:
            ledger, allocation = self._ledger_and_allocation(tmp, amount=1_000_000)
            broker = LedgerBudgetBroker(ledger)

            def failing_http(*args, **kwargs):
                raise RuntimeError("simulated transient failure")

            failing_transport = GeminiTransport(lambda: "secret-key", broker=broker, http=failing_http)
            context = make_context(ledger, allocation_id=allocation.allocation_id, attempt_id="scene0-member0-completion")
            with self.assertRaises(RuntimeError):
                run_author_turns(
                    failing_transport, [{"role": "user", "parts": [{"text": "start"}]}],
                    context=context, seed_for_turn=lambda turn: turn, max_output_tokens=10,
                )
            self.assertEqual(ledger.summary()["unresolved_requests"], 1)

            # The pinned pipeline's own retry: same context, same deterministic
            # attempt_id sequence, a fresh run_author_turns call from turn 0 --
            # this time against a working transport.
            working_transport = GeminiTransport(lambda: "secret-key", broker=broker,
                                                http=lambda *a, **k: gemini_payload(candidates=[{
                                                    "finishReason": "STOP",
                                                    "content": {"role": "model", "parts": [{"text": "done"}]},
                                                }]))
            result = run_author_turns(
                working_transport, [{"role": "user", "parts": [{"text": "start"}]}],
                context=context, seed_for_turn=lambda turn: turn, max_output_tokens=10,
            )
            self.assertEqual(result.text, "done")
            summary = ledger.summary()
            self.assertEqual(summary["unresolved_requests"], 1)  # the first failure, untouched
            self.assertGreater(summary["settled_microusd"], 0)   # the retry actually settled
            ledger.close()

    def test_a_restart_after_a_later_turn_settles_does_not_rebill_forever(self):
        # Independent design review (2026-09-22) found and reproduced a real
        # gap: the pipeline restarts a whole member from turn 0, not just
        # its failed turn. A member whose turn 0 already SETTLED gets turn
        # 0 genuinely re-sent and re-billed on every restart (real work,
        # not a cache-hit) -- unbounded before the retry-generation cap.
        # This must now succeed for a handful of restarts, then fail loud
        # rather than re-billing indefinitely.
        with tempfile.TemporaryDirectory() as tmp:
            ledger, allocation = self._ledger_and_allocation(tmp, amount=1_000_000)
            broker = LedgerBudgetBroker(ledger)
            context = make_context(ledger, allocation_id=allocation.allocation_id, attempt_id="member0-completion")

            # First attempt: turn 0 settles, turn 1 fails transiently.
            # Real distinct calls never share a provider responseId; each
            # simulated call below must mint a fresh one too, or the
            # ledger's OWN separate anti-replay UNIQUE(provider_response_id)
            # guard (correctly) rejects the repeat as a duplicate response.
            response_ids = iter(f"response-{i}" for i in range(1000))
            turn = {"n": 0}

            def flaky_http(*args, **kwargs):
                if turn["n"] == 0:
                    turn["n"] += 1
                    return gemini_payload(responseId=next(response_ids), candidates=[{
                        "finishReason": "STOP", "content": {"role": "model", "parts": [
                            {"functionCall": {"name": "move", "args": {}}},
                        ]},
                    }])
                raise RuntimeError("simulated transient failure on turn 1")

            flaky_transport = GeminiTransport(lambda: "secret-key", broker=broker, http=flaky_http)
            with self.assertRaises(RuntimeError):
                run_author_turns(
                    flaky_transport, [{"role": "user", "parts": [{"text": "start"}]}],
                    context=context, seed_for_turn=lambda t: t, max_output_tokens=10,
                    execute_tool=lambda call: {"ok": True},
                )
            self.assertEqual(ledger.summary()["settled_microusd"], cost_microdollars(5, 2 + 3))

            # The pipeline's restart: identical context, from turn 0 again,
            # repeated up to the cap. Each restart re-sends (and re-bills)
            # the already-completed turn 0, then fails again on turn 1.
            for _ in range(Ledger.MAX_ATTEMPT_RETRY_GENERATIONS):
                restart_turn = {"n": 0}

                def flaky_http_restart(*args, **kwargs):
                    if restart_turn["n"] == 0:
                        restart_turn["n"] += 1
                        return gemini_payload(responseId=next(response_ids), candidates=[{
                            "finishReason": "STOP", "content": {"role": "model", "parts": [
                                {"functionCall": {"name": "move", "args": {}}},
                            ]},
                        }])
                    raise RuntimeError("simulated transient failure on turn 1")

                restart_transport = GeminiTransport(lambda: "secret-key", broker=broker, http=flaky_http_restart)
                with self.assertRaises(RuntimeError):
                    run_author_turns(
                        restart_transport, [{"role": "user", "parts": [{"text": "start"}]}],
                        context=context, seed_for_turn=lambda t: t, max_output_tokens=10,
                        execute_tool=lambda call: {"ok": True},
                    )

            # One more restart beyond the cap must fail loud, not re-bill again.
            with self.assertRaises(AccountingHalt):
                run_author_turns(
                    GeminiTransport(lambda: "secret-key", broker=broker, http=lambda *a, **k: gemini_payload()),
                    [{"role": "user", "parts": [{"text": "start"}]}],
                    context=context, seed_for_turn=lambda t: t, max_output_tokens=10,
                    execute_tool=lambda call: {"ok": True},
                )

            summary = ledger.summary()
            # settled once per successful restart of turn 0 (1 original + MAX_ATTEMPT_RETRY_GENERATIONS)
            expected_settlements = 1 + Ledger.MAX_ATTEMPT_RETRY_GENERATIONS
            self.assertEqual(summary["settled_microusd"], expected_settlements * cost_microdollars(5, 2 + 3))
            self.assertEqual(summary["redundant_settled_microusd"],
                             (expected_settlements - 1) * cost_microdollars(5, 2 + 3))
            ledger.close()

    def test_a_real_leading_hyphen_provider_response_id_settles_through_the_full_stack(self):
        # End-to-end regression for the other live 2026-09-22 finding: a
        # real Gemini responseId that starts with "-" must settle through
        # the actual transport -> broker -> ledger path, not just at the
        # Ledger unit-test level.
        with tempfile.TemporaryDirectory() as tmp:
            ledger, allocation = self._ledger_and_allocation(tmp)
            broker = LedgerBudgetBroker(ledger)
            transport = GeminiTransport(lambda: "secret-key", broker=broker,
                                        http=lambda *a, **k: gemini_payload(responseId="-NWwasf4MsGlg8UP69rl8QU"))
            request = {"contents": [{"role": "user", "parts": [{"text": "hi"}]}], "store": False,
                      "generationConfig": {"temperature": 0.2, "maxOutputTokens": 10,
                          "candidateCount": 1, "seed": 1,
                          "thinkingConfig": {"thinkingLevel": "MEDIUM", "includeThoughts": False}}}
            context = make_context(ledger, allocation_id=allocation.allocation_id)
            result = transport.generate(request, context=context)
            self.assertEqual(result.text, "final answer")
            self.assertEqual(ledger.summary()["unresolved_requests"], 0)
            ledger.close()


if __name__ == "__main__":
    unittest.main()
