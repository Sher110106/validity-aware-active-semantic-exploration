from __future__ import annotations

import os
import unittest
from unittest import mock

from prospective_integration.overlay_runtime import LedgerContext, build_input_bound_fn, deterministic_seed, make_context
from prospective_runtime.transport import conservative_input_bound


class LedgerContextFromEnvTests(unittest.TestCase):
    def test_returns_none_when_not_configured_at_all(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(LedgerContext.from_env())

    def test_raises_on_partial_configuration_rather_than_falling_back_unaccounted(self):
        with mock.patch.dict(os.environ, {"ASP_PROSPECTIVE_LEDGER_PATH": "/tmp/ledger.sqlite"}, clear=True):
            with self.assertRaises(RuntimeError):
                LedgerContext.from_env()

    def test_full_configuration_is_read_correctly(self):
        env = {
            "ASP_PROSPECTIVE_LEDGER_PATH": "/tmp/ledger.sqlite",
            "ASP_PROSPECTIVE_CREDENTIAL_PATH": "/tmp/cred",
            "ASP_PROSPECTIVE_CAMPAIGN_ID": "paired_v5",
            "ASP_PROSPECTIVE_ALLOCATION_ID": "block-1",
            "ASP_PROSPECTIVE_RUN_ID": "run-1",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            context = LedgerContext.from_env()
        self.assertEqual(context.phase_id, "engineering")
        self.assertEqual(context.max_output_tokens, 8192)
        self.assertEqual(context.campaign_id, "paired_v5")


class BuildInputBoundFnTests(unittest.TestCase):
    """Regression context: the byte bound overshot the real countTokens
    count by 440x on a real request (2026-09-21 pilot). This is opt-in via
    ASP_PROSPECTIVE_NATIVE_COUNT=1 so no existing deployment changes
    behavior until explicitly turned on."""

    def _context(self, credential_path="/tmp/cred"):
        return LedgerContext(ledger_path="/tmp/l", credential_path=credential_path, campaign_id="camp",
                             phase_id="engineering", allocation_id="alloc", run_id="run",
                             max_output_tokens=8192)

    def test_returns_the_byte_bound_directly_when_not_enabled(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            bound_fn = build_input_bound_fn(self._context())
        self.assertIs(bound_fn, conservative_input_bound)

    def test_an_unrecognized_flag_value_also_stays_on_the_byte_bound(self):
        with mock.patch.dict(os.environ, {"ASP_PROSPECTIVE_NATIVE_COUNT": "true"}, clear=True):
            bound_fn = build_input_bound_fn(self._context())
        self.assertIs(bound_fn, conservative_input_bound)

    def test_enabled_flag_wires_a_real_countTokens_backed_function(self):
        import tempfile
        fd, path = tempfile.mkstemp()
        try:
            os.write(fd, b"AQ.fake-credential-value")
            os.close(fd)
            os.chmod(path, 0o600)
            with mock.patch.dict(os.environ, {"ASP_PROSPECTIVE_NATIVE_COUNT": "1"}, clear=True):
                with mock.patch("prospective_integration.overlay_runtime.native_input_bound") as fake:
                    fake.return_value = 42
                    bound_fn = build_input_bound_fn(self._context(credential_path=path))
                    request = {"contents": [{"role": "user", "parts": [{"text": "hi"}]}]}
                    result = bound_fn(request)
            self.assertEqual(result, 42)
            fake.assert_called_once()
            self.assertEqual(fake.call_args.args[0], request)
            self.assertEqual(fake.call_args.kwargs["credential_loader"](), "AQ.fake-credential-value")
            self.assertIsNone(fake.call_args.kwargs["on_count"])  # no ASP_PROSPECTIVE_COUNT_LOG set
        finally:
            os.path.exists(path) and os.remove(path)

    def test_enabled_flag_with_a_log_path_wires_a_real_on_count_hook(self):
        import tempfile
        fd, cred_path = tempfile.mkstemp()
        with tempfile.TemporaryDirectory() as d:
            log_path = os.path.join(d, "counts.jsonl")
            try:
                os.write(fd, b"AQ.fake-credential-value")
                os.close(fd)
                os.chmod(cred_path, 0o600)
                env = {"ASP_PROSPECTIVE_NATIVE_COUNT": "1", "ASP_PROSPECTIVE_COUNT_LOG": log_path}
                with mock.patch.dict(os.environ, env, clear=True):
                    with mock.patch("prospective_integration.overlay_runtime.native_input_bound") as fake:
                        fake.return_value = 42
                        bound_fn = build_input_bound_fn(self._context(credential_path=cred_path))
                        bound_fn({"contents": []})
                self.assertIsNotNone(fake.call_args.kwargs["on_count"])
                fake.call_args.kwargs["on_count"](real_count=5, byte_bound=100, used=10, error=None)
                with open(log_path) as f:
                    self.assertIn('"real_count": 5', f.read())
            finally:
                os.path.exists(cred_path) and os.remove(cred_path)


class ContextAndSeedTests(unittest.TestCase):
    def _context(self):
        return LedgerContext(ledger_path="/tmp/l", credential_path="/tmp/c", campaign_id="camp",
                             phase_id="engineering", allocation_id="alloc", run_id="run",
                             max_output_tokens=8192)

    def test_make_context_is_stable_per_scene_member_call(self):
        lc = self._context()
        a = make_context(lc, scene_index=0, ensemble_index=1, call="completion", pipeline_stage="0")
        b = make_context(lc, scene_index=0, ensemble_index=1, call="completion", pipeline_stage="0")
        c = make_context(lc, scene_index=0, ensemble_index=2, call="completion", pipeline_stage="0")
        self.assertEqual(a, b)
        self.assertNotEqual(a.member_id, c.member_id)
        a.validate()

    def test_make_context_gives_every_pipeline_stage_a_distinct_attempt_id(self):
        # Regression: confirmed live, 2026-09-22 real scientific campaign --
        # omitting the real stage number let every stage beyond the first
        # reconstruct scene0-member0-completion identically to stage 0,
        # since scene_index/ensemble_index/call alone repeat every stage.
        # That silently exhausted resolve_attempt_id's retry-generation
        # cap on ordinary progress, not real failures, halting every
        # member after only 4 real stages.
        lc = self._context()
        stage0 = make_context(lc, scene_index=0, ensemble_index=1, call="completion", pipeline_stage="0")
        stage1 = make_context(lc, scene_index=0, ensemble_index=1, call="completion", pipeline_stage="1")
        stage12 = make_context(lc, scene_index=0, ensemble_index=1, call="completion", pipeline_stage="12")
        self.assertNotEqual(stage0.attempt_id, stage1.attempt_id)
        self.assertNotEqual(stage1.attempt_id, stage12.attempt_id)
        self.assertNotEqual(stage0.attempt_id, stage12.attempt_id)
        stage0.validate()
        stage1.validate()
        stage12.validate()

    def test_deterministic_seed_is_pure_and_scene_member_turn_sensitive(self):
        lc = self._context()
        first = deterministic_seed(lc, 0, 1, 0, base_seed=42)
        second = deterministic_seed(lc, 0, 1, 0, base_seed=42)
        third = deterministic_seed(lc, 0, 1, 1, base_seed=42)
        fourth = deterministic_seed(lc, 0, 2, 0, base_seed=42)
        self.assertEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertNotEqual(first, fourth)
        self.assertTrue(0 <= first <= 2_147_483_647)

    def test_deterministic_seed_masks_a_known_overflowing_hash(self):
        # Pinned, not sampled: with lc.run_id="run", (scene_index=0,
        # ensemble_index=0, turn=0, base_seed=42), sha256(...)[:4] as an
        # unsigned 32-bit big-endian int is 2321322531 (0x8a5c9223), which
        # exceeds the API's signed 31-bit max (2**31-1 = 2147483647) --
        # exactly the class of value that broke live workers before the
        # mask was added. A random draw only overflows about half the
        # time, so an unpinned test proves nothing; this input is chosen
        # specifically because its unmasked hash overflows.
        lc = self._context()
        unmasked = 2_321_322_531
        assert unmasked > 2_147_483_647  # guards the fixture itself against drift
        value = deterministic_seed(lc, 0, 0, 0, base_seed=42)
        self.assertEqual(value, unmasked & 0x7FFFFFFF)
        self.assertEqual(value, 173_838_883)
        self.assertTrue(0 <= value <= 2_147_483_647)

    def test_deterministic_seed_stays_in_the_signed_31_bit_range_across_many_samples(self):
        # Regression: int.from_bytes(4 bytes, "big") alone gives an unsigned
        # 32-bit range, exceeding the API's signed 31-bit max about half the
        # time -- confirmed live (capability pilot, 2026-09-21), where ~half
        # of 8 concurrent workers' seeds were rejected before any
        # reservation. A single sample has ~50% odds of missing this by
        # chance (as the test above did); sample many turn/index/seed
        # combinations to actually exercise both halves of the hash output.
        lc = self._context()
        for scene_index in range(4):
            for ensemble_index in range(4):
                for turn in range(4):
                    for base_seed in (0, 1, 42, 999999):
                        value = deterministic_seed(lc, scene_index, ensemble_index, turn, base_seed=base_seed)
                        self.assertTrue(0 <= value <= 2_147_483_647, value)


if __name__ == "__main__":
    unittest.main()
