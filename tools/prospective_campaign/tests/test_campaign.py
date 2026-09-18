import hashlib
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

from prospective_campaign.budget import FakeGeminiLedger
from prospective_campaign.claims import claim_gate
from prospective_campaign.contract import BASELINE, EXPERIMENTAL, ContractError
from prospective_campaign.control import (Control, EventLog, Telemetry, atomic_json,
                                           parse_hash_file, secure_attempt, validate_artifacts,
                                           validate_telemetry)
from prospective_campaign.manifest import build_manifest
from prospective_campaign.queue import (Pair, PairAdmissionController, allocate_block_costs,
                                        deterministic_queue, validate_block)
from prospective_campaign.scope import decide_scope
from prospective_campaign.state import CampaignSupervisor, Phase, PairState, load_state, save_state


class Health:
    def healthy(self): return True


class TestCampaign(unittest.TestCase):
    def test_order_execution_and_policy_order(self):
        queue = deterministic_queue()
        self.assertEqual([(x.seed, x.scene, x.order) for x in queue], [
            (42, '00069', 'O→E'), (42, '00573', 'E→O'), (42, '00853', 'O→E'),
            (43, '00573', 'E→O'), (43, '00853', 'O→E'), (43, '00069', 'E→O'),
            (44, '00853', 'O→E'), (44, '00069', 'E→O'), (44, '00573', 'O→E')])
        self.assertEqual(queue[1].policies, (EXPERIMENTAL, BASELINE))
        with self.assertRaises(ContractError): Pair('00069', 42, 'E→O', 120)

    def test_block_is_exact_and_transactional(self):
        pairs = deterministic_queue(25)[:3]
        validate_block(pairs, 42, 25)
        with self.assertRaises(ContractError): validate_block(pairs[:2], 42, 25)
        ledger = FakeGeminiLedger(190_000_000)
        admission = PairAdmissionController(ledger, Health(), worst_block_micro_usd=64_820_000).admit_block(pairs, allocation_id='a1')
        self.assertTrue(admission.admitted)
        self.assertFalse(ledger.reserve_block('a1', 1))
        self.assertTrue(ledger.draw('a1', 'req1', 1_000_000))
        with self.assertRaises(RuntimeError): ledger.release('a1')

    def test_integer_scope_and_sequential_decrement(self):
        decision = decide_scope(pilot_cost_micro_usd=1_540_000, available_after_pilot_micro_usd=198_460_000,
                                candidate_block_costs_micro_usd=(117_620_000, 117_620_000), selected_horizon_m=50,
                                unresolved_micro_usd=10_000_000)
        self.assertEqual(decision.admitted_block_costs_micro_usd, (117_620_000,))
        self.assertIsInstance(decision.admitted_block_costs_micro_usd[0], int)
        self.assertEqual(allocate_block_costs(200, (100, 101)), (100,))

    def test_missing_telemetry_fails_closed(self):
        with self.assertRaises(ContractError): validate_telemetry(Telemetry(None, True, 100, 1, 1, True))

    def test_secure_paths_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secure_attempt(root, 'paired_v5', '00069', 42, BASELINE, 1)
            with self.assertRaises(ContractError): secure_attempt(root, '..', '00069', 42, BASELINE, 1)
            link = root / 'runs' / 'prospective_gemini' / 'paired_v5' / '00573'
            link.parent.mkdir(parents=True, exist_ok=True); link.symlink_to(root)
            with self.assertRaises(ContractError): secure_attempt(root, 'paired_v5', '00573', 42, BASELINE, 1)

    def test_hash_parser_rejects_malformed_traversal_duplicate_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); hashes = root / 'ARTIFACTS.sha256'; digest = 'a' * 64
            hashes.write_text(f'{digest}  good.json\n')
            self.assertEqual(parse_hash_file(hashes, ('good.json',))['good.json'], digest)
            for text in (f'{digest} bad.json\n', f'{digest}  ../bad.json\n', f'{digest}  good.json\n{digest}  good.json\n'):
                hashes.write_text(text)
                with self.assertRaises(ContractError): parse_hash_file(hashes, ('good.json',))
            target = root / 'real'; target.write_text('x'); hashes.unlink(); hashes.symlink_to(target)
            with self.assertRaises(ContractError): parse_hash_file(hashes, ('good.json',))

    def test_artifact_requires_every_hash_and_regular_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); artifact = run / 'trajectory.json'; artifact.write_text('ok')
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            (run / 'ARTIFACTS.sha256').write_text(f'{digest}  trajectory.json\n')
            self.assertTrue(validate_artifacts(run, ('trajectory.json',))[0])
            (run / 'ARTIFACTS.sha256').write_text('0' * 64 + '  trajectory.json\n')
            self.assertFalse(validate_artifacts(run, ('trajectory.json',))[0])

    def test_crash_reload_and_wrong_start_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'status.json'
            state = PairState(2, 'campaign', 'block', 'pair', 'run', 1, 'alloc', 'a'*64, 'b'*64,
                              (BASELINE, EXPERIMENTAL), (), 'reserved', 1)
            save_state(path, state); self.assertEqual(load_state(path), state)
            raw = json.loads(path.read_text()); raw['start_state_hash'] = 'c' * 64; path.write_text(json.dumps(raw))
            self.assertNotEqual(load_state(path).start_state_hash, state.start_state_hash)
            raw['attempt'] = 3; path.write_text(json.dumps(raw))
            with self.assertRaises(ContractError): load_state(path)

    def test_manifest_allowlist_and_leakage_rejection(self):
        kwargs = dict(source_tag='authoritative-v5-2026-09-17', author_commit='a'*64, container_digest='b'*64,
                      environment_tag='container-ubuntu20', hashes={x: 'c'*64 for x in ('scene','reference','navmesh','calibrator','prompt','policy')},
                      model='gemini-3.8-flash', thinking_level='medium', policy=EXPERIMENTAL, controller_mode='unattended',
                      audit_mode='strict', scene='00069', seed=42, start_state_hash='d'*64, horizon_m=25,
                      budget_ledger_id='ledger', allocation_id='alloc')
        manifest = build_manifest(**kwargs); self.assertNotIn('environment', manifest)
        kwargs['environment_tag'] = 'credential=secret'
        with self.assertRaises(ContractError): build_manifest(**kwargs)
        kwargs['environment_tag'] = 'safe'; kwargs['model'] = 'other'
        with self.assertRaises(ContractError): build_manifest(**kwargs)

    def test_claim_metrics_are_finite_and_policy_specific(self):
        args = dict(complete_pairs=3, complete_block=True, invalid_hypothesis_ok=True, detour_receipt_valid=True,
                    fp_detour_reduction=.2, baseline_detour=1, f1_loss=.01, ged_increase=.01)
        self.assertEqual(claim_gate(experimental_policy=EXPERIMENTAL, **args)['status'], 'established')
        args['fp_detour_reduction'] = math.nan
        self.assertNotEqual(claim_gate(experimental_policy=EXPERIMENTAL, **args)['status'], 'established')
        args['fp_detour_reduction'] = .2
        self.assertEqual(claim_gate(experimental_policy='beta_r', **args)['status'], 'not_established')

    def test_certify_member_is_idempotent_and_does_not_duplicate_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / 'run'; run.mkdir()
            artifact = run / 'trajectory.json'; artifact.write_text('ok')
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            (run / 'ARTIFACTS.sha256').write_text(f'{digest}  trajectory.json\n')
            status_path = root / 'status.json'
            events = EventLog(root / 'events.jsonl')
            events.append('reserve', sequence=0, run_id='run', allocation_id='alloc')
            state = PairState(2, 'campaign', 'block', 'pair', 'run', 1, 'alloc', 'a' * 64, 'b' * 64,
                              (BASELINE, EXPERIMENTAL), (), Phase.RUNNING.value, 0)
            save_state(status_path, state)
            supervisor = CampaignSupervisor(status_path, events, runner=None)
            self.assertTrue(supervisor.certify_member(run, ('trajectory.json',), BASELINE))
            first_sequence = supervisor.state.transition_sequence
            first_members = supervisor.state.completed_members
            # Re-certifying the same member (e.g. a retry after a crash) must be a
            # no-op: no new transition, no duplicate "complete" event.
            self.assertTrue(supervisor.certify_member(run, ('trajectory.json',), BASELINE))
            self.assertEqual(supervisor.state.transition_sequence, first_sequence)
            self.assertEqual(supervisor.state.completed_members, first_members)
            event_lines = (root / 'events.jsonl').read_text().splitlines()
            self.assertEqual(len(event_lines), 2)  # reserve + one complete, no duplicate

    def test_certify_member_reaches_complete_for_both_ordered_members(self):
        # Regression: certify_member used to gate on phase == RUNNING, but the
        # first certification moves the pair to RESERVED -- which meant the
        # second, different member could never be certified and a pair could
        # never reach COMPLETE.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status_path = root / 'status.json'
            events = EventLog(root / 'events.jsonl')
            events.append('reserve', sequence=0, run_id='run', allocation_id='alloc')
            state = PairState(2, 'campaign', 'block', 'pair', 'run', 1, 'alloc', 'a' * 64, 'b' * 64,
                              (BASELINE, EXPERIMENTAL), (), Phase.RUNNING.value, 0)
            save_state(status_path, state)
            supervisor = CampaignSupervisor(status_path, events, runner=None)
            for policy in (BASELINE, EXPERIMENTAL):
                run = root / policy
                artifact = run / 'trajectory.json'; run.mkdir(); artifact.write_text('ok')
                digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
                (run / 'ARTIFACTS.sha256').write_text(f'{digest}  trajectory.json\n')
                self.assertTrue(supervisor.certify_member(run, ('trajectory.json',), policy))
            self.assertEqual(supervisor.state.phase, Phase.COMPLETE.value)
            self.assertEqual(set(supervisor.state.completed_members), {BASELINE, EXPERIMENTAL})

    def test_event_allowlist_and_chaining(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = EventLog(Path(tmp) / 'events.jsonl'); log.append('reserve', sequence=0, run_id='run', allocation_id='alloc')
            log.append('launch_intent', sequence=1, run_id='run', allocation_id='alloc')
            with self.assertRaises(ContractError): log.append('leak', sequence=2, run_id='run', allocation_id='alloc')


if __name__ == '__main__': unittest.main()
