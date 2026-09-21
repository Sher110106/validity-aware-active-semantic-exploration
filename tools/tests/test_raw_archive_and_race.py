from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from prospective_integration.count_log import CountLog
from prospective_integration.race_instrumentation import RaceInstrumentation
from prospective_integration.raw_archive import RawResponseArchive
from prospective_integration import overlay_runtime


class RawResponseArchiveTests(unittest.TestCase):
    def test_appends_request_and_response_with_context_identifiers(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "archive.jsonl"
            archive = RawResponseArchive(path)
            context = mock.Mock(run_id="run", stage_id="stage", member_id="member",
                               turn_id="turn", attempt_id="attempt")
            archive(request={"contents": []}, payload={"candidates": []}, context=context)
            lines = path.read_text().splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["run_id"], "run")
            self.assertEqual(record["request"], {"contents": []})
            self.assertEqual(record["response"], {"candidates": []})

    def test_refuses_symlink_path(self):
        with tempfile.TemporaryDirectory() as d:
            real = Path(d) / "real.jsonl"
            real.write_text("")
            link = Path(d) / "link.jsonl"
            link.symlink_to(real)
            with self.assertRaises(ValueError):
                RawResponseArchive(link)

    def test_concurrent_appends_from_multiple_threads_dont_interleave(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "archive.jsonl"
            archive = RawResponseArchive(path)
            context = mock.Mock(run_id="run", stage_id="s", member_id="m", turn_id="t", attempt_id="a")

            def write_many(n):
                for i in range(20):
                    archive(request={"i": n, "j": i}, payload={"ok": True}, context=context)

            threads = [threading.Thread(target=write_many, args=(n,)) for n in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            lines = path.read_text().splitlines()
            self.assertEqual(len(lines), 100)
            for line in lines:
                json.loads(line)  # every line must be independently valid JSON


class RaceInstrumentationTests(unittest.TestCase):
    def test_records_scene_ensemble_and_result_path(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "race.jsonl"
            instrumentation = RaceInstrumentation(path)
            instrumentation.record_member_finished(scene_index=0, ensemble_index=2, graph_id=2,
                                                    result_path="/tmp/graph2.yaml")
            instrumentation.record_member_finished(scene_index=1, ensemble_index=0, graph_id=4,
                                                    result_path=None)
            records = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(records[0]["scene_index"], 0)
            self.assertEqual(records[0]["result_path"], "/tmp/graph2.yaml")
            self.assertIsNone(records[1]["result_path"])  # a dropped member is recorded too

    def test_refuses_symlink_path(self):
        with tempfile.TemporaryDirectory() as d:
            real = Path(d) / "real.jsonl"
            real.write_text("")
            link = Path(d) / "link.jsonl"
            link.symlink_to(real)
            with self.assertRaises(ValueError):
                RaceInstrumentation(link)


class CountLogTests(unittest.TestCase):
    def test_records_real_count_byte_bound_used_and_no_error_on_success(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "counts.jsonl"
            log = CountLog(path)
            log.record(real_count=100, byte_bound=4_000_000, used=356, error=None)
            record = json.loads(path.read_text().splitlines()[0])
            self.assertEqual(record["real_count"], 100)
            self.assertEqual(record["byte_bound"], 4_000_000)
            self.assertEqual(record["used"], 356)
            self.assertFalse(record["fell_back"])
            self.assertIsNone(record["error_type"])

    def test_records_the_exception_type_and_message_on_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "counts.jsonl"
            log = CountLog(path)
            log.record(real_count=None, byte_bound=4_000_000, used=4_000_000,
                      error=TimeoutError("no network"))
            record = json.loads(path.read_text().splitlines()[0])
            self.assertIsNone(record["real_count"])
            self.assertTrue(record["fell_back"])
            self.assertEqual(record["error_type"], "TimeoutError")
            self.assertEqual(record["error_message"], "no network")

    def test_refuses_symlink_path(self):
        with tempfile.TemporaryDirectory() as d:
            real = Path(d) / "real.jsonl"
            real.write_text("")
            link = Path(d) / "link.jsonl"
            link.symlink_to(real)
            with self.assertRaises(ValueError):
                CountLog(link)


class OverlayRuntimeWiringTests(unittest.TestCase):
    def test_record_race_instrumentation_is_a_noop_when_unconfigured(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            overlay_runtime.record_race_instrumentation(
                scene_index=0, ensemble_index=0, graph_id=0, result_path=None)  # must not raise

    def test_record_race_instrumentation_writes_when_configured(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "race.jsonl"
            with mock.patch.dict("os.environ", {"ASP_PROSPECTIVE_RACE_LOG": str(path)}, clear=True):
                overlay_runtime.record_race_instrumentation(
                    scene_index=0, ensemble_index=1, graph_id=1, result_path="/tmp/g.yaml")
            record = json.loads(path.read_text().splitlines()[0])
            self.assertEqual(record["ensemble_index"], 1)

    def test_build_transport_wires_archive_only_when_configured(self):
        with tempfile.TemporaryDirectory() as d:
            ledger_path = str(Path(d) / "ledger.sqlite")
            archive_path = str(Path(d) / "archive.jsonl")
            lc = overlay_runtime.LedgerContext(
                ledger_path=ledger_path, credential_path="/tmp/cred", campaign_id="c",
                phase_id="engineering", allocation_id="a", run_id="r", max_output_tokens=8192,
            )
            with mock.patch.dict("os.environ", {}, clear=True):
                transport = overlay_runtime.build_transport(lc)
                self.assertIsNone(transport._on_raw_response)

            with mock.patch.dict("os.environ", {"ASP_PROSPECTIVE_RAW_ARCHIVE_PATH": archive_path}, clear=True):
                transport = overlay_runtime.build_transport(lc)
                self.assertIsInstance(transport._on_raw_response, overlay_runtime.RawResponseArchive)


if __name__ == "__main__":
    unittest.main()
