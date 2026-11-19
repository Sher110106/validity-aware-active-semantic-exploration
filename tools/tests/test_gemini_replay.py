"""gemini_replay.py: the cap, the stop on a billing reply, resume, and the input check. No network:
the author's loop and the genai client are stand-ins."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "live_policy"))
import gemini_replay as gr  # noqa: E402


class Usage:
    def __init__(self, p, c, th, cached=0):
        self.prompt_token_count, self.candidates_token_count, self.thoughts_token_count = p, c, th
        self.cached_content_token_count = cached


class Resp:
    def __init__(self, p=40000, c=500, th=300, cached=30000):
        self.usage_metadata = Usage(p, c, th, cached)


COST = (10000 * 1.25 + 30000 * 0.125 + 800 * 10.0) / 1e6      # one call of the stand-in client, at 2.5 Pro's prices


class ApiError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def make_lc(meter, calls_per_member=3, fail_at=None, error=None, bad_parse=(), fail_only=()):
    """A stand-in for the author's module. Each member makes `calls_per_member` calls through the
    metered client. `fail_at` = n makes the n-th try and every later one raise `error`; `fail_only`
    names the tries that raise it. A retry is a try of its own."""
    count = {"n": 0}

    def inner(_self):
        count["n"] += 1
        if (fail_at is not None and count["n"] >= fail_at) or count["n"] in fail_only:
            raise error
        return Resp()

    call = meter.wrap(inner)

    class LLMCompletion:
        def __init__(self, base_path, file_to_analyze, model_name, user_prompt, seed):
            self.base, self.seed = Path(base_path), seed

        def generate_completion_response(self, observed, slices):
            assert Path(observed).is_file() and len(list(Path(slices).iterdir())) == 2
            for _ in range(calls_per_member):
                call(None)
            return "graph text"

        def parse_response(self, text, observed, name):
            member = int(name.rsplit("_", 1)[1].split(".")[0])
            if member in bad_parse:
                return False
            (self.base / name).write_text("nodes: []\n")
            return True

    class Module:
        pass

    Module.LLMCompletion = LLMCompletion
    Module.count = count
    return Module


def sha(b):
    return hashlib.sha256(b).hexdigest()


def make_input(root, row, seed=42):
    d = root / row
    (d / "slices").mkdir(parents=True)
    graph, prompt = ("graph of %s\n" % row).encode(), b"the prompt\n"
    (d / "graph.yaml").write_bytes(graph)
    (d / "prompt.txt").write_bytes(prompt)
    slices = []
    for name in ("scene_z_0_0_to_0_3.jpg", "scene_z_0_3_to_0_5.jpg"):
        b = (row + name).encode()
        (d / "slices" / name).write_bytes(b)
        slices.append({"name": name, "bytes": len(b), "sha256": sha(b)})
    (d / "meta.json").write_text(json.dumps({"row_id": row, "run": "run_" + row, "stage": 8, "config_seed": seed,
                                             "graph_sha256": sha(graph), "prompt_sha256": sha(prompt), "slices": slices}))
    return d


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(gr, "RETRY_WAIT_S", 0)


@pytest.fixture
def dirs(tmp_path):
    inputs, out = tmp_path / "inputs", tmp_path / "out"
    out.mkdir()
    for r in ("row_a", "row_b", "row_c"):
        make_input(inputs, r)
    return inputs, out


def ledger_lines(out):
    return [json.loads(l) for l in (out / "gemini_calls.jsonl").read_text().splitlines()]


def test_all_rows_done_and_every_call_is_in_the_ledger(dirs):
    inputs, out = dirs
    meter = gr.Meter(str(out), 100.0)
    s = gr.replay(make_lc(meter), meter, str(inputs), str(out), ["row_a", "row_b"], 4, 1.0)
    assert s["stop"] is None and [r["row"] for r in s["rows"]] == ["row_a", "row_b"]
    assert all(r["done"] and [m["end"] for m in r["members"]] == ["ok"] * 4 for r in s["rows"])
    lines = ledger_lines(out)
    assert len(lines) == 2 * 4 * 3 == s["calls"]
    assert s["spent_usd"] == pytest.approx(24 * COST, abs=1e-4)
    assert sum(m["cost"] for r in s["rows"] for m in r["members"]) == pytest.approx(24 * COST, abs=1e-4)
    assert [m["seed"] for m in s["rows"][0]["members"]] == [42, 43, 44, 45]
    for k in range(4):
        assert (out / "row_a" / ("gemini_new_graph_%d.yaml" % k)).is_file()
        assert (out / "row_a" / ("response_%d.txt" % k)).read_text() == "graph text"
    assert (out / "row_a" / "habitat_scene_graph_original_graph0.yaml").read_bytes() == (inputs / "row_a" / "graph.yaml").read_bytes()


def test_a_row_does_not_start_without_room_for_all_its_members(dirs):
    inputs, out = dirs
    meter = gr.Meter(str(out), 3.9)                      # four members at the admit cost of 1.0 need 4.0
    s = gr.replay(make_lc(meter), meter, str(inputs), str(out), ["row_a", "row_b"], 4, 1.0)
    assert s["stop"] == "cap_before_row" and s["rows"] == [] and s["not_started"] == ["row_a", "row_b"]
    assert (out / "gemini_calls.jsonl").read_text() == "" and not (out / "row_a").exists()


def test_admit_grows_to_the_dearest_member_and_stops_the_next_row(dirs):
    inputs, out = dirs
    one_row = 4 * 3 * COST
    meter = gr.Meter(str(out), one_row + 4 * 0.05)      # admit 0.05 lets row_a in; its members cost 3 x COST each
    s = gr.replay(make_lc(meter), meter, str(inputs), str(out), ["row_a", "row_b"], 4, 0.05)
    assert [r["row"] for r in s["rows"]] == ["row_a"] and s["rows"][0]["done"]
    assert s["stop"] == "cap_before_row" and s["not_started"] == ["row_b"]
    assert s["admit_end"] == pytest.approx(3 * COST, abs=1e-4)


def test_cap_reached_inside_a_row_leaves_it_not_done_and_it_runs_again(dirs):
    inputs, out = dirs
    meter = gr.Meter(str(out), 5 * COST + gr.RESERVE_USD)
    s = gr.replay(make_lc(meter), meter, str(inputs), str(out), ["row_a", "row_b"], 4, 0.0)
    assert s["stop"] == "cap" and s["rows"][0]["done"] is False and s["not_started"] == ["row_b"]
    assert "stopped" in [m["end"] for m in s["rows"][0]["members"]]
    spent_before = meter.spent
    meter2 = gr.Meter(str(out), 100.0)                   # the ledger carries the spend over
    assert meter2.spent == pytest.approx(spent_before)
    s2 = gr.replay(make_lc(meter2), meter2, str(inputs), str(out), ["row_a", "row_b"], 4, 0.0)
    assert s2["skipped_done"] == [] and all(r["done"] for r in s2["rows"]) and len(s2["rows"]) == 2


def test_a_billing_reply_stops_everything(dirs):
    inputs, out = dirs
    meter = gr.Meter(str(out), 100.0)
    lc = make_lc(meter, fail_at=5, error=ApiError(402, "payment required"))
    s = gr.replay(lc, meter, str(inputs), str(out), ["row_a", "row_b", "row_c"], 1, 0.0)   # one member, so the order is fixed
    assert s["stop"] == "billing" and meter.stopped == "billing"
    assert [r["done"] for r in s["rows"]] == [True, False] and s["rows"][1]["members"][0]["end"] == "stopped"
    assert s["not_started"] == ["row_c"]
    assert lc.count["n"] == 5                            # no call reached the client after the refusal
    assert [l for l in ledger_lines(out) if "error" in l][0]["cost"] == 0.0


def test_a_done_row_is_not_run_again(dirs):
    inputs, out = dirs
    meter = gr.Meter(str(out), 100.0)
    gr.replay(make_lc(meter), meter, str(inputs), str(out), ["row_a"], 4, 0.0)
    meter2 = gr.Meter(str(out), 100.0)
    lc2 = make_lc(meter2)
    s = gr.replay(lc2, meter2, str(inputs), str(out), ["row_a", "row_b"], 4, 0.0)
    assert s["skipped_done"] == ["row_a"] and [r["row"] for r in s["rows"]] == ["row_b"] and lc2.count["n"] == 12


def test_a_member_that_does_not_parse_is_dropped_and_the_row_is_done(dirs):
    inputs, out = dirs
    meter = gr.Meter(str(out), 100.0)
    s = gr.replay(make_lc(meter, bad_parse=(2,)), meter, str(inputs), str(out), ["row_a"], 4, 0.0)
    ends = [m["end"] for m in s["rows"][0]["members"]]
    assert ends == ["ok", "ok", "dropped_parse", "ok"] and s["rows"][0]["done"] and s["stop"] is None
    assert not (out / "row_a" / "gemini_new_graph_2.yaml").exists()


def test_an_error_that_is_not_about_billing_drops_the_member_only(dirs):
    inputs, out = dirs
    meter = gr.Meter(str(out), 100.0)
    lc = make_lc(meter, calls_per_member=1, fail_only=(4,), error=ValueError("bad reply"))
    s = gr.replay(lc, meter, str(inputs), str(out), ["row_a"], 4, 0.0)
    ends = sorted(m["end"] for m in s["rows"][0]["members"])
    assert ends == ["dropped_error", "ok", "ok", "ok"] and s["rows"][0]["done"] and s["stop"] is None
    assert [l for l in ledger_lines(out) if "error" in l][0]["cost"] == gr.RESERVE_USD


def test_a_rate_limit_is_retried_and_the_member_goes_on(dirs):
    inputs, out = dirs
    meter = gr.Meter(str(out), 100.0)
    lc = make_lc(meter, fail_only=(2, 3), error=ApiError(429, "quota exceeded, check your plan and billing details"))
    s = gr.replay(lc, meter, str(inputs), str(out), ["row_a"], 1, 0.0)
    assert s["stop"] is None and s["rows"][0]["done"] and s["rows"][0]["members"][0]["end"] == "ok"
    lines = ledger_lines(out)
    assert len(lines) == 5 and [l.get("retry", 0) for l in lines] == [0, 0, 1, 2, 0]
    assert [l["cost"] for l in lines if "error" in l] == [0.0, 0.0]            # a refused call is not billed
    assert s["spent_usd"] == pytest.approx(3 * COST, abs=1e-4)


def test_the_third_failed_retry_stops_the_replay(dirs):
    inputs, out = dirs
    meter = gr.Meter(str(out), 100.0)
    lc = make_lc(meter, fail_at=2, error=ApiError(503, "unavailable"))
    s = gr.replay(lc, meter, str(inputs), str(out), ["row_a", "row_b"], 1, 0.0)
    assert s["stop"] == "retries" and s["rows"][0]["done"] is False and s["not_started"] == ["row_b"]
    assert lc.count["n"] == 1 + 1 + gr.RETRIES                               # one good call, one failure, three retries
    assert s["rows"][0]["members"][0]["end"] == "stopped"


def test_input_that_differs_from_its_meta_is_refused(dirs):
    inputs, _ = dirs
    (inputs / "row_a" / "graph.yaml").write_text("changed\n")
    with pytest.raises(ValueError, match="graph.yaml"):
        gr.check_inputs(str(inputs / "row_a"))
    (inputs / "row_b" / "slices" / "extra.jpg").write_bytes(b"x")
    with pytest.raises(ValueError, match="slices"):
        gr.check_inputs(str(inputs / "row_b"))


def test_failed_calls_are_classified_by_code_first():
    assert gr.classify(ApiError(402, "x")) == "stop"
    assert gr.classify(ApiError(429, "check your plan and billing details")) == "retry"
    assert gr.classify(ApiError(503, "unavailable")) == "retry" and gr.classify(ApiError(500, "internal")) == "retry"
    assert gr.classify(RuntimeError("Your prepayment credits are depleted")) == "stop"
    assert gr.classify(ApiError(403, "billing is not enabled for this project")) == "stop"
    assert gr.classify(ApiError(400, "invalid argument")) == "drop"
    assert gr.classify(ValueError("could not parse the 4020 nodes")) == "drop"


def test_rows_file_keeps_order_and_skips_comments(tmp_path):
    f = tmp_path / "rows.txt"
    f.write_text("# Round 1\nrow_b /some/dir 8\n\nrow_a\n# note\nrow_c x y\n")
    assert gr.read_rows(str(f)) == ["row_b", "row_a", "row_c"]


def test_call_cost_uses_the_cache_price_and_the_large_prompt_tier():
    assert gr.call_cost("gemini-2.5-pro", 40000, 30000, 500, 300) == pytest.approx(COST)
    assert gr.call_cost("gemini-2.5-pro", 40000, 0, 0, 0) == pytest.approx(0.05)
    assert gr.call_cost("gemini-2.5-pro", 250000, 0, 1000, 0) == pytest.approx(250000 * 2.5e-6 + 1000 * 15e-6)
    assert gr.call_cost("gemini-3.8-flash", 1000000, 0, 0, 1000000) == pytest.approx(0.75 + 3.75)
    assert gr.call_cost("gemini-3.8-flash", 1000, 5000, 0, 0) == pytest.approx(1000 * 0.075e-6)   # cached never above the prompt


def test_the_flash_model_is_metered_at_its_own_prices(dirs):
    inputs, out = dirs
    meter = gr.Meter(str(out), 100.0, "gemini-3.8-flash")
    s = gr.replay(make_lc(meter), meter, str(inputs), str(out), ["row_a"], 4, 0.0)
    one = (10000 * 0.75 + 30000 * 0.075 + 800 * 3.75) / 1e6
    assert s["spent_usd"] == pytest.approx(12 * one, abs=1e-4) and s["model"] == "gemini-3.8-flash"
