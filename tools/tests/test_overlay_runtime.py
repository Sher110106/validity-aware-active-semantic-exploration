from __future__ import annotations

import os
import unittest
from unittest import mock

from prospective_integration.overlay_runtime import LedgerContext, deterministic_seed, make_context


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


class ContextAndSeedTests(unittest.TestCase):
    def _context(self):
        return LedgerContext(ledger_path="/tmp/l", credential_path="/tmp/c", campaign_id="camp",
                             phase_id="engineering", allocation_id="alloc", run_id="run",
                             max_output_tokens=8192)

    def test_make_context_is_stable_per_scene_member_call(self):
        lc = self._context()
        a = make_context(lc, scene_index=0, ensemble_index=1, call="completion")
        b = make_context(lc, scene_index=0, ensemble_index=1, call="completion")
        c = make_context(lc, scene_index=0, ensemble_index=2, call="completion")
        self.assertEqual(a, b)
        self.assertNotEqual(a.member_id, c.member_id)
        a.validate()

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


if __name__ == "__main__":
    unittest.main()
