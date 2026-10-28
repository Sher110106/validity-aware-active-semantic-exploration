"""Tests for the 2026-10-28 shim additions: metering, cost cap, hard pin,
timeout and retry backoff. Defaults must keep the matrix-run behaviour."""
import importlib.util
import json
import os
import sys

import pytest

SHIM_PATH = os.path.join(os.path.dirname(__file__), "..", "legacy", "asp_openrouter_shim.py")


def _load_shim():
    spec = importlib.util.spec_from_file_location("asp_openrouter_shim_under_test", SHIM_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


shim = _load_shim()


class _Resp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body


def _ok_body(cost=0.001, text="done", tool_calls=None):
    return {
        "id": "gen-1",
        "provider": "DeepInfra",
        "model": "deepseek/deepseek-v4.1-flash-1017",
        "choices": [{"finish_reason": "stop", "message": {"content": text, "tool_calls": tool_calls}}],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "cost": cost,
            "prompt_tokens_details": {"cached_tokens": 80},
            "completion_tokens_details": {"reasoning_tokens": 5},
        },
    }


@pytest.fixture
def captured(monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"payload": json, "timeout": timeout})
        return _Resp(200, _ok_body())

    monkeypatch.setattr(shim.requests, "post", fake_post)
    for var in (
        "ASP_LLM_LOG_DIR",
        "ASP_OPENROUTER_MAX_COST_USD",
        "ASP_OPENROUTER_ALLOW_FALLBACKS",
        "ASP_OPENROUTER_TIMEOUT_S",
        "ASP_OPENROUTER_RETRY_BACKOFF_S",
        "ASP_OPENROUTER_PROVIDER_ORDER",
        "ASP_OPENROUTER_QUANTIZATIONS",
        "ASP_OPENROUTER_RESERVE_USD",
        "ASP_OPENROUTER_TOTAL_TIMEOUT_S",
    ):
        monkeypatch.delenv(var, raising=False)
    return calls


def test_defaults_match_matrix_behaviour(captured, monkeypatch):
    monkeypatch.setenv("ASP_OPENROUTER_PROVIDER_ORDER", "deepinfra/fp8")
    shim._openrouter_generate_content_once(["hi"], None, "k")
    call = captured[0]
    assert call["timeout"] == 180.0
    assert call["payload"]["provider"]["allow_fallbacks"] is True
    assert "usage" not in call["payload"]


def test_hard_pin_and_timeout_from_env(captured, monkeypatch):
    monkeypatch.setenv("ASP_OPENROUTER_PROVIDER_ORDER", "deepinfra/fp8")
    monkeypatch.setenv("ASP_OPENROUTER_QUANTIZATIONS", "fp8")
    monkeypatch.setenv("ASP_OPENROUTER_ALLOW_FALLBACKS", "0")
    monkeypatch.setenv("ASP_OPENROUTER_TIMEOUT_S", "600")
    shim._openrouter_generate_content_once(["hi"], None, "k")
    call = captured[0]
    assert call["timeout"] == 600.0
    assert call["payload"]["provider"] == {
        "require_parameters": True,
        "order": ["deepinfra/fp8"],
        "allow_fallbacks": False,
        "quantizations": ["fp8"],
    }


def test_usage_logged_and_cost_accumulates(captured, monkeypatch, tmp_path):
    monkeypatch.setenv("ASP_LLM_LOG_DIR", str(tmp_path))
    shim._openrouter_generate_content_once(["hi"], None, "k")
    shim._openrouter_generate_content_once(["hi"], None, "k")
    assert captured[0]["payload"]["usage"] == {"include": True}
    lines = [json.loads(l) for l in (tmp_path / "usage.jsonl").read_text().splitlines()]
    assert len(lines) == 2
    assert lines[0]["provider"] == "DeepInfra"
    assert lines[0]["cached_tokens"] == 80
    assert lines[0]["reasoning_tokens"] == 5
    assert lines[1]["run_cost_usd"] == pytest.approx(0.002)
    assert float((tmp_path / "_cost_usd").read_text()) == pytest.approx(0.002)


def test_non_200_is_logged_with_zero_cost(monkeypatch, tmp_path, captured):
    monkeypatch.setattr(shim.requests, "post", lambda *a, **k: _Resp(429, {"error": "rate"}))
    monkeypatch.setenv("ASP_LLM_LOG_DIR", str(tmp_path))
    with pytest.raises(RuntimeError):
        shim._openrouter_generate_content_once(["hi"], None, "k")
    line = json.loads((tmp_path / "usage.jsonl").read_text())
    assert line["status"] == 429 and line["cost"] == 0.0


def test_cost_cap_blocks_call_and_sets_flag(captured, monkeypatch, tmp_path):
    monkeypatch.setenv("ASP_LLM_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("ASP_OPENROUTER_MAX_COST_USD", "0.0024")
    monkeypatch.setenv("ASP_OPENROUTER_RESERVE_USD", "0.0005")
    shim._openrouter_generate_content_once(["hi"], None, "k")  # spends 0.001
    shim._openrouter_generate_content_once(["hi"], None, "k")  # 0.001 + 0.0005 <= cap, allowed
    with pytest.raises(shim.CostCapExceeded):
        shim._openrouter_generate_content_once(["hi"], None, "k")  # 0.002 + 0.0005 > 0.0024
    assert len(captured) == 2
    assert (tmp_path / "_cost_cap_reached").exists()
    assert float((tmp_path / "_reserved_usd").read_text()) == pytest.approx(0.0)


def test_concurrent_reservations_count_against_the_cap(captured, monkeypatch, tmp_path):
    monkeypatch.setenv("ASP_LLM_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("ASP_OPENROUTER_MAX_COST_USD", "0.035")
    monkeypatch.setenv("ASP_OPENROUTER_RESERVE_USD", "0.01")
    held = [shim._reserve_budget(), shim._reserve_budget(), shim._reserve_budget()]  # 3 in flight
    with pytest.raises(shim.CostCapExceeded):
        shim._reserve_budget()
    assert held == [0.01, 0.01, 0.01]
    shim._record_usage(200, 1.0, _ok_body(cost=0.002), 0.01)
    assert float((tmp_path / "_reserved_usd").read_text()) == pytest.approx(0.02)
    assert shim._reserve_budget() == 0.01  # 0.002 spent + 0.02 held + 0.01 <= 0.035


def test_missing_cost_and_exceptions_fail_closed(monkeypatch, tmp_path, captured):
    monkeypatch.setenv("ASP_LLM_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("ASP_OPENROUTER_MAX_COST_USD", "1")
    monkeypatch.setenv("ASP_OPENROUTER_RESERVE_USD", "0.01")
    body = _ok_body()
    del body["usage"]["cost"]
    monkeypatch.setattr(shim.requests, "post", lambda *a, **k: _Resp(200, body))
    shim._openrouter_generate_content_once(["hi"], None, "k")

    def boom(*a, **k):
        raise shim.requests.exceptions.ReadTimeout("slow")

    monkeypatch.setattr(shim.requests, "post", boom)
    with pytest.raises(shim.requests.exceptions.ReadTimeout):
        shim._openrouter_generate_content_once(["hi"], None, "k")
    lines = [json.loads(l) for l in (tmp_path / "usage.jsonl").read_text().splitlines()]
    assert [l["cost"] for l in lines] == [0.01, 0.01]
    assert lines[0]["cost_known"] is False and lines[1]["status"] == "exception"
    assert float((tmp_path / "_cost_usd").read_text()) == pytest.approx(0.02)
    assert float((tmp_path / "_reserved_usd").read_text()) == pytest.approx(0.0)


def test_cost_cap_gives_up_without_retry(captured, monkeypatch, tmp_path):
    monkeypatch.setenv("ASP_LLM_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("ASP_OPENROUTER_MAX_COST_USD", "0")
    resp = shim.openrouter_generate_content(["hi"], None, "k")
    assert resp.text == ""
    assert captured == []


def test_retry_backoff_sleeps_between_attempts(monkeypatch, captured):
    import time as time_mod

    sleeps = []
    monkeypatch.setattr(time_mod, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(shim.requests, "post", lambda *a, **k: _Resp(500, {"error": "x"}))
    monkeypatch.setenv("ASP_OPENROUTER_RETRY_BACKOFF_S", "5")
    resp = shim.openrouter_generate_content(["hi"], None, "k")
    assert resp.text == ""
    assert sleeps == [5.0, 10.0]


def test_total_deadline_abandons_a_hung_request(monkeypatch, tmp_path, captured):
    import threading

    release = threading.Event()

    def hang(*a, **k):
        release.wait(5)
        return _Resp(200, _ok_body())

    monkeypatch.setattr(shim.requests, "post", hang)
    monkeypatch.setenv("ASP_LLM_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("ASP_OPENROUTER_TOTAL_TIMEOUT_S", "0.2")
    with pytest.raises(shim.RequestDeadlineExceeded):
        shim._openrouter_generate_content_once(["hi"], None, "k")
    release.set()
    line = json.loads((tmp_path / "usage.jsonl").read_text())
    assert line["status"] == "exception" and line["cost"] > 0  # charged: it may still be billed


def test_total_deadline_passes_normal_responses(monkeypatch, captured):
    monkeypatch.setenv("ASP_OPENROUTER_TOTAL_TIMEOUT_S", "5")
    resp = shim._openrouter_generate_content_once(["hi"], None, "k")
    assert resp.text == "done"
