"""Tests for tools/llm_anthropic (Claude loop, meter, static replay). No network: a fake client throughout,
and a guard that fails any real socket connect."""
import ast
import base64
import copy
import hashlib
import importlib.util
import itertools
import json
import socket
import sys
import threading
import types
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx2
import pytest
from anthropic.types.beta import (
    BetaMessage, BetaRedactedThinkingBlock, BetaTextBlock, BetaThinkingBlock, BetaToolUseBlock, BetaUsage,
)

from llm_anthropic import author_tool, claude_loop, claude_static, meter as meter_mod
from llm_anthropic.claude_loop import LoopSettings, RateGate, run_member
from llm_anthropic.meter import CapStop, Caps, Meter, Usage, call_cost

OPUS = "claude-opus-5-5"
HAIKU = "claude-haiku-5-5"
REQ = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")

YAML_TEXT = """nodes:
- id: 0
  name: Table
  node_type: object
  position: '[1.0, 1.0, 0.5]'
  dimension: '[1.0, 1.0, 1.0]'
- id: 1
  name: Wall
  node_type: structure
  position: [5.0, 0.0, 1.0]
  dimension: [0.2, 4.0, 2.0]
- id: 2
  name: Kitchen
  node_type: room
  position: '[0.0, 0.0, 0.0]'
edges:
- [0, 2]
"""
COLLIDING = {"label": "Chair", "center_x": 1.0, "center_y": 1.0, "center_z": 0.5,
             "size_x": 0.5, "size_y": 0.5, "size_z": 0.5}
FREE = {"label": "Lamp", "center_x": 3.0, "center_y": 3.0, "center_z": 0.5,
        "size_x": 0.5, "size_y": 0.5, "size_z": 0.5}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def boom(self, *a, **k):
        raise AssertionError("network connect attempted in a test")
    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket.socket, "connect_ex", boom)


# ---- fakes -------------------------------------------------------------------------------------

class Raise:
    def __init__(self, exc, where="enter", snapshot_usage=None):
        self.exc, self.where, self.snapshot_usage = exc, where, snapshot_usage


def rate_limit(retry_after=None):
    h = {"retry-after": str(retry_after)} if retry_after is not None else {}
    return anthropic.RateLimitError("rate limited", response=httpx2.Response(429, headers=h, request=REQ), body=None)


def bad_request():
    return anthropic.BadRequestError("bad", response=httpx2.Response(400, request=REQ), body=None)


def conn_error():
    return anthropic.APIConnectionError(request=REQ)


def sse_error():
    return anthropic.APIStatusError("overloaded", response=httpx2.Response(200, request=REQ), body=None)


_ids = itertools.count(1)


def usage(inp=1000, out=1000, write=0, read=0, write_1h=0):
    kw = dict(input_tokens=inp, output_tokens=out, cache_creation_input_tokens=write + write_1h,
              cache_read_input_tokens=read)
    if write_1h:
        kw["cache_creation"] = {"ephemeral_5m_input_tokens": write, "ephemeral_1h_input_tokens": write_1h}
    return BetaUsage(**kw)


def reply(*blocks, stop=None, model=OPUS, use=None, stop_details=None):
    content = []
    for b in blocks:
        if b[0] == "thinking":
            content.append(BetaThinkingBlock(type="thinking", thinking=b[2] if len(b) > 2 else "", signature=b[1]))
        elif b[0] == "redacted":
            content.append(BetaRedactedThinkingBlock(type="redacted_thinking", data=b[1]))
        elif b[0] == "text":
            content.append(BetaTextBlock(type="text", text=b[1]))
        elif b[0] == "tool":
            content.append(BetaToolUseBlock(type="tool_use", name=b[1], input=b[2],
                                            id=b[3] if len(b) > 3 else f"toolu_{next(_ids)}"))
    if stop is None:
        stop = "tool_use" if any(c.type == "tool_use" for c in content) else "end_turn"
    return BetaMessage(id=f"msg_{next(_ids)}", model=model, role="assistant", type="message", stop_reason=stop,
                       stop_sequence=None, content=content, usage=use or usage(), stop_details=stop_details)


class FakeStream:
    def __init__(self, item, idx):
        self.item, self.request_id, self._idx = item, None, idx

    def __enter__(self):
        if isinstance(self.item, Raise) and self.item.where == "enter":
            raise self.item.exc
        return self

    def __exit__(self, *a):
        return False

    @property
    def current_message_snapshot(self):  # what the SDK has accumulated when a stream breaks
        su = getattr(self.item, "snapshot_usage", None)
        if su is None:
            raise RuntimeError("no snapshot yet")
        return SimpleNamespace(usage=su)

    def get_final_message(self):
        if isinstance(self.item, Raise):
            raise self.item.exc
        self.request_id = f"req_{self._idx}"
        return self.item


class FakeClient:
    """Stands in for anthropic.Anthropic. Records a deep copy of every request."""

    def __init__(self, script=None, responder=None):
        self.script, self.responder = list(script or []), responder
        self.calls: list = []
        self._lock = threading.Lock()
        self.base_url = "https://api.anthropic.com"
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream, create=self._create))

    def _next(self, api, kw):
        with self._lock:
            idx = len(self.calls)
            self.calls.append({"api": api, "kw": copy.deepcopy(kw)})
            item = self.responder(idx, copy.deepcopy(kw)) if self.responder else self.script.pop(0)
        return idx, item

    def _stream(self, **kw):
        idx, item = self._next("stream", kw)
        return FakeStream(item, idx)

    def _create(self, **kw):
        idx, item = self._next("create", kw)
        if isinstance(item, Raise):
            raise item.exc
        return item

    @property
    def requests(self):
        return [c["kw"] for c in self.calls]


def jpeg(i):
    return b"\xff\xd8\xff\xe0" + bytes([i]) * 40


def make_images(tmp_path, names=None):
    d = tmp_path / "slices"
    d.mkdir(exist_ok=True)
    names = names or [f"s{i}.jpg" for i in range(6)]
    paths = []
    for i, n in enumerate(names):
        (d / n).write_bytes(jpeg(i))
        paths.append(d / n)
    return paths


def make_input(root, name, n_images=6, prompt=None):
    d = Path(root) / name
    (d / "slices").mkdir(parents=True)
    (d / "prompt.txt").write_text(prompt if prompt is not None else f"PROMPT for {name}\n")
    (d / "graph.yaml").write_text(YAML_TEXT)
    (d / "meta.json").write_text(json.dumps({"run": "r1", "scene": "s1", "stage": 8, "track": "T"}))
    for i in range(n_images):
        (d / "slices" / f"slice_{i}.jpg").write_bytes(jpeg(i))
    return d


def echo_cb(name, args):
    return {"echo": name, "args": args}


def blocks_of(msg):
    return [b["type"] for b in msg["content"]]


# ---- messages, tools, request shape ------------------------------------------------------------

def test_first_message_block_order_image_order_and_cache_marker(tmp_path):
    # image paths given in reverse; the loop sorts by file name
    paths = list(reversed(make_images(tmp_path, ["c.jpg", "a.jpg", "b.jpg", "d.jpg", "f.jpg", "e.jpg"])))
    client = FakeClient([reply(("text", "done"))])
    rec = run_member(client, OPUS, "PROMPT TEXT", YAML_TEXT, paths, echo_cb)
    first = client.requests[0]["messages"][0]
    assert first["role"] == "user"
    assert blocks_of(first) == ["text", "text"] + ["image"] * 6
    assert first["content"][0]["text"] == "PROMPT TEXT"
    assert first["content"][1]["text"] == YAML_TEXT
    expected = [jpeg(i) for i, n in sorted(enumerate(["c", "a", "b", "d", "f", "e"]), key=lambda t: t[1])]
    got = [base64.b64decode(b["source"]["data"]) for b in first["content"][2:]]
    assert got == expected
    assert all(b["source"]["media_type"] == "image/jpeg" for b in first["content"][2:])
    marks = [i for i, b in enumerate(first["content"]) if "cache_control" in b]
    assert marks == [7] and first["content"][7]["cache_control"] == {"type": "ephemeral"}
    assert [m["name"] for m in rec["images"]] == ["a.jpg", "b.jpg", "c.jpg", "d.jpg", "e.jpg", "f.jpg"]


def test_images_only_in_first_message_and_tool_ids_pair_in_order(tmp_path):
    paths = make_images(tmp_path)
    client = FakeClient([
        reply(("thinking", "S1"), ("tool", "check_collision", COLLIDING, "toolu_A"),
              ("tool", "check_collision", FREE, "toolu_B")),
        reply(("text", "```yaml\nnodes: []\n```")),
    ])
    cb = author_tool.default_callback_factory()[0](YAML_TEXT)
    rec = run_member(client, OPUS, "P", YAML_TEXT, paths, cb)
    second = client.requests[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]
    results = second[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["toolu_A", "toolu_B"]
    assert all(r["type"] == "tool_result" for r in results)
    assert json.loads(results[0]["content"])["valid"] is False
    assert json.loads(results[1]["content"])["valid"] is True
    assert "image" not in {b["type"] for m in second[1:] for b in m["content"]}
    assert [t["id"] for t in rec["tool_calls"]] == ["toolu_A", "toolu_B"]


def test_tool_result_carries_the_authors_content_only_no_is_error_flag():
    client = FakeClient([reply(("tool", "check_collision", {"label": "x"}, "toolu_E")), reply(("text", "ok"))])
    cb = author_tool.make_author_callback(YAML_TEXT, author_tool.load_author_feasibility().fn)
    rec = run_member(client, OPUS, "P", YAML_TEXT, [], cb)
    block = client.requests[1]["messages"][2]["content"][0]
    assert set(block) == {"type", "tool_use_id", "content"}  # the author's loop sends no error flag
    assert "missing argument(s)" in json.loads(block["content"])["error"]
    assert rec["status"] == "ok" and rec["tool_calls"][0]["result"] == json.loads(block["content"])


def test_each_request_starts_with_previous_messages_byte_for_byte(tmp_path):
    paths = make_images(tmp_path)
    client = FakeClient([
        reply(("thinking", "SIG1"), ("text", "step 1"), ("tool", "check_collision", FREE, "t1")),
        reply(("thinking", "SIG2"), ("tool", "check_collision", COLLIDING, "t2")),
        reply(("redacted", "REDACTED"), ("tool", "check_collision", FREE, "t3")),
        reply(("text", "final")),
    ])
    cb = author_tool.default_callback_factory()[0](YAML_TEXT)
    run_member(client, OPUS, "P", YAML_TEXT, paths, cb)
    reqs = client.requests
    assert len(reqs) == 4
    for prev, cur in zip(reqs, reqs[1:]):
        n = len(prev["messages"])
        assert json.dumps(cur["messages"][:n]) == json.dumps(prev["messages"])
        assert len(cur["messages"]) == n + 2
        assert [m["role"] for m in cur["messages"][n:]] == ["assistant", "user"]
        for k in ("tools", "thinking", "output_config", "tool_choice", "model", "max_tokens", "betas"):
            assert cur[k] == prev[k]


def test_thinking_blocks_are_resent_unchanged():
    client = FakeClient([
        reply(("thinking", "SIGNATURE-1"), ("text", "let me check"), ("redacted", "OPAQUE"),
              ("tool", "check_collision", FREE, "toolu_T")),
        reply(("text", "done")),
    ])
    run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb)
    assistant = client.requests[1]["messages"][1]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == [
        {"signature": "SIGNATURE-1", "thinking": "", "type": "thinking"},
        {"text": "let me check", "type": "text"},
        {"data": "OPAQUE", "type": "redacted_thinking"},
        {"id": "toolu_T", "input": FREE, "name": "check_collision", "type": "tool_use"},
    ]


def test_request_parameters_follow_the_skill():
    client = FakeClient([reply(("text", "done"))])
    run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb)
    kw = client.requests[0]
    assert client.calls[0]["api"] == "stream"
    for banned in ("temperature", "top_p", "top_k", "seed", "fallbacks", "speed"):
        assert banned not in kw
    assert kw["tool_choice"] == {"type": "auto"}
    assert kw["thinking"] == {"type": "adaptive", "block_binding": {"prefix_mismatch_behavior": "error"}}
    assert kw["betas"] == [claude_loop.BETA_BLOCK_BINDING] == ["thinking-binding-controls-2026-08-01"]
    assert kw["output_config"] == {"effort": "medium"}  # sent explicitly
    assert kw["max_tokens"] == 64000
    assert kw["cache_control"] == {"type": "ephemeral"}
    assert kw["timeout"] == 300.0
    tool = kw["tools"][0]
    assert tool["name"] == "check_collision" and tool["strict"] is True and "eager_input_streaming" not in tool
    schema = tool["input_schema"]
    assert schema["additionalProperties"] is False and schema["required"] == list(author_tool.ARG_NAMES)


def test_settings_change_effort_ttl_binding():
    s = LoopSettings(effort="high", cache_ttl="1h", block_binding=None, max_tokens=1234)
    client = FakeClient([reply(("text", "x"))])
    run_member(client, HAIKU, "P", YAML_TEXT, [], echo_cb, s)
    kw = client.requests[0]
    assert kw["output_config"] == {"effort": "high"} and kw["max_tokens"] == 1234
    assert kw["thinking"] == {"type": "adaptive"} and "betas" not in kw
    assert kw["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert kw["messages"][0]["content"][-1]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    with pytest.raises(ValueError):
        LoopSettings(effort="medum")


def test_final_text_joins_text_blocks_and_records_request_ids_and_usage():
    client = FakeClient([
        reply(("tool", "check_collision", FREE, "t1"), use=usage(100, 50, write=2000, read=0)),
        reply(("thinking", "S"), ("text", "AAA"), ("text", "BBB"), use=usage(10, 70, write=30, read=2000)),
    ])
    rec = run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb)
    assert rec["status"] == "ok" and rec["final_text"] == "AAABBB" and rec["dropped"] is False
    assert rec["request_ids"] == ["req_0", "req_1"]
    assert rec["served_models"] == [OPUS, OPUS] and rec["flags"] == []
    assert rec["stop_reasons"] == ["tool_use", "end_turn"]
    assert rec["calls"][0]["usage"] == {"input_tokens": 100, "cache_write": 2000, "cache_write_5m": 2000,
                                        "cache_write_1h": 0, "cache_read": 0, "output_tokens": 50,
                                        "prompt_tokens": 2100}
    assert rec["calls"][1]["usage"]["cache_read"] == 2000
    assert len(rec["responses"]) == 2 and rec["responses"][0]["stop_reason"] == "tool_use"
    assert rec["turns"] == 2 and rec["tool_rounds"] == 1
    json.dumps(rec)  # the record is JSON-ready


def test_turn_limit_drops_member_after_50_tool_rounds():
    def responder(idx, kw):
        return reply(("tool", "check_collision", FREE, f"t{idx}"))
    client = FakeClient(responder=responder)
    rec = run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb)
    assert rec["status"] == "dropped_turn_limit" and rec["dropped"] is True and rec["final_text"] is None
    assert rec["tool_rounds"] == 50 and rec["turns"] == 50 and len(client.calls) == 50
    assert [len(c["kw"]["messages"]) for c in client.calls][:3] == [1, 3, 5]


def test_refusal_drops_member_and_logs_stop_details():
    sd = {"type": "refusal", "category": "cyber", "explanation": "declined"}
    client = FakeClient([reply(("text", "I can't"), stop="refusal", stop_details=sd)])
    rec = run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb)
    assert rec["status"] == "dropped_refusal" and rec["dropped"] and rec["final_text"] is None
    assert rec["stop_details"]["category"] == "cyber" and rec["stop_details"]["explanation"] == "declined"
    assert len(client.calls) == 1  # no fallback model, no retry
    assert "fallbacks" not in client.requests[0]


def test_served_model_mismatch_is_flagged():
    client = FakeClient([reply(("text", "x"), model="claude-opus-5-5-other")])
    rec = run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb)
    assert rec["status"] == "ok"
    assert rec["flags"] == ["served_model_mismatch:claude-opus-5-5-other"]


def test_only_registered_drop_reasons_exist():
    # §12: dropped = refused, 50 turns, still failing after the retries. A short or empty text is not a drop
    # here: it goes to the parser, which drops what does not parse.
    assert claude_loop.FINAL_STATUSES == {"ok", "dropped_refusal", "dropped_turn_limit", "dropped_error"}
    assert claude_loop.OPEN_STATUSES == {"error", "cap_stopped"}
    r = run_member(FakeClient([reply(("text", "part"), stop="max_tokens")]), OPUS, "P", YAML_TEXT, [], echo_cb)
    assert r["status"] == "ok" and r["final_text"] == "part" and "stop_max_tokens" in r["flags"]
    r = run_member(FakeClient([reply(("thinking", "S"), stop="end_turn")]), OPUS, "P", YAML_TEXT, [], echo_cb)
    assert r["status"] == "ok" and r["final_text"] == "" and "empty_text" in r["flags"]
    r = run_member(FakeClient([reply(("text", "x"), stop="pause_turn")]), OPUS, "P", YAML_TEXT, [], echo_cb)
    assert r["status"] == "dropped_error" and "pause_turn" in json.dumps(r["error"])

    def bad_cb(name, args):
        raise KeyError("id")
    r = run_member(FakeClient([reply(("tool", "check_collision", FREE, "t"))]), OPUS, "P", YAML_TEXT, [], bad_cb)
    assert r["status"] == "dropped_error" and r["error"]["where"] == "tool_callback"
    assert r["error"]["type"] == "KeyError" and r["dropped"] is True


def test_member_cap_is_a_cap_stop_not_a_drop(tmp_path):
    mt = Meter(tmp_path / "u.jsonl", caps=Caps(member=0.01), reserve_usd={OPUS: 0.02})
    r = run_member(FakeClient([reply(("text", "x"))]), OPUS, "P", YAML_TEXT, [], echo_cb, meter=mt)
    assert r["status"] == "cap_stopped" and r["error"]["scope"] == "member" and r["dropped"] is False
    assert r["status"] in claude_loop.OPEN_STATUSES


def test_non_jpeg_is_refused(tmp_path):
    p = tmp_path / "x.jpg"
    p.write_bytes(b"\x89PNG....")
    with pytest.raises(ValueError):
        run_member(FakeClient([]), OPUS, "P", YAML_TEXT, [p], echo_cb)


def test_make_client_pins_direct_url_and_owns_the_retries(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:4000")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "gateway-token-123")
    c = claude_loop.make_client("sk-ant-test-not-real")
    assert str(c.base_url).startswith("https://api.anthropic.com")
    assert c.timeout == 300.0
    assert c.max_retries == 0  # every retry is ours: metered, logged, three at most (§12)
    assert c.auth_token is None  # the gateway token is not picked up beside the key
    assert claude_loop.LoopSettings().retries == 3


# ---- transport: 429 backoff, stream breaks -----------------------------------------------------

class Clock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def now(self):
        return self.t

    def sleep(self, d):
        self.sleeps.append(d)
        self.t += d

    def gate(self):
        return RateGate(clock=self.now, sleep=self.sleep)


def test_429_backoff_uses_retry_after_then_succeeds(tmp_path):
    clk = Clock()
    client = FakeClient([Raise(rate_limit(3)), Raise(rate_limit(3)), reply(("text", "ok"))])
    mt = Meter(tmp_path / "usage.jsonl", caps=Caps(run=10))
    rec = run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb, meter=mt, gate=clk.gate(), rng=lambda: 0.0)
    assert rec["status"] == "ok" and len(client.calls) == 3
    assert clk.sleeps == [3.0, 3.0]
    assert rec["flags"] == ["retry_turn_0", "retry_turn_0"]
    lines = [json.loads(l) for l in (tmp_path / "usage.jsonl").read_text().splitlines()]
    assert [l["status"] for l in lines] == ["not_billed", "not_billed", "ok"]
    assert mt.held_total == pytest.approx(0.0)  # reservations released


def test_429_without_retry_after_backs_off_exponentially_and_gives_up():
    clk = Clock()
    s = LoopSettings(retries=2)
    client = FakeClient([Raise(rate_limit()), Raise(rate_limit()), Raise(rate_limit())])
    rec = run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb, s, gate=clk.gate(), rng=lambda: 0.0)
    assert clk.sleeps == [2.0, 4.0]
    # still failing after the retries: the member is dropped, and a drop is final
    assert rec["status"] == "dropped_error" and rec["error"]["type"] == "RateLimitError"
    assert rec["status"] in claude_loop.FINAL_STATUSES and rec["dropped"] is True


def test_gate_pauses_every_worker_that_shares_it():
    clk = Clock()
    g = clk.gate()
    g.wait()
    assert clk.sleeps == []
    g.trip(5)
    g.wait()
    assert clk.sleeps == [5]
    g.trip(1)  # shorter trip inside the pause does not shorten it
    g.trip(10)
    g.wait()
    assert clk.sleeps == [5, 10]


def test_stream_break_retries_once_and_books_the_failed_attempt(tmp_path):
    client = FakeClient([Raise(conn_error(), where="final"), reply(("text", "ok"))])
    mt = Meter(tmp_path / "usage.jsonl", reserve_usd={OPUS: 0.25})
    rec = run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb, meter=mt)
    assert rec["status"] == "ok" and rec["flags"] == ["retry_turn_0"] and len(client.calls) == 2
    lines = [json.loads(l) for l in (tmp_path / "usage.jsonl").read_text().splitlines()]
    assert lines[0]["status"] == "failed_estimated" and lines[0]["cost"] == 0.25
    assert lines[1]["status"] == "ok"


def test_transient_errors_retry_three_times_then_the_member_is_dropped():
    breaks = [conn_error, sse_error, lambda: anthropic.APITimeoutError(request=REQ),
              lambda: anthropic.InternalServerError("overloaded", response=httpx2.Response(529, request=REQ), body=None)]
    ok = FakeClient([Raise(breaks[0](), "final"), Raise(breaks[1](), "final"), Raise(breaks[2](), "final"),
                     reply(("text", "fine"))])
    rec = run_member(ok, OPUS, "P", YAML_TEXT, [], echo_cb, gate=Clock().gate(), rng=lambda: 0.0)
    assert rec["status"] == "ok" and len(ok.calls) == 4  # three retries allowed
    bad = FakeClient([Raise(b(), "final") for b in breaks])
    rec = run_member(bad, OPUS, "P", YAML_TEXT, [], echo_cb, gate=Clock().gate(), rng=lambda: 0.0)
    assert rec["status"] == "dropped_error" and len(bad.calls) == 4 and rec["final_text"] is None
    assert rec["status"] in claude_loop.FINAL_STATUSES  # a resume does not run it again


def test_a_broken_stream_is_booked_at_the_larger_of_reserve_and_usage(tmp_path):
    big = usage(inp=100_000, out=50_000)  # (100000*4 + 50000*20)/1e6 = 1.40
    client = FakeClient([Raise(sse_error(), "final", snapshot_usage=big), Raise(sse_error(), "final",
                                                                               snapshot_usage=usage(10, 10)),
                         reply(("text", "ok"))])
    mt = Meter(tmp_path / "usage.jsonl", reserve_usd={OPUS: 0.25})
    rec = run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb, meter=mt, gate=Clock().gate(), rng=lambda: 0.0)
    lines = [json.loads(l) for l in (tmp_path / "usage.jsonl").read_text().splitlines()]
    assert [l["status"] for l in lines] == ["failed_estimated", "failed_estimated", "ok"]
    assert lines[0]["cost"] == pytest.approx(1.40)  # usage shows more than the reserve
    assert lines[1]["cost"] == 0.25  # usage shows less: the reserve stands
    assert rec["status"] == "ok"


def test_5xx_before_the_stream_is_not_billed_but_is_retried(tmp_path):
    e = anthropic.InternalServerError("overloaded", response=httpx2.Response(529, request=REQ), body=None)
    client = FakeClient([Raise(e), reply(("text", "ok"))])
    mt = Meter(tmp_path / "usage.jsonl")
    rec = run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb, meter=mt, gate=Clock().gate(), rng=lambda: 0.0)
    lines = [json.loads(l) for l in (tmp_path / "usage.jsonl").read_text().splitlines()]
    assert rec["status"] == "ok" and [l["status"] for l in lines] == ["not_billed", "ok"]


def test_400_is_not_billed_not_retried_and_leaves_the_member_unfinished(tmp_path):
    client = FakeClient([Raise(bad_request())])
    mt = Meter(tmp_path / "usage.jsonl")
    rec = run_member(client, OPUS, "P", YAML_TEXT, [], echo_cb, meter=mt)
    # a bad request is a fault in our harness, not a member that failed after retries: open, not dropped
    assert rec["status"] == "error" and rec["error"]["status_code"] == 400 and len(client.calls) == 1
    assert rec["status"] in claude_loop.OPEN_STATUSES and rec["dropped"] is False
    assert json.loads((tmp_path / "usage.jsonl").read_text())["status"] == "not_billed"
    assert mt.settled_run == 0.0


# ---- meter -------------------------------------------------------------------------------------

def test_cost_arithmetic_opus():
    u = Usage(input_tokens=1000, cache_write_5m=2000, cache_write_1h=500, cache_read=10000, output_tokens=3000)
    cost, info = call_cost(OPUS, u)
    assert cost == pytest.approx((1000 * 4 + 2000 * 5 + 500 * 8 + 10000 * 0.2 + 3000 * 20) / 1e6)
    assert cost == pytest.approx(0.08) and info["tier"] == "standard"


def test_haiku_long_prompt_price_step_at_100k():
    at = Usage(input_tokens=50_000, cache_write_5m=10_000, cache_read=40_000, output_tokens=2000)
    assert at.prompt_tokens == 100_000
    c1, i1 = call_cost(HAIKU, at)
    assert i1["tier"] == "standard"
    assert c1 == pytest.approx((50_000 * 0.10 + 10_000 * 0.125 + 40_000 * 0.01 + 2000 * 0.50) / 1e6)
    over = Usage(input_tokens=50_001, cache_write_5m=10_000, cache_read=40_000, output_tokens=2000)
    c2, i2 = call_cost(HAIKU, over)
    assert i2["tier"] == "long" and over.prompt_tokens == 100_001
    assert c2 == pytest.approx((50_001 * 0.50 + 10_000 * 0.625 + 40_000 * 0.05 + 2000 * 2.50) / 1e6)
    assert c2 > 4 * c1  # the whole call moves to the higher card, output included
    c3, i3 = call_cost(HAIKU, Usage(cache_write_1h=90_000))
    assert i3["tier"] == "standard" and c3 == pytest.approx(90_000 * 0.10 * 2.0 / 1e6)  # 1h write = 2x input rate
    c4, i4 = call_cost(HAIKU, Usage(cache_write_1h=110_000))
    assert i4["tier"] == "long" and c4 == pytest.approx(110_000 * 0.50 * 2.0 / 1e6)


def test_usage_from_api_splits_cache_writes_by_ttl():
    u = Usage.from_api(usage(inp=5, out=6, write=100, write_1h=40, read=7))
    assert (u.input_tokens, u.cache_write_5m, u.cache_write_1h, u.cache_read, u.output_tokens) == (5, 100, 40, 7, 6)
    bare = Usage.from_api({"input_tokens": 1, "output_tokens": 2, "cache_creation_input_tokens": 9,
                           "cache_read_input_tokens": 0})
    assert bare.cache_write_5m == 9
    assert Usage.from_api({"cache_creation_input_tokens": 9}, default_ttl="1h").cache_write_1h == 9


def test_default_reserves_cover_the_worst_call():
    assert meter_mod.DEFAULT_RESERVE_USD[OPUS] == 1.50 and meter_mod.DEFAULT_RESERVE_USD[HAIKU] == 0.35


def test_unknown_model_is_not_priced_at_zero(tmp_path):
    with pytest.raises(meter_mod.UnknownModel):
        call_cost("claude-nonesuch", Usage(input_tokens=1))
    with pytest.raises(meter_mod.UnknownModel):
        Meter(tmp_path / "u.jsonl").reserve("claude-nonesuch", "k")
    assert "2026" in meter_mod.PRICE_DATE and "skill" in meter_meter_source()


def meter_meter_source():
    return meter_mod.PRICE_SOURCE


def test_reserve_settle_and_run_cap(tmp_path):
    mt = Meter(tmp_path / "usage.jsonl", caps=Caps(run=1.0), reserve_usd={OPUS: 0.4})
    r1 = mt.reserve(OPUS, "m1")
    r2 = mt.reserve(OPUS, "m2")
    with pytest.raises(CapStop) as ei:
        mt.reserve(OPUS, "m3")  # settled 0 + held 0.8 + 0.4 > 1.0
    assert ei.value.scope == "run" and mt.stopped is not None
    cost = mt.settle(r1, Usage(input_tokens=1000, output_tokens=1000), request_id="req_1", served_model=OPUS,
                     stop_reason="end_turn", turn=0)
    assert cost == pytest.approx(0.024)
    assert mt.settled_run == pytest.approx(0.024) and mt.held_total == pytest.approx(0.4)
    mt.reserve(OPUS, "m3")  # 0.024 + 0.4 + 0.4 = 0.824 <= 1.0
    mt.release(r2, "http 429")
    line = json.loads((tmp_path / "usage.jsonl").read_text().splitlines()[0])
    assert line["request_id"] == "req_1" and line["cost"] == pytest.approx(0.024) and line["model"] == OPUS
    assert line["input_tokens"] == 1000 and line["output_tokens"] == 1000 and line["tier"] == "standard"


def test_member_model_and_campaign_caps_and_ledger_reload(tmp_path):
    led = tmp_path / "usage.jsonl"
    mt = Meter(led, caps=Caps(member=0.05), reserve_usd={OPUS: 0.04})
    r = mt.reserve(OPUS, "k1")
    mt.settle(r, Usage(input_tokens=10_000))  # 0.04
    with pytest.raises(CapStop) as ei:
        mt.reserve(OPUS, "k1")
    assert ei.value.scope == "member" and mt.stopped is None  # a member cap is not a run stop
    mt.reserve(OPUS, "k2")  # other member is fine
    # a new process reads the ledger: campaign and model totals persist, the run total starts at zero
    mt2 = Meter(led, caps=Caps(campaign=0.05, by_model={OPUS: 0.05}), reserve_usd={OPUS: 0.04})
    assert mt2.settled_campaign == pytest.approx(0.04) and mt2.settled_run == 0.0
    with pytest.raises(CapStop) as ei:
        mt2.reserve(OPUS, "k9")
    assert ei.value.scope in ("model", "campaign")
    mt3 = Meter(led, caps=Caps(by_model={HAIKU: 0.01}), reserve_usd={HAIKU: 0.02})
    with pytest.raises(CapStop) as ei:
        mt3.reserve(HAIKU, "h1")
    assert ei.value.scope == "model"


def test_failed_call_is_booked_at_its_reserve_and_a_torn_ledger_line_is_skipped(tmp_path):
    led = tmp_path / "usage.jsonl"
    mt = Meter(led, reserve_usd={OPUS: 0.3})
    r = mt.reserve(OPUS, "k")
    assert mt.settle_failed(r, "boom") == 0.3 and mt.settled_run == 0.3
    with open(led, "a") as f:
        f.write('{"cost": 1.0, "model": "claude-opus')  # torn line from a crash
    mt2 = Meter(led)
    assert mt2.settled_campaign == pytest.approx(0.3) and mt2.ledger_bad_lines == 1


def test_admit_member_waits_for_running_members_then_stops_cleanly(tmp_path):
    mt = Meter(tmp_path / "u.jsonl", caps=Caps(run=0.25), admit_usd={OPUS: 0.1})
    mt.admit_member(OPUS, "a")  # needs 0.1 <= 0.25
    mt.admit_member(OPUS, "b")  # needs 0.2 <= 0.25
    seen = {}

    def third():
        try:
            mt.admit_member(OPUS, "c")  # needs 0.3 > 0.25: waits while a and b run
            seen["r"] = "admitted"
        except CapStop as e:
            seen["r"] = e.scope

    t = threading.Thread(target=third)
    t.start()
    t.join(timeout=0.3)
    assert t.is_alive()  # still waiting
    mt.end_member(OPUS, "a")
    t.join(timeout=2)
    assert seen["r"] == "admitted"  # one member ended: 0.1 running + 0.1 new <= 0.25
    mt.end_member(OPUS, "b")
    mt.end_member(OPUS, "c")
    mt_small = Meter(tmp_path / "u2.jsonl", caps=Caps(run=0.05), admit_usd={OPUS: 0.1})
    with pytest.raises(CapStop):
        mt_small.admit_member(OPUS, "x")  # nothing running, no room: clean stop


# ---- campaign: input format, rounds, whole-member stops, resume, prewarm -----------------------

def campaign_responder(per_call=usage(1000, 1000), warm=None, flat=False):
    """Member = tool call, then final text. Pre-warm is recognised by max_tokens 0.

    flat=True makes every call cost exactly `per_call` (0.024 on Opus), so cap tests can count to the cent."""
    warm = warm if warm is not None else set()

    def responder(idx, kw):
        prompt = kw["messages"][0]["content"][0]["text"]
        if kw["max_tokens"] == 0:
            warm.add(prompt)
            return reply(use=usage(inp=10, out=0, write=5000))
        n = len(kw["messages"])
        use = per_call
        if n == 1 and not flat:
            use = usage(inp=100, out=1000, read=5000) if prompt in warm else usage(inp=100, out=1000, write=5000)
        if n == 1:
            return reply(("thinking", "S"), ("tool", "check_collision", FREE, f"t{idx}"), use=use)
        return reply(("text", f"FINAL for {prompt.strip()}"), use=use)
    return responder


def run_static(tmp_path, specs, *, client, members=2, models=(OPUS,), caps=None, reserve=None, admit=None,
               resume=True, prewarm=False, concurrency=1, rounds=None, settings=None, out="out"):
    out_dir = tmp_path / out
    mt = Meter(out_dir / "usage.jsonl", caps=caps or Caps(run=100), reserve_usd=reserve, admit_usd=admit)
    factory, feas = author_tool.default_callback_factory()
    summary = claude_static.run_campaign(
        client=client, specs=specs, rounds=rounds or [sorted(specs)], models=list(models), members=members,
        settings=settings or LoopSettings(), meter=mt, out_dir=out_dir, concurrency=concurrency, resume=resume,
        do_prewarm=prewarm, callback_factory=factory, feasibility_sha=feas.sha256, sleep=lambda d: None)
    return summary, mt, out_dir


def test_input_loader_checks_files_images_and_meta(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    spec = claude_static.load_input(root / "a")
    assert spec.id == "a" and len(spec.images) == 6 and spec.meta["stage"] == 8
    assert [p.name for p in spec.images] == sorted(p.name for p in spec.images)
    make_input(root, "few", n_images=5)
    with pytest.raises(ValueError, match="expected 6"):
        claude_static.load_input(root / "few")
    claude_static.load_input(root / "few", expect_images=0)
    make_input(root, "nometa")
    (root / "nometa" / "meta.json").write_text(json.dumps({"run": 1}))
    with pytest.raises(ValueError, match="missing"):
        claude_static.load_input(root / "nometa")
    (root / "a" / "prompt.txt").unlink()
    with pytest.raises(ValueError, match="prompt.txt"):
        claude_static.load_input(root / "a")


def mdir_of(out, model, i, k, effort="medium"):
    return claude_static.member_dir(out, model, effort, i, k)


def test_order_file_rounds_in_the_sample_frame_format(tmp_path):
    root = tmp_path / "in"
    for name in ("b", "c", "a"):
        make_input(root, name)  # meta: run r1, stage 8
    specs = claude_static.load_inputs(root)
    text = ("# The sample frame: 3 rows. <row_id> <run_dir in the container> <stage>\n"
            "# Round 1: stage 8\n"
            "b /workspace/runs/live_campaign/r1 8\n"
            "c /workspace/runs/live_campaign/r1 8   # trailing note\n"
            "\n"
            "# Round 2: the rest\n"
            "a /workspace/runs/live_campaign/r1 8\n")
    assert claude_static.parse_order(text, specs) == [["b", "c"], ["a"]]
    assert claude_static.plan_rounds(specs, text) == [["b", "c"], ["a"]]
    assert claude_static.plan_rounds(specs, None) == [["a", "b", "c"]]
    with pytest.raises(ValueError, match="unknown"):
        claude_static.parse_order("# Round 1\nzzz /w/r1 8\n", specs)
    with pytest.raises(ValueError, match="twice"):
        claude_static.parse_order("# Round 1\na /w/r1 8\na /w/r1 8\n", specs)
    with pytest.raises(ValueError, match="stage"):
        claude_static.parse_order("# Round 1\na /w/r1 9\n", specs)  # the saved input says stage 8
    with pytest.raises(ValueError, match="run"):
        claude_static.parse_order("# Round 1\na /w/other_run 8\n", specs)


def test_sample_frame_file_parses_when_inputs_match():
    frame = Path(__file__).resolve().parents[1] / "live_policy" / "semantic" / "sample_frame.txt"
    if not frame.exists():
        pytest.skip("sample_frame.txt not present")
    rows = [l.split() for l in frame.read_text().splitlines() if l.strip() and not l.startswith("#")]
    fake = {r[0]: SimpleNamespace(meta={"run": Path(r[1]).name, "stage": int(r[2])}) for r in rows}
    rounds = claude_static.parse_order(frame.read_text(), fake)
    assert sum(len(r) for r in rounds) == len(rows) == 44 and len(rounds) == 4
    assert [len(r) for r in rounds][:2] == [12, 12]


def test_campaign_writes_one_folder_per_model_input_member(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    make_input(root, "b")
    specs = claude_static.load_inputs(root)
    client = FakeClient(responder=campaign_responder())
    summary, mt, out = run_static(tmp_path, specs, client=client, members=2, models=(HAIKU, OPUS))
    for model in (HAIKU, OPUS):
        for i in ("a", "b"):
            for k in (0, 1):
                d = mdir_of(out, model, i, k)
                assert d == out / model / "effort_medium" / i / f"member_{k}"
                rec = json.loads((d / "record.json").read_text())
                assert rec["status"] == "ok" and rec["model"] == model and rec["input"] == i and rec["member"] == k
                assert (d / "final.txt").read_text() == f"FINAL for PROMPT for {i}"
                assert rec["meta"]["stage"] == 8 and len(rec["meta"]["feasibility_sha256"]) == 64
    assert summary["counts"] == {"ok": 8}
    assert len((out / "usage.jsonl").read_text().splitlines()) == 16
    # Haiku first in the round, then Opus
    models_called = [c["kw"]["model"] for c in client.calls]
    assert models_called == sorted(models_called, key=lambda m: m != HAIKU)


def test_cap_stop_falls_between_whole_members(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    specs = claude_static.load_inputs(root)
    # each call: 1000 in + 1000 out = 0.024; a member is two calls = 0.048. The round projection fits
    # (3 x 0.04 = 0.12 <= 0.12), so the round starts; the third member finds no room at admission.
    client = FakeClient(responder=campaign_responder(flat=True))
    summary, mt, out = run_static(tmp_path, specs, client=client, members=3, caps=Caps(run=0.12),
                                  reserve={OPUS: 0.03}, admit={OPUS: 0.04})
    assert summary["round_skips"] == []
    assert summary["counts"] == {"ok": 2, "skipped_cap": 1}
    assert summary["stopped_by_cap"] is True
    assert mt.settled_run == pytest.approx(0.096) and mt.settled_run <= 0.12
    recs = [json.loads(p.read_text()) for p in out.glob("*/*/*/member_*/record.json")]
    assert len(recs) == 2 and all(r["status"] == "ok" for r in recs)  # no half-finished member on disk


def test_cap_hit_mid_member_is_recorded_as_open_and_reruns_on_resume(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    specs = claude_static.load_inputs(root)
    # admit estimate far below the real member cost (0.048): admission lets member 1 start, a call reserve stops it
    client = FakeClient(responder=campaign_responder(flat=True))
    summary, mt, out = run_static(tmp_path, specs, client=client, members=2, caps=Caps(run=0.07),
                                  reserve={OPUS: 0.03}, admit={OPUS: 0.01})
    assert summary["counts"] == {"ok": 1, "cap_stopped": 1}
    m1 = mdir_of(out, OPUS, "a", 1)
    rec = json.loads((m1 / "record.json").read_text())
    assert rec["status"] == "cap_stopped" and rec["final_text"] is None
    assert not claude_static.is_finished(m1, "medium") and claude_static.is_finished(mdir_of(out, OPUS, "a", 0), "medium")
    # resume with more room: only the open member runs
    client2 = FakeClient(responder=campaign_responder(flat=True))
    summary2, _, _ = run_static(tmp_path, specs, client=client2, members=2, caps=Caps(run=5), resume=True)
    assert summary2["counts"] == {"resumed": 1, "ok": 1}
    assert len(client2.calls) == 2  # one member, two calls


def test_resume_never_pays_for_a_finished_member_twice(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    make_input(root, "b")
    specs = claude_static.load_inputs(root)
    c1 = FakeClient(responder=campaign_responder())
    run_static(tmp_path, specs, client=c1, members=2)
    assert len(c1.calls) == 8
    ledger_before = (tmp_path / "out" / "usage.jsonl").read_text()
    c2 = FakeClient(responder=campaign_responder())
    summary, _, out = run_static(tmp_path, specs, client=c2, members=2, resume=True)
    assert c2.calls == [] and summary["counts"] == {"resumed": 4}
    assert (out / "usage.jsonl").read_text() == ledger_before  # nothing new was billed
    # an errored member is open: it runs again; a dropped one is final: it does not
    med = {"effort": "medium"}
    (mdir_of(out, OPUS, "a", 0) / "record.json").write_text(json.dumps({"status": "error", "settings": med}))
    (mdir_of(out, OPUS, "a", 1) / "record.json").write_text(json.dumps({"status": "dropped_error", "settings": med}))
    c3 = FakeClient(responder=campaign_responder())
    summary3, _, _ = run_static(tmp_path, specs, client=c3, members=2, resume=True)
    assert summary3["counts"] == {"ok": 1, "resumed": 3} and len(c3.calls) == 2


def test_prewarm_then_members_and_first_call_reads_the_cache(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    make_input(root, "b")
    specs = claude_static.load_inputs(root)
    client = FakeClient(responder=campaign_responder())
    summary, mt, out = run_static(tmp_path, specs, client=client, members=2, prewarm=True, concurrency=3)
    calls = client.calls
    pre = [c for c in calls if c["kw"]["max_tokens"] == 0]
    assert len(pre) == 2 and all(c["api"] == "create" for c in pre)  # one per input, non-streaming
    for p in pre:
        prompt = p["kw"]["messages"][0]["content"][0]["text"]
        first_member_idx = min(i for i, c in enumerate(calls)
                               if c["kw"]["max_tokens"] != 0 and c["kw"]["messages"][0]["content"][0]["text"] == prompt)
        assert calls.index(p) < first_member_idx  # the pre-warm finished before that input's members began
        member_first = next(c for c in calls if c["kw"]["max_tokens"] != 0 and len(c["kw"]["messages"]) == 1
                            and c["kw"]["messages"][0]["content"][0]["text"] == prompt)
        for k in ("model", "tools", "thinking", "output_config", "tool_choice", "betas"):
            assert p["kw"][k] == member_first["kw"][k]  # same thinking and effort, same cache key parts
        assert p["kw"]["messages"] == member_first["kw"]["messages"]  # same first message, same marker
        assert "cache_control" not in p["kw"]  # explicit marker only; no top-level one
    assert summary["warnings"] == [] and summary["counts"] == {"ok": 4}
    for p in out.glob("*/*/*/member_*/record.json"):
        rec = json.loads(p.read_text())
        assert rec["calls"][0]["usage"]["cache_read"] == 5000 and "first_call_no_cache_read" not in rec["flags"]
    kinds = [json.loads(l)["kind"] for l in (out / "usage.jsonl").read_text().splitlines()]
    assert kinds.count("prewarm") == 2


def test_prewarm_warns_when_a_first_call_does_not_read_the_cache(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    specs = claude_static.load_inputs(root)

    def responder(idx, kw):
        if kw["max_tokens"] == 0:
            return reply(use=usage(inp=10, out=0, write=5000))
        if len(kw["messages"]) == 1:
            return reply(("text", "x"), use=usage(inp=100, out=10, write=5000))  # wrote again, read nothing
        raise AssertionError
    summary, _, out = run_static(tmp_path, specs, client=FakeClient(responder=responder), members=1, prewarm=True)
    assert any("first call read no cache" in w for w in summary["warnings"])
    rec = json.loads((mdir_of(out, OPUS, "a", 0) / "record.json").read_text())
    assert "first_call_no_cache_read" in rec["flags"]


def test_prewarm_failure_skips_the_input_without_running_members(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    specs = claude_static.load_inputs(root)
    client = FakeClient(responder=lambda idx, kw: Raise(bad_request()))
    summary, _, out = run_static(tmp_path, specs, client=client, members=2, prewarm=True)
    assert summary["counts"] == {"skipped_prewarm_failed": 2} and len(client.calls) == 1
    assert not list(out.glob("*/*/*/member_*"))


def test_one_models_cap_stops_only_that_model(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    specs = claude_static.load_inputs(root)
    client = FakeClient(responder=campaign_responder(flat=True))
    # Haiku's reserve (0.02) is above its cap (0.01): its first call is refused with scope "model".
    # Its admit estimate is tiny so the round projection lets it start.
    summary, mt, out = run_static(tmp_path, specs, client=client, members=2, models=(HAIKU, OPUS),
                                  caps=Caps(run=100, by_model={HAIKU: 0.01}),
                                  reserve={HAIKU: 0.02, OPUS: 0.03}, admit={HAIKU: 0.001, OPUS: 0.05})
    by = {(o["model"], o["status"]) for o in summary["outcomes"]}
    assert (HAIKU, "cap_stopped") in by and (HAIKU, "skipped_cap") in by
    assert [o["status"] for o in summary["outcomes"] if o["model"] == OPUS] == ["ok", "ok"]  # Opus went on
    assert summary["stopped_models"] == [HAIKU] and summary["stopped_all"] is False
    assert all(c["kw"]["model"] == OPUS for c in client.calls if c["kw"]["max_tokens"] != 0)


def test_run_cap_stops_every_model(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    specs = claude_static.load_inputs(root)
    client = FakeClient(responder=campaign_responder(flat=True))
    summary, mt, out = run_static(tmp_path, specs, client=client, members=3, models=(HAIKU, OPUS),
                                  caps=Caps(run=0.05), reserve={HAIKU: 0.03, OPUS: 0.03},
                                  admit={HAIKU: 0.01, OPUS: 0.01})
    assert summary["stopped_all"] is True
    assert not any(o["status"] == "ok" and o["model"] == OPUS for o in summary["outcomes"])


def test_round_projection_stops_a_model_that_cannot_finish_the_round(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    make_input(root, "b")
    specs = claude_static.load_inputs(root)
    client = FakeClient(responder=campaign_responder(flat=True))  # a member costs 0.048 (two calls)
    logs = []
    out_dir = tmp_path / "out"
    mt = Meter(out_dir / "usage.jsonl", caps=Caps(run=100, by_model={OPUS: 0.20}),
               reserve_usd={OPUS: 0.03, HAIKU: 0.03}, admit_usd={OPUS: 0.06, HAIKU: 0.06})
    factory, feas = author_tool.default_callback_factory()
    summary = claude_static.run_campaign(
        client=client, specs=specs, rounds=[["a"], ["b"]], models=[HAIKU, OPUS], members=2, settings=LoopSettings(),
        meter=mt, out_dir=out_dir, concurrency=1, resume=True, do_prewarm=False, callback_factory=factory,
        sleep=lambda d: None, log=logs.append)
    # round 1: Opus projected 2 x 0.06 = 0.12 <= 0.20, runs and settles 0.096.
    # round 2: projected 0.12 > 0.20 - 0.096 = 0.104, so Opus stops before the round. Haiku has no cap and goes on.
    st = {(o["model"], o["input"]): [] for o in summary["outcomes"]}
    for o in summary["outcomes"]:
        st[(o["model"], o["input"])].append(o["status"])
    assert st[(OPUS, "a")] == ["ok", "ok"] and (OPUS, "b") not in st
    assert st[(HAIKU, "a")] == ["ok", "ok"] and st[(HAIKU, "b")] == ["ok", "ok"]
    assert [(s["round"], s["model"], s["scope"]) for s in summary["round_skips"]] == [(2, OPUS, "model")]
    assert summary["round_skips"][0]["projected_usd"] == pytest.approx(0.12)
    assert any("stops before round 2" in l and OPUS in l for l in logs)
    assert summary["stopped_models"] == [OPUS] and summary["stopped_all"] is False
    # Haiku ran first inside each round
    order = [c["kw"]["model"] for c in client.calls]
    assert order[: 4] == [HAIKU] * 4 and OPUS in order[4:8]


def test_effort_is_part_of_the_resume_key(tmp_path):
    root = tmp_path / "in"
    make_input(root, "a")
    specs = claude_static.load_inputs(root)
    c1 = FakeClient(responder=campaign_responder(flat=True))
    _, _, out = run_static(tmp_path, specs, client=c1, members=1, settings=LoopSettings(effort="medium"))
    c2 = FakeClient(responder=campaign_responder(flat=True))
    summary, _, _ = run_static(tmp_path, specs, client=c2, members=1, resume=True, settings=LoopSettings(effort="low"))
    assert summary["counts"] == {"ok": 1} and len(c2.calls) == 2  # not "resumed": a new effort is new work
    assert c2.requests[0]["output_config"] == {"effort": "low"}
    assert (out / OPUS / "effort_medium" / "a" / "member_0" / "record.json").exists()  # the first run is intact
    assert (out / OPUS / "effort_low" / "a" / "member_0" / "record.json").exists()
    # a record whose saved effort differs from its folder is not done either
    rec = json.loads((mdir_of(out, OPUS, "a", 0, "low") / "record.json").read_text())
    rec["settings"]["effort"] = "medium"
    (mdir_of(out, OPUS, "a", 0, "low") / "record.json").write_text(json.dumps(rec))
    assert not claude_static.is_finished(mdir_of(out, OPUS, "a", 0, "low"), "low")


def test_out_dir_lock_is_exclusive_for_the_life_of_the_process(tmp_path):
    out = tmp_path / "out"
    with claude_static.out_lock(out):
        with pytest.raises(SystemExit, match="lock"):
            with claude_static.out_lock(out):
                pass
        with pytest.raises(SystemExit, match="lock"):  # a shared ledger path is locked too
            with claude_static.out_lock(tmp_path / "other_out", ledger=out / "usage.jsonl"):
                pass
    with claude_static.out_lock(out):  # free again once released
        pass


# ---- CLI ---------------------------------------------------------------------------------------

def test_dry_run_builds_requests_calls_nothing_and_never_shows_the_key(tmp_path, monkeypatch, capsys):
    root = tmp_path / "in"
    make_input(root, "a")
    make_input(root, "b")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-SECRET-VALUE-123")

    def no_client(settings):
        raise AssertionError("a client was built in a dry run")
    rc = claude_static.main([str(root), str(tmp_path / "out"), "--dry-run", "--members", "3"], client_factory=no_client)
    shown = capsys.readouterr()
    assert rc == 0
    assert "sk-ant-SECRET" not in shown.out + shown.err
    assert "image blocks=6" in shown.out and "members to run=3/3" in shown.out and "count_tokens" in shown.out
    import re
    sizes = [int(m) for m in re.findall(r"request bytes=(\d+)", shown.out)]
    assert len(sizes) == 4 and all(s > 780 for s in sizes)  # 2 inputs x 2 models; the whole request, not a stub
    assert "projected" in shown.out
    assert not (tmp_path / "out").exists()


def test_main_runs_with_a_fake_client_and_never_writes_the_key(tmp_path, monkeypatch, capsys):
    root = tmp_path / "in"
    make_input(root, "a")
    secret = "sk-ant-SECRET-VALUE-456"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    seen = {}
    client = FakeClient(responder=campaign_responder())

    def fake_make_client(key, settings=None, **kw):
        seen["key"] = key
        return client
    monkeypatch.setattr(claude_loop, "make_client", fake_make_client)
    out = tmp_path / "out"
    argv = [str(root), str(out), "--models", "opus", "--members", "2", "--cap-run", "5", "--cap-model", "opus=3",
            "--admit", "opus=0.5", "--reserve", "opus=0.1"]
    rc = claude_static.main(argv)
    cap = capsys.readouterr()
    assert rc == 0 and seen["key"] == secret
    assert secret not in cap.out + cap.err
    for p in out.rglob("*"):
        if p.is_file():
            assert secret not in p.read_text(), p
    assert (out / "summary.json").exists() and (out / "usage.jsonl").exists()
    # without --resume a second run over finished members is refused
    with pytest.raises(SystemExit, match="--resume"):
        claude_static.main(argv)


def sse(events):
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


def stream_events(model, blocks, stop, use):
    """Server-sent events for one reply. blocks: ('thinking', sig) | ('text', s) | ('tool', id, name, input)."""
    ev = [{"type": "message_start", "message": {
        "id": "msg_1", "type": "message", "role": "assistant", "model": model, "content": [], "stop_reason": None,
        "stop_sequence": None, "usage": {**use, "output_tokens": 1}}}]
    for i, b in enumerate(blocks):
        if b[0] == "thinking":
            ev += [{"type": "content_block_start", "index": i, "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
                   {"type": "content_block_delta", "index": i, "delta": {"type": "signature_delta", "signature": b[1]}}]
        elif b[0] == "text":
            ev += [{"type": "content_block_start", "index": i, "content_block": {"type": "text", "text": ""}},
                   {"type": "content_block_delta", "index": i, "delta": {"type": "text_delta", "text": b[1]}}]
        else:
            ev += [{"type": "content_block_start", "index": i, "content_block": {"type": "tool_use", "id": b[1], "name": b[2], "input": {}}},
                   {"type": "content_block_delta", "index": i, "delta": {"type": "input_json_delta", "partial_json": json.dumps(b[3])}}]
        ev.append({"type": "content_block_stop", "index": i})
    ev += [{"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None}, "usage": {"output_tokens": 42}},
           {"type": "message_stop"}]
    return sse(ev)


class Wire:
    """A real anthropic client over httpx2.MockTransport. Records the exact URL, headers and JSON body sent."""

    def __init__(self, model, script):
        self.model, self.script, self.captured = model, list(script), []

    def handler(self, request):
        body = json.loads(request.content)
        self.captured.append({"url": str(request.url), "method": request.method,
                              "headers": {k.lower(): v for k, v in request.headers.items()}, "body": body})
        use = {"input_tokens": 100, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 5000}
        if not body.get("stream"):  # the pre-warm
            return httpx2.Response(200, headers={"request-id": "req_pre"}, json={
                "id": "msg_pre", "type": "message", "role": "assistant", "model": self.model, "content": [],
                "stop_reason": "max_tokens", "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 0, "cache_creation_input_tokens": 5000,
                          "cache_read_input_tokens": 0}})
        blocks, stop = self.script.pop(0)
        return httpx2.Response(200, headers={"content-type": "text/event-stream", "request-id": f"req_m{len(self.captured)}"},
                               content=stream_events(self.model, blocks, stop, use))

    def client(self, settings=None, **kw):
        return claude_loop.make_client("sk-ant-WIRE-KEY", settings, http_client=anthropic.DefaultHttpxClient(
            transport=httpx2.MockTransport(self.handler)), **kw)


def test_gateway_environment_is_ignored_and_the_key_stays_out_of_every_output(tmp_path, monkeypatch, capsys):
    root = tmp_path / "in"
    make_input(root, "a")
    secret = "sk-ant-GATEWAY-TEST-KEY"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:4000")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "gateway-token-123")
    monkeypatch.delenv("ANTHROPIC_CUSTOM_HEADERS", raising=False)
    wire = Wire(OPUS, [([("text", "FINAL")], "end_turn")])
    real_make = claude_loop.make_client
    # the real constructor (pinned URL, no env auth) with only the transport swapped for the recorder
    monkeypatch.setattr(claude_loop, "make_client", lambda key, settings=None, **kw: real_make(
        key, settings, http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(wire.handler))))
    out = tmp_path / "out"
    rc = claude_static.main([str(root), str(out), "--models", "opus", "--members", "1", "--cap-run", "5", "--prewarm"])
    cap = capsys.readouterr()
    assert rc == 0 and len(wire.captured) == 2
    for c in wire.captured:
        assert c["url"].startswith("https://api.anthropic.com/v1/messages")  # not the local gateway
        blob = json.dumps(c["headers"])
        assert "gateway-token-123" not in blob and "127.0.0.1" not in blob
        assert "authorization" not in c["headers"] or c["headers"]["authorization"] == f"Bearer {secret}"
    texts = cap.out + cap.err + "".join(p.read_text() for p in out.rglob("*") if p.is_file())
    for needle in (secret, "gateway-token-123"):
        assert needle not in texts
    # the real constructor pins the URL too (the patched one above only swaps the transport)
    c = real_make(secret)
    assert str(c.base_url).startswith("https://api.anthropic.com") and c.auth_token is None


def test_main_refuses_custom_headers_or_a_client_that_points_elsewhere(tmp_path, monkeypatch):
    root = tmp_path / "in"
    make_input(root, "a")
    argv = [str(root), str(tmp_path / "out"), "--models", "opus", "--cap-run", "5"]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    monkeypatch.setenv("ANTHROPIC_CUSTOM_HEADERS", "X-Gateway: 1")
    with pytest.raises(SystemExit, match="ANTHROPIC_CUSTOM_HEADERS"):
        claude_static.main(argv, client_factory=lambda s: FakeClient())
    monkeypatch.setenv("ANTHROPIC_CUSTOM_HEADERS", "")  # empty counts as unset
    elsewhere = FakeClient()
    elsewhere.base_url = "http://127.0.0.1:4000"
    with pytest.raises(SystemExit, match="base_url"):
        claude_static.main(argv, client_factory=lambda s: elsewhere)
    nourl = FakeClient()
    del nourl.base_url
    with pytest.raises(SystemExit, match="base_url"):
        claude_static.main(argv, client_factory=lambda s: nourl)
    assert not (tmp_path / "out" / "usage.jsonl").exists()  # nothing was spent or even opened


@pytest.mark.parametrize("model", [OPUS, HAIKU])
def test_real_sdk_wire_format_for_prewarm_first_call_and_second_call(model, tmp_path):
    paths = make_images(tmp_path, ["z_2.jpg", "z_0.jpg", "z_1.jpg", "z_4.jpg", "z_3.jpg", "z_5.jpg"])
    wire = Wire(model, [([("thinking", "SIGX"), ("text", "checking"), ("tool", "toolu_W1", "check_collision", FREE)],
                         "tool_use"), ([("text", "```yaml\nnodes: []\n```")], "end_turn")])
    client = wire.client()
    cb = author_tool.default_callback_factory()[0](YAML_TEXT)
    pre = claude_loop.prewarm(client, model, "PROMPT", YAML_TEXT, paths)
    rec = run_member(client, model, "PROMPT", YAML_TEXT, paths, cb)
    assert pre["cache_written"] and rec["status"] == "ok" and rec["final_text"].startswith("```yaml")
    assert len(wire.captured) == 3
    a, b, c = wire.captured
    tool = {"name": "check_collision", "description": "Checks collision for a box centered at (center_x, center_y, center_z).",
            "strict": True,
            "input_schema": {"type": "object", "additionalProperties": False,
                             "required": ["label", "center_x", "center_y", "center_z", "size_x", "size_y", "size_z"],
                             "properties": {"label": {"type": "string"}, **{k: {"type": "number"} for k in (
                                 "center_x", "center_y", "center_z", "size_x", "size_y", "size_z")}}}}
    by_name = {"z_2.jpg": 0, "z_0.jpg": 1, "z_1.jpg": 2, "z_4.jpg": 3, "z_3.jpg": 4, "z_5.jpg": 5}
    expect_data = [base64.b64encode(jpeg(by_name[n])).decode() for n in sorted(by_name)]
    for req in (a, b, c):
        assert req["method"] == "POST" and req["url"].split("?")[0] == "https://api.anthropic.com/v1/messages"
        h = req["headers"]
        assert h["anthropic-beta"] == "thinking-binding-controls-2026-08-01"  # exactly this one beta
        assert h["content-type"] == "application/json"
        assert "sk-ant-WIRE-KEY" in json.dumps(h)  # the key goes out only in the auth header ...
        assert json.dumps(h).count("sk-ant-WIRE-KEY") == 1  # ... and in one place
        body = req["body"]
        assert body["model"] == model
        assert body["thinking"] == {"type": "adaptive", "block_binding": {"prefix_mismatch_behavior": "error"}}
        assert body["output_config"] == {"effort": "medium"}
        assert body["tools"] == [tool] and body["tool_choice"] == {"type": "auto"}
        for banned in ("temperature", "top_p", "top_k", "seed", "fallbacks", "speed", "system", "metadata"):
            assert banned not in body
        first = body["messages"][0]
        assert first["role"] == "user"
        assert [x["type"] for x in first["content"]] == ["text", "text"] + ["image"] * 6
        assert first["content"][0]["text"] == "PROMPT" and first["content"][1]["text"] == YAML_TEXT
        imgs = first["content"][2:]
        assert [i["source"]["media_type"] for i in imgs] == ["image/jpeg"] * 6
        assert [i["source"]["type"] for i in imgs] == ["base64"] * 6
        assert [i["source"]["data"] for i in imgs] == expect_data  # sorted by file name
        marked = [i for i, blk in enumerate(first["content"]) if "cache_control" in blk]
        assert marked == [7] and first["content"][7]["cache_control"] == {"type": "ephemeral"}  # last image only
    # (a) the pre-warm: max_tokens 0, no stream, no top-level cache_control
    assert a["body"]["max_tokens"] == 0 and "stream" not in a["body"] and "cache_control" not in a["body"]
    assert set(a["body"]) == {"model", "max_tokens", "thinking", "output_config", "tools", "tool_choice", "messages"}
    assert len(a["body"]["messages"]) == 1
    # (b) first member call: streamed, top-level cache_control for the tail
    assert b["body"]["max_tokens"] == 64000 and b["body"]["stream"] is True
    assert b["body"]["cache_control"] == {"type": "ephemeral"}
    assert set(b["body"]) == {"model", "max_tokens", "thinking", "output_config", "tools", "tool_choice", "messages",
                              "stream", "cache_control"}
    assert b["body"]["messages"] == a["body"]["messages"]  # the pre-warm wrote exactly this prefix
    # (c) second call, after the tool use: history grew by two messages and nothing earlier changed
    msgs = c["body"]["messages"]
    assert json.dumps(msgs[0]) == json.dumps(b["body"]["messages"][0]) and len(msgs) == 3
    assert msgs[1] == {"role": "assistant", "content": [
        {"type": "thinking", "thinking": "", "signature": "SIGX"}, {"type": "text", "text": "checking"},
        {"type": "tool_use", "id": "toolu_W1", "name": "check_collision", "input": FREE}]}
    assert msgs[2]["role"] == "user" and [x["type"] for x in msgs[2]["content"]] == ["tool_result"]
    assert msgs[2]["content"][0]["tool_use_id"] == "toolu_W1" and "is_error" not in msgs[2]["content"][0]
    assert json.loads(msgs[2]["content"][0]["content"])["valid"] is True
    assert c["body"]["stream"] is True and c["body"]["cache_control"] == {"type": "ephemeral"}
    assert rec["request_ids"] == ["req_m2", "req_m3"] and rec["served_models"] == [model, model]
    assert rec["calls"][0]["usage"]["cache_read"] == 5000


def test_ipv4_flag_is_off_by_default_and_changes_only_the_transport():
    plain = claude_loop.make_client("sk-ant-x")
    v4 = claude_loop.make_client("sk-ant-x", ipv4=True)
    assert str(v4.base_url) == str(plain.base_url) and v4.timeout == plain.timeout
    assert isinstance(v4._client._transport, httpx2.HTTPTransport)
    assert claude_static.build_parser().parse_args(["i", "o"]).ipv4 is False


def test_main_refuses_a_live_run_without_caps_or_key(tmp_path, monkeypatch):
    root = tmp_path / "in"
    make_input(root, "a")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="cap"):
        claude_static.main([str(root), str(tmp_path / "o")])
    with pytest.raises(SystemExit, match="ANTHROPIC_API_KEY"):
        claude_static.main([str(root), str(tmp_path / "o"), "--cap-run", "1"])
    with pytest.raises(meter_mod.UnknownModel):
        claude_static.main([str(root), str(tmp_path / "o"), "--models", "gpt-9", "--dry-run"])


# ---- the author's feasibility function, and parity with his loop -------------------------------

def test_default_callback_calls_the_authors_own_function():
    feas = author_tool.load_author_feasibility()
    src = author_tool.DEFAULT_AUTHOR_SOURCE.read_text()
    node = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "validate_feasibility")
    assert feas.sha256 == hashlib.sha256(ast.get_source_segment(src, node).encode()).hexdigest()
    cb = author_tool.make_author_callback(YAML_TEXT, feas.fn)
    hit = cb("check_collision", COLLIDING)
    assert hit["valid"] is False and hit["collision_count"] == 1 and hit["collisions"][0]["name"] == "Table"
    assert cb("check_collision", FREE)["valid"] is True
    ints = {**FREE, "center_x": 3, "size_x": 1}  # Claude may send integers; they go to his function as sent
    pos = cb("check_collision", ints)["position"]
    assert pos == [3, 3.0, 0.5] and isinstance(pos[0], int)
    assert cb("nope", {}) == {"error": "Unknown function nope"}
    assert cb("check_collision", {"label": "x"})["error"].startswith("check_collision missing argument(s): center_x")


def test_tool_definition_matches_the_authors_code():
    sig = author_tool.author_tool_signature()
    assert sig["args"] == list(author_tool.ARG_NAMES) == sig["required_args"]
    assert sig["doc"] == author_tool.CHECK_COLLISION_DESCRIPTION
    props = author_tool.TOOL_DEF["input_schema"]["properties"]
    for name, ann in sig["annotations"].items():
        assert props[name]["type"] == ("string" if ann == "str" else "number")


def test_author_module_does_not_import_here_and_report_says_why():
    report = author_tool.author_import_report()
    assert report["numpy"] is True and report["yaml"] is True
    assert report["spark_dsg"] is False and report["scene_graph_visualize_2d"] is False
    with pytest.raises(ModuleNotFoundError):
        spec = importlib.util.spec_from_file_location("author_plain_import", author_tool.DEFAULT_AUTHOR_SOURCE)
        spec.loader.exec_module(importlib.util.module_from_spec(spec))


class _Part:
    state = None

    def __init__(self, text=None, function_call=None, **kw):
        self.text, self.function_call = text, function_call
        self.__dict__.update(kw)

    @staticmethod
    def from_text(text):
        return _Part(text=text, kind="text")

    @staticmethod
    def from_bytes(data, mime_type):
        return _Part(kind="bytes", data=data, mime_type=mime_type)

    @staticmethod
    def from_function_response(name, response):
        _Part.state["responses"].append((name, response))
        return _Part(kind="fn_response", name=name)


def _genai_reply(text, calls):
    parts = ([_Part(text=text)] if text else []) + [
        _Part(function_call=SimpleNamespace(name=n, args=a)) for n, a in calls]
    return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=parts))], text=text)


def run_author_loop(monkeypatch, tmp_path, script, prompt, yaml_text, image_dir):
    """Drive the author's real generate_completion_response with a scripted fake of google.genai."""
    state = {"responses": [], "sent": [], "script": list(script), "chat_configs": []}
    _Part.state = state

    class Chat:
        def send_message(self, contents):
            state["sent"].append(contents)
            item = state["script"].pop(0)
            return _genai_reply(item.get("text"), item.get("calls", []))

    class Client:
        def __init__(self, api_key=None):
            self.chats = SimpleNamespace(create=lambda model, config, history: (state["chat_configs"].append(config), Chat())[1])

    google, genai, gtypes = types.ModuleType("google"), types.ModuleType("google.genai"), types.ModuleType("google.genai.types")
    google.__path__ = []
    genai.types, google.genai, genai.Client = gtypes, genai, Client
    gtypes.Part = _Part
    for n in ("GenerateContentConfig", "AutomaticFunctionCallingConfig", "ThinkingConfig", "ToolConfig",
              "FunctionCallingConfig"):
        setattr(gtypes, n, lambda **kw: SimpleNamespace(**kw))
    spark, spark_nx = types.ModuleType("spark_dsg"), types.ModuleType("spark_dsg.networkx")
    spark.networkx = spark_nx
    bidict_mod = types.ModuleType("bidict")
    bidict_mod.bidict = dict
    sgv = types.ModuleType("scene_graph_visualize_2d")
    sgv.create_scene_slices = lambda *a, **k: None
    for name, mod in {"google": google, "google.genai": genai, "google.genai.types": gtypes, "spark_dsg": spark,
                      "spark_dsg.networkx": spark_nx, "bidict": bidict_mod, "scene_graph_visualize_2d": sgv}.items():
        monkeypatch.setitem(sys.modules, name, mod)
    spec = importlib.util.spec_from_file_location("author_llm_completion_under_test", author_tool.DEFAULT_AUTHOR_SOURCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    yaml_path = tmp_path / "graph.yaml"
    yaml_path.write_text(yaml_text)
    worker = mod.LLMCompletion(str(tmp_path), None, "fake-model", prompt, 1)
    text = worker.generate_completion_response(str(yaml_path), str(image_dir))
    return text, state


REAL_GRAPH = Path("/Users/sher/project/cvp/replay_inputs/smoke_inputs/smoke_00871_s44_official_st17/graph.yaml")


@pytest.fixture
def real_graph():
    if not REAL_GRAPH.exists():
        pytest.skip("smoke graph not present")
    import yaml as _yaml
    text = REAL_GRAPH.read_text()  # read only
    nodes = [n for n in _yaml.safe_load(text)["nodes"] if n.get("node_type") in ("object", "structure")]
    assert len(nodes) > 20
    return text, nodes


def _vec(v):
    return json.loads(v) if isinstance(v, str) else v


def real_boxes(nodes):
    """Boxes made from the real graph. Integers on purpose: the author's loop gets whatever type the model sends,
    and the comparison below is exact, so a silent int-to-float change would show."""
    n = nodes[0]
    px, py, pz = _vec(n["position"])
    on_node = {"label": "OnFirst", "center_x": px, "center_y": py, "center_z": pz, "size_x": 1, "size_y": 1, "size_z": 1}
    huge = {"label": "Huge", "center_x": int(px), "center_y": int(py), "center_z": 1, "size_x": 30, "size_y": 30, "size_z": 30}
    far = {"label": "Far", "center_x": 5000, "center_y": 5000, "center_z": 5000, "size_x": 1, "size_y": 1, "size_z": 1}
    return on_node, huge, far


def claude_side(script, paths, yaml_text, max_turns=50):
    """Same logical script, as Claude replies; our loop with the default (author) callback."""
    replies = [reply(*([("text", s["text"])] if s.get("text") else []),
                     *[("tool", n, a, f"toolu_{i}_{j}") for j, (n, a) in enumerate(s.get("calls", []))])
               for i, s in enumerate(script)]
    client = FakeClient(replies)
    cb = author_tool.default_callback_factory()[0](yaml_text)
    rec = run_member(client, OPUS, "AUTHOR PROMPT", yaml_text, paths, cb, LoopSettings(max_turns=max_turns))
    return rec, client


def parity_scripts(nodes):
    on_node, huge, far = real_boxes(nodes)
    return {
        "text_only": [{"text": "```yaml\nnodes: []\n```"}],
        "one_call": [{"calls": [("check_collision", on_node)]}, {"text": "final A"}],
        "parallel_and_errors": [
            {"text": "thinking out loud", "calls": [("check_collision", on_node), ("check_collision", far)]},
            {"calls": [("check_collision", huge), ("unknown_tool", {"a": 1})]},
            {"calls": [("check_collision", {"label": "x", "center_x": 1})]},
            {"calls": [("check_collision", {**far, "label": "Rug", "size_z": 0.01})]},
            {"text": "final B\nmore"},
        ],
    }


@pytest.mark.parametrize("name", ["text_only", "one_call", "parallel_and_errors"])
def test_parity_with_the_authors_loop_on_scripted_replies(name, monkeypatch, tmp_path, real_graph):
    yaml_text, nodes = real_graph
    script = parity_scripts(nodes)[name]
    paths = make_images(tmp_path)
    a_text, a_state = run_author_loop(monkeypatch, tmp_path, script, "AUTHOR PROMPT", yaml_text, tmp_path / "slices")
    rec, client = claude_side(script, paths, yaml_text)
    mine = [(t["name"], json.dumps(t["result"])) for t in rec["tool_calls"]]
    theirs = [(n, json.dumps(r)) for n, r in a_state["responses"]]
    assert mine == theirs  # exact: same names, same keys in the same order, same numbers, ints stay ints
    assert len(mine) == sum(len(s.get("calls", [])) for s in script)
    assert rec["final_text"] == a_text == script[-1]["text"]
    # on the wire the tool result is that same JSON text
    wire = [b["content"] for req in client.requests[1:] for b in req["messages"][-1]["content"]
            if b["type"] == "tool_result"]
    assert wire == [j for _, j in mine]
    if name == "parallel_and_errors":
        results = [json.loads(j) for _, j in mine]
        assert results[0]["valid"] is False and results[0]["collisions"]  # real collisions on the real graph
        assert results[1]["valid"] is True
        assert results[2]["collision_count"] > 1  # the huge box meets many nodes
        assert results[3] == {"error": "Unknown function unknown_tool"}
        assert results[4]["error"].startswith("check_collision missing argument(s)")
        assert results[0]["position"][0] == _vec(nodes[0]["position"])[0]
        assert results[2]["position"] == [int(_vec(nodes[0]["position"])[0]), int(_vec(nodes[0]["position"])[1]), 1]
        assert isinstance(results[2]["position"][2], int)  # an integer went in, an integer came out
    # same first message: prompt, YAML, same images (his order is the file system's; ours is sorted)
    sent = a_state["sent"][0]
    assert sent[0] == "AUTHOR PROMPT" and sent[1].text == yaml_text
    assert sorted(p.data for p in sent[2:]) == sorted(
        base64.b64decode(b["source"]["data"]) for b in client.requests[0]["messages"][0]["content"][2:])
    assert client.requests[0]["messages"][0]["content"][1]["text"] == yaml_text
    # his config: temperature 0.2, dynamic thinking. Ours cannot copy those.
    cfg = a_state["chat_configs"][0]
    assert cfg.temperature == 0.2 and cfg.thinking_config.thinking_budget == -1


def test_parity_turn_limit_same_tool_calls_and_no_text(monkeypatch, tmp_path, real_graph):
    yaml_text, nodes = real_graph
    _, huge, far = real_boxes(nodes)
    paths = make_images(tmp_path)
    script = [{"calls": [("check_collision", {**(huge if i % 2 else far), "label": f"L{i}"})]} for i in range(60)]
    a_text, a_state = run_author_loop(monkeypatch, tmp_path, script, "AUTHOR PROMPT", yaml_text, tmp_path / "slices")
    rec, client = claude_side(script, paths, yaml_text)
    assert a_text is None and rec["final_text"] is None and rec["status"] == "dropped_turn_limit"
    mine = [(t["name"], json.dumps(t["result"])) for t in rec["tool_calls"]]
    theirs = [(n, json.dumps(r)) for n, r in a_state["responses"]]
    assert len(mine) == len(theirs) == 50 and mine == theirs
    # his loop makes one more call (the 51st) and throws the reply away; ours does not make it
    assert len(a_state["sent"]) == 51 and len(client.calls) == 50
