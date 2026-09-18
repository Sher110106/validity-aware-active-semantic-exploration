import json
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path

from gemini_campaign.adapter import Broker, TransportFailure, parse_response
from gemini_campaign.config import (
    MODEL_ID,
    NORMAL_CEILING_MICROUSD,
    OUTPUT_LIMIT,
    THINKING_LEVEL,
    cost_microdollars,
)
from gemini_campaign.credentials import load_credential
from gemini_campaign.errors import AccountingHalt, CredentialError, LedgerError, PolicyError
from gemini_campaign.events import append_event
from gemini_campaign.estimator import NativeCount, conservative_input_bound, request_hash
from gemini_campaign.ledger import Ledger, RecoveryControl

META = dict(campaign_id="campaign", phase_id="engineering", run_id="run", stage_id="stage", member_id="member", tool_turn_id="turn")


class LedgerTests(unittest.TestCase):
    def make_ledger(self, *, recovery=None):
        return Ledger(tempfile.mktemp(), recovery_control=recovery)

    def allocation(self, ledger, phase="engineering", amount=18_000_000):
        return ledger.allocate(campaign_id="campaign", phase_id=phase, amount_microusd=amount)

    def reserve(self, ledger, allocation, attempt="attempt", input_bound=1, max_output=10, **extra):
        return ledger.reserve(
            allocation_id=allocation.allocation_id, attempt_id=attempt,
            model=MODEL_ID, thinking_level=THINKING_LEVEL,
            input_bound=input_bound, max_output_tokens=max_output,
            **META, **extra,
        )

    def test_authority_caps_and_explicit_recovery_control(self):
        with self.assertRaises(LedgerError):
            Ledger(tempfile.mktemp(), recovery_control=RecoveryControl(True, "recovery", 10_000_001, "repair", 2_000_000_000))
        ledger = self.make_ledger()
        with self.assertRaises(AccountingHalt):
            ledger.allocate(campaign_id="campaign", phase_id="recovery", amount_microusd=1)
        control = RecoveryControl(True, "recovery", 10_000_000, "repair", 2_000_000_000)
        ledger = self.make_ledger(recovery=control)
        self.assertEqual(ledger.ceiling, 190_000_000)
        self.assertEqual(ledger.allocate(campaign_id="campaign", phase_id="recovery", amount_microusd=10_000_000).amount_microusd, 10_000_000)

    def test_phase_caps_and_allocation_drawdown(self):
        ledger = self.make_ledger()
        allocation = self.allocation(ledger, amount=1000)
        first = self.reserve(ledger, allocation, attempt="first", input_bound=1, max_output=1)
        self.assertGreater(first.reservation_microusd, 0)
        with self.assertRaises(AccountingHalt):
            self.reserve(ledger, allocation, attempt="second", input_bound=1_000_000, max_output=1)
        with self.assertRaises(AccountingHalt):
            ledger.allocate(campaign_id="campaign", phase_id="probe", amount_microusd=2_000_001)

    def test_concurrent_phase_allocations_collect_all_thread_errors(self):
        ledger_path = tempfile.mktemp()
        results, errors = [], []

        def worker(index):
            try:
                ledger = Ledger(ledger_path)
                results.append(ledger.allocate(campaign_id="campaign", phase_id="probe", amount_microusd=600_000))
                ledger.close()
            except Exception as error:
                errors.append(error)

        threads = [threading.Thread(target=worker, args=(index,)) for index in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(errors) + len(results), 8)
        self.assertLessEqual(sum(item.amount_microusd for item in results), 2_000_000)
        self.assertLessEqual(len(results), 3)

    def test_concurrent_request_reservations_draw_down_one_allocation(self):
        ledger_path = tempfile.mktemp()
        setup = Ledger(ledger_path)
        allocation = setup.allocate(campaign_id="campaign", phase_id="probe", amount_microusd=2_000_000)
        setup.close()
        results, errors = [], []

        def worker(index):
            try:
                ledger = Ledger(ledger_path)
                results.append(ledger.reserve(
                    allocation_id=allocation.allocation_id, campaign_id="campaign", phase_id="probe",
                    run_id="run", stage_id="stage", member_id="member", tool_turn_id="turn",
                    attempt_id=f"attempt-{index}", model=MODEL_ID, thinking_level=THINKING_LEVEL,
                    max_output_tokens=65_536, input_bound=1,
                ))
                ledger.close()
            except Exception as error:
                errors.append(error)

        threads = [threading.Thread(target=worker, args=(index,)) for index in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(results) + len(errors), 12)
        check = Ledger(ledger_path)
        self.assertLessEqual(check.summary()["reserved_microusd"], 2_000_000)
        check.close()

    def test_identifiers_attempt_uniqueness_and_retry_provenance(self):
        ledger = self.make_ledger()
        allocation = self.allocation(ledger, amount=10_000)
        first = self.reserve(ledger, allocation, attempt="one")
        with self.assertRaises(AccountingHalt):
            self.reserve(ledger, allocation, attempt="one")
        retry = self.reserve(ledger, allocation, attempt="two", retry_of=first.request_id)
        self.assertNotEqual(first.request_id, retry.request_id)
        with self.assertRaises(AccountingHalt):
            self.reserve(ledger, allocation, attempt="three", retry_of="missing")

    def test_dispatch_receipt_and_settlement_state(self):
        ledger = self.make_ledger()
        allocation = self.allocation(ledger, amount=10_000)
        reservation = self.reserve(ledger, allocation)
        with self.assertRaises(AccountingHalt):
            ledger.settle(reservation.request_id, model=MODEL_ID, service_tier="standard", input_tokens=1,
                          candidate_tokens=1, thought_tokens=0, cached_tokens=0, total_tokens=2,
                          provider_response_id="response", finish_reason="STOP")
        dispatch_id = ledger.mark_dispatched(reservation.request_id)
        self.assertTrue(dispatch_id)
        ledger.settle(reservation.request_id, model=MODEL_ID, service_tier="standard", input_tokens=1,
                      candidate_tokens=1, thought_tokens=1, cached_tokens=0, total_tokens=3,
                      provider_response_id="response", finish_reason="STOP")
        # Identical full settlement is idempotent; changing usage is not.
        ledger.settle(reservation.request_id, model=MODEL_ID, service_tier="standard", input_tokens=1,
                      candidate_tokens=1, thought_tokens=1, cached_tokens=0, total_tokens=3,
                      provider_response_id="response", finish_reason="STOP")
        with self.assertRaises(AccountingHalt):
            ledger.settle(reservation.request_id, model=MODEL_ID, service_tier="standard", input_tokens=2,
                          candidate_tokens=1, thought_tokens=1, cached_tokens=0, total_tokens=4,
                          provider_response_id="response", finish_reason="STOP")

    def test_usage_and_budget_boundaries_fail_closed(self):
        ledger = self.make_ledger()
        allocation = self.allocation(ledger, amount=10_000)
        reservation = self.reserve(ledger, allocation, max_output=2)
        ledger.mark_dispatched(reservation.request_id)
        cases = [
            dict(service_tier="premium"),
            dict(model="wrong"),
            dict(candidate_tokens=2, thought_tokens=1, total_tokens=4),
            dict(cached_tokens=2, total_tokens=2),
            dict(pricing_version="changed"),
        ]
        for index, changes in enumerate(cases):
            fields = dict(model=MODEL_ID, service_tier="standard", input_tokens=1, candidate_tokens=1,
                          thought_tokens=0, cached_tokens=0, total_tokens=2, provider_response_id=f"r{index}", finish_reason="STOP")
            fields.update(changes)
            with self.assertRaises(AccountingHalt):
                ledger.settle(reservation.request_id, **fields)
        self.assertEqual(ledger.summary()["unresolved_requests"], 1)

    def test_allocate_accepts_idempotent_caller_supplied_id(self):
        ledger = self.make_ledger()
        allocation = ledger.allocate(campaign_id="campaign", phase_id="engineering",
                                     amount_microusd=1000, allocation_id="block-1")
        self.assertEqual(allocation.allocation_id, "block-1")
        with self.assertRaises(AccountingHalt):
            ledger.allocate(campaign_id="campaign", phase_id="engineering",
                            amount_microusd=1000, allocation_id="block-1")

    def test_corrupt_or_unsupported_db_fails_closed(self):
        path = tempfile.mktemp()
        Path(path).write_text("not sqlite")
        with self.assertRaises(LedgerError):
            Ledger(path)


class EnvelopeAndAdapterTests(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger(tempfile.mktemp())
        self.allocation = self.ledger.allocate(campaign_id="campaign", phase_id="engineering", amount_microusd=1_000_000)
        self.metadata = dict(campaign_id="campaign", phase_id="engineering", run_id="run", stage_id="stage", member_id="member", tool_turn_id="turn", attempt_id="adapter")

    def response(self, **changes):
        value = {
            "model": MODEL_ID, "model_version": MODEL_ID, "response_id": "provider-response",
            "service_tier": "standard", "finish_reason": "STOP", "text": "ok",
            "usage": {"prompt_tokens": 10, "candidate_tokens": 2, "thought_tokens": 3, "cached_tokens": 0, "total_tokens": 15},
        }
        value.update(changes)
        return value

    def test_envelope_bound_covers_unicode_tools_and_images(self):
        envelope = {"contents": [{"text": "λ" * 100}], "tools": [{"name": "draw", "schema": {"x": "y"}}], "inline_image": "data-descriptor"}
        self.assertEqual(conservative_input_bound(envelope), len(json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()))

    def test_native_count_is_tied_to_exact_unmutated_request(self):
        envelope = {"contents": [{"text": "hello"}]}
        count = NativeCount(4, request_hash(envelope))
        mutated = {"contents": [{"text": "changed"}]}
        with self.assertRaises(PolicyError):
            Broker(self.ledger, lambda **_: self.response()).request(envelope=mutated, native_count=count, allocation_id=self.allocation.allocation_id, metadata=self.metadata, max_output_tokens=10)

    def test_context_overflow_and_explicit_medium_transport_metadata(self):
        huge = {"text": "x" * 1_048_000}
        with self.assertRaises(PolicyError):
            Broker(self.ledger, lambda **_: self.response()).request(envelope=huge, allocation_id=self.allocation.allocation_id, metadata=self.metadata, max_output_tokens=65_536)
        seen = {}
        def transport(**kwargs):
            seen.update(kwargs["metadata"])
            return self.response()
        result = Broker(self.ledger, transport).request(envelope={"text": "hello"}, allocation_id=self.allocation.allocation_id, metadata={**self.metadata, "attempt_id": "transport"}, max_output_tokens=10)
        self.assertEqual(result.text, "ok")
        self.assertEqual(seen["thinking_level"], THINKING_LEVEL)
        self.assertEqual(seen["max_output_tokens"], 10)

    def test_transport_failures_keep_full_reservation_and_do_not_leak(self):
        def fail(**_):
            raise RuntimeError("secret transport detail")
        with self.assertRaises(TransportFailure) as error:
            Broker(self.ledger, fail).request(envelope={"text": "hello"}, allocation_id=self.allocation.allocation_id, metadata=self.metadata, max_output_tokens=10)
        self.assertNotIn("secret", str(error.exception))
        self.assertEqual(self.ledger.summary()["unresolved_requests"], 1)

    def test_response_parser_rejects_malformed_usage_and_model(self):
        with self.assertRaises(AccountingHalt):
            parse_response(self.response(model="other"))
        with self.assertRaises(AccountingHalt):
            parse_response(self.response(usage={"prompt_tokens": 1}))


class CredentialAndEventTests(unittest.TestCase):
    def test_credential_modes_size_symlink_and_forbidden_root(self):
        root = Path(tempfile.mkdtemp())
        outside = Path(tempfile.mkdtemp()) / "credential"
        outside.write_text("fake-AQ.not-a-secret")
        with self.assertRaises(CredentialError):
            load_credential(str(outside), forbidden_roots=(str(outside.parent),))
        os.chmod(outside, 0o644)
        with self.assertRaises(CredentialError):
            load_credential(str(outside), forbidden_roots=())
        os.chmod(outside, 0o400)
        self.assertEqual(load_credential(str(outside), forbidden_roots=()), "fake-AQ.not-a-secret")
        os.chmod(outside, 0o600)
        self.assertEqual(load_credential(str(outside), forbidden_roots=()), "fake-AQ.not-a-secret")
        if os.geteuid() == 0:
            os.chown(outside, 1, -1)
            with self.assertRaises(CredentialError):
                load_credential(str(outside), forbidden_roots=())
            os.chown(outside, os.getuid(), -1)
        link = root / "link"
        link.symlink_to(outside)
        with self.assertRaises(CredentialError):
            load_credential(str(link), forbidden_roots=())
        oversized = root / "oversized"
        oversized.write_bytes(b"x" * 4097)
        os.chmod(oversized, 0o600)
        with self.assertRaises(CredentialError):
            load_credential(str(oversized), forbidden_roots=())
        self.assertNotIn(str(outside), "credential file is unavailable")

    def test_event_chain_is_sanitized_and_sequenced(self):
        path = tempfile.mktemp()
        append_event(path, {"event": "dispatch", "request_id": "request", "authorization": "fake-AQ.not-a-secret", "error_code": "timeout"})
        append_event(path, {"event": "timeout", "request_id": "request", "error_code": "timeout"})
        records = [json.loads(line) for line in Path(path).read_text().splitlines()]
        self.assertEqual([record["sequence"] for record in records], [1, 2])
        self.assertNotIn("authorization", records[0])
        self.assertEqual(records[1]["previous_hash"], records[0]["hash"])
        with self.assertRaises(ValueError):
            append_event(path, {"event": "bad", "request_id": "https://secret.invalid"})


if __name__ == "__main__":
    unittest.main()
