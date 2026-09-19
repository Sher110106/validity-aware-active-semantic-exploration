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


if __name__ == "__main__":
    unittest.main()
