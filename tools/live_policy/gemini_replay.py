"""Replay Gemini on saved replay inputs, through the author's own tool loop.

The rules are in PREREGISTRATION_GEMINI.md. It is October's gemini_static.py with three changes: the
inputs are the folders exported for the Claude replays (the same bytes Claude saw), rows run one at a
time in a given order, and a row starts only if the cap leaves room for all its members.

Runs inside the container, where the author's code and google-genai live:

    ASP_LLM_PROVIDER=google ASP_LLM_LOG_DIR=<out_dir>/llm_log ASP_LLM_MAX_CALLS=20000 \
    python -B gemini_replay.py <inputs_dir> <out_dir> <cap_usd> <rows_file> --model gemini-2.5-pro \
        [--members 4] [--admit 1.4]

    <inputs_dir>/<row_id>/   prompt.txt, graph.yaml, slices/*.jpg, meta.json (sha256 of each file)
    <rows_file>              one row id per line, in running order; lines that start with # are skipped
    <out_dir>/<row_id>/      gemini_new_graph_<k>.yaml, response_<k>.txt, row.json
    <out_dir>/gemini_calls.jsonl   one line per call; its sum is the spend the cap is checked against

Every run that shares a cap must share one <out_dir>: the ledger is read at the start, so a smoke test
and the rounds after it count against the same cap. A row whose row.json says "done" is not run again.

The cap is enforced before every call, from the usage the API reports, at the list prices in PRICES
(read from the public price page on 2026-11-19): thoughts are billed as output, and tokens the API
reports as cached are billed at the cache price. The key is read from
/workspace/.cvp-secrets/gemini-auth-key by this process and is never printed.

A call that fails with HTTP 429, a 5xx code, a timeout or a broken connection is tried again after
60 s, up to 3 times. The replay stops, and no call is made after it, on HTTP 402, on any other reply
that names prepaid credit or billing, when one call has failed its third retry, and when a member's
call fails for another reason before that member has had one good call (a fault of the set-up, such
as a model the key may not use: it would otherwise mark every row done with all its members dropped).
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

SCRIPTS = "/workspace/catkin_ws/src/active_semantic_perception/exploration/scripts"
KEY_FILE = "/workspace/.cvp-secrets/gemini-auth-key"
# USD per million tokens: (input, cached input, output). 2.5 Pro has a second tier for prompts over 200k tokens.
PRICES = {
    "gemini-2.5-pro": {"small": (1.25, 0.125, 10.0), "large": (2.50, 0.25, 15.0), "large_over": 200000},
    "gemini-3.8-flash": {"small": (0.75, 0.075, 3.75)},
    "gemini-4-argon": {"small": (2.00, 0.10, 10.0)},      # through 2026-11-30
    "gemini-4-neon": {"small": (3.00, 0.15, 15.0)},
}
RESERVE_USD = 0.08
OBSERVED = "habitat_scene_graph_original_graph0.yaml"
BILLING_WORDS = ("billing", "credit", "prepay", "payment required", "payment_required")
NETWORK_WORDS = ("timeout", "timedout", "connecterror", "connectionerror", "readerror", "writeerror",
                 "remoteprotocolerror", "connection reset", "connection aborted", "temporarily unavailable")
RETRIES = 3
RETRY_WAIT_S = 60


class CapReached(RuntimeError):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def classify(exc):
    """What a failed call means: "stop" (the credit is used up), "retry" (HTTP 429 or 5xx, a timeout
    or a broken connection) or "drop". The HTTP code decides first: a rate limit's text also names
    billing."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code == 402:
        return "stop"
    if code == 429 or (isinstance(code, int) and 500 <= code <= 599):
        return "retry"
    text = (type(exc).__name__ + " " + repr(exc)).lower()
    if any(w in text for w in BILLING_WORDS):
        return "stop"
    if not isinstance(code, int) and any(w in text for w in NETWORK_WORDS):
        return "retry"
    return "drop"


def call_cost(model, prompt, cached, candidates, thoughts):
    """List price of one call. `prompt` includes the cached tokens."""
    table = PRICES[model]
    tier = "large" if prompt > table.get("large_over", float("inf")) else "small"
    p_in, p_cache, p_out = table[tier]
    cached = min(max(cached, 0), prompt)
    return ((prompt - cached) * p_in + cached * p_cache + (candidates + thoughts) * p_out) / 1e6


def read_rows(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                rows.append(line.split()[0])
    return rows


def check_inputs(src):
    """The input folder must hold the bytes its meta.json lists. Returns (meta, prompt text)."""
    with open(os.path.join(src, "meta.json")) as f:
        meta = json.load(f)
    problems = []
    if sha256_file(os.path.join(src, "graph.yaml")) != meta["graph_sha256"]:
        problems.append("graph.yaml")
    if sha256_file(os.path.join(src, "prompt.txt")) != meta["prompt_sha256"]:
        problems.append("prompt.txt")
    names = sorted(os.listdir(os.path.join(src, "slices")))
    if names != sorted(s["name"] for s in meta["slices"]):
        problems.append("slices (names)")
    for s in meta["slices"]:
        p = os.path.join(src, "slices", s["name"])
        if not os.path.isfile(p) or sha256_file(p) != s["sha256"]:
            problems.append("slices/" + s["name"])
    if problems:
        raise ValueError("input does not match its meta.json: " + ", ".join(problems))
    with open(os.path.join(src, "prompt.txt")) as f:
        return meta, f.read()


class Meter:
    """Spend, the cap, and the ledger. One lock for all of it."""

    def __init__(self, out_root, cap, model="gemini-2.5-pro"):
        self.cap = float(cap)
        self.model = model
        self.lock = threading.Lock()
        self.local = threading.local()
        self.path = os.path.join(out_root, "gemini_calls.jsonl")
        self.spent = 0.0
        self.calls = 0
        self.reserved = 0.0
        self.stopped = None            # None, "cap", "billing", "retries" or "setup"
        self.by_member = {}            # (row, member) -> [cost, calls]
        self.good = {}                 # (row, member) -> calls that returned
        if os.path.exists(self.path):
            with open(self.path) as f:
                for line in f:
                    if line.strip():
                        self.spent += float(json.loads(line).get("cost", 0.0))
                        self.calls += 1
        self.ledger = open(self.path, "a")

    def tag(self, row, member):
        self.local.key = (row, member)

    def room_for(self, members, admit):
        with self.lock:
            return self.stopped is None and self.spent + self.reserved + members * admit <= self.cap

    def wrap(self, inner):
        meter = self

        def attempt(client_self, args, kwargs, key, retry):
            """One try of one call. Returns (response, None) or (None, the exception)."""
            with meter.lock:
                if meter.stopped or meter.spent + meter.reserved + RESERVE_USD > meter.cap:
                    meter.stopped = meter.stopped or "cap"
                    raise CapReached("stopped (%s): spent %.4f of %.2f" % (meter.stopped, meter.spent, meter.cap))
                meter.reserved += RESERVE_USD
            t0 = time.time()
            cost = RESERVE_USD     # charged if the call raises: it may still be billed
            rec = {"ts": t0, "row": key[0], "member": key[1]}
            if retry:
                rec["retry"] = retry
            resp, err = None, None
            try:
                resp = inner(client_self, *args, **kwargs)
                um = getattr(resp, "usage_metadata", None)
                p = int(getattr(um, "prompt_token_count", 0) or 0) + int(getattr(um, "tool_use_prompt_token_count", 0) or 0)
                ca = int(getattr(um, "cached_content_token_count", 0) or 0)
                c = int(getattr(um, "candidates_token_count", 0) or 0)
                th = int(getattr(um, "thoughts_token_count", 0) or 0)
                if um is not None:
                    cost = call_cost(meter.model, p, ca, c, th)
                rec.update({"latency_s": round(time.time() - t0, 2), "prompt": p, "cached": ca, "candidates": c, "thoughts": th})
                with meter.lock:
                    meter.good[key] = meter.good.get(key, 0) + 1
            except Exception as e:
                err = e
                rec["error"] = repr(e)[:300]
                code = getattr(e, "code", None) or getattr(e, "status_code", None)
                if code in (402, 429):
                    cost = 0.0     # a refused call is not billed
            rec["cost"] = cost
            with meter.lock:
                meter.reserved -= RESERVE_USD
                meter.spent += cost
                meter.calls += 1
                m = meter.by_member.setdefault(key, [0.0, 0])
                m[0] += cost
                m[1] += 1
                meter.ledger.write(json.dumps(rec) + "\n")
                meter.ledger.flush()
            return resp, err

        def capped(client_self, *args, **kwargs):
            key = getattr(meter.local, "key", ("?", -1))
            retry = 0
            while True:
                resp, err = attempt(client_self, args, kwargs, key, retry)
                if err is None:
                    return resp
                what = classify(err)
                if what == "retry" and retry < RETRIES:
                    retry += 1
                    time.sleep(RETRY_WAIT_S)
                    continue
                with meter.lock:
                    if what == "stop":                 # the credit is used up
                        meter.stopped = meter.stopped or "billing"
                    elif what == "retry":              # the third retry failed
                        meter.stopped = meter.stopped or "retries"
                    elif not meter.good.get(key):      # refused before this member had one good call
                        meter.stopped = meter.stopped or "setup"
                raise err

        return capped


def run_member(lc, meter, work, prompt, row, member, seed):
    """One member: the author's loop, then his parser. Ends as ok, dropped_parse, dropped_error or stopped."""
    meter.tag(row, member)
    observed = os.path.join(work, OBSERVED)
    t0 = time.time()
    out = {"member": member, "seed": seed}
    try:
        worker = lc.LLMCompletion(base_path=work, file_to_analyze=None, model_name=meter.model, user_prompt=prompt, seed=seed)
        text = worker.generate_completion_response(observed, os.path.join(work, "input_slices"))
        with open(os.path.join(work, "response_%d.txt" % member), "w") as f:
            f.write(text if isinstance(text, str) else repr(text))
        ok = bool(worker.parse_response(text, observed, "gemini_new_graph_%d.yaml" % member))
        out["end"] = "ok" if ok else "dropped_parse"
    except CapReached as e:
        out.update({"end": "stopped", "error": repr(e)[:300]})
    except Exception as e:
        out.update({"end": "stopped" if meter.stopped else "dropped_error", "error": repr(e)[:300]})
    if out["end"] != "ok" and meter.stopped:
        out["end"] = "stopped"         # a member that fails while the replay is stopping was cut short, not dropped
    cost, calls = meter.by_member.get((row, member), [0.0, 0])
    out.update({"ok": out["end"] == "ok", "wall_s": round(time.time() - t0, 1), "cost": round(cost, 6), "calls": calls})
    return out


def run_row(lc, meter, inputs_dir, out_root, row, members):
    src = os.path.join(inputs_dir, row)
    meta, prompt = check_inputs(src)
    work = os.path.join(out_root, row)
    slices = os.path.join(work, "input_slices")
    if os.path.isdir(work):
        shutil.rmtree(work)            # a row cut short starts clean; its calls stay in the ledger
    os.makedirs(slices)
    shutil.copy(os.path.join(src, "graph.yaml"), os.path.join(work, OBSERVED))
    for s in meta["slices"]:
        shutil.copy(os.path.join(src, "slices", s["name"]), os.path.join(slices, s["name"]))
    seed0 = int(meta.get("config_seed", meta.get("seed", 42)))
    with ThreadPoolExecutor(members) as pool:
        results = list(pool.map(lambda m: run_member(lc, meter, work, prompt, row, m, seed0 + m), range(members)))
    done = all(r["end"] != "stopped" for r in results)
    rec = {"row": row, "run": meta.get("run"), "stage": meta.get("stage"), "model": meter.model, "members": results,
           "done": done, "spent_after": round(meter.spent, 4)}
    with open(os.path.join(work, "row.json"), "w") as f:
        json.dump(rec, f, indent=1)
    return rec


def row_done(out_root, row):
    p = os.path.join(out_root, row, "row.json")
    if not os.path.isfile(p):
        return False
    with open(p) as f:
        return bool(json.load(f).get("done"))


def replay(lc, meter, inputs_dir, out_root, rows, members, admit):
    """Rows in order. Returns the summary dict. `admit` grows to the dearest member seen."""
    summary = {"rows": [], "skipped_done": [], "not_started": [], "stop": None, "model": meter.model}
    for i, row in enumerate(rows):
        if row_done(out_root, row):
            summary["skipped_done"].append(row)
            continue
        if not meter.room_for(members, admit):
            summary["stop"] = meter.stopped or "cap_before_row"
            summary["not_started"] = [r for r in rows[i:] if not row_done(out_root, r)]
            break
        rec = run_row(lc, meter, inputs_dir, out_root, row, members)
        summary["rows"].append(rec)
        print(json.dumps({"row": row, "done": rec["done"], "ends": [m["end"] for m in rec["members"]],
                          "costs": [m["cost"] for m in rec["members"]], "spent": rec["spent_after"]}), flush=True)
        admit = max([admit] + [m["cost"] for m in rec["members"]])
        if meter.stopped:
            summary["stop"] = meter.stopped
            summary["not_started"] = [r for r in rows[i + 1:] if not row_done(out_root, r)]
            break
    summary.update({"spent_usd": round(meter.spent, 4), "calls": meter.calls, "cap": meter.cap, "admit_end": round(admit, 4)})
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs_dir")
    ap.add_argument("out_dir")
    ap.add_argument("cap_usd", type=float)
    ap.add_argument("rows_file")
    ap.add_argument("--model", required=True, choices=sorted(PRICES))
    ap.add_argument("--members", type=int, default=4)
    ap.add_argument("--admit", type=float, default=1.4, help="cost per member assumed before any is measured")
    a = ap.parse_args(argv)

    os.makedirs(a.out_dir, exist_ok=True)
    if os.environ.get("ASP_LLM_PROVIDER") != "google" or not os.environ.get("ASP_LLM_LOG_DIR", "").startswith(a.out_dir):
        sys.exit("set ASP_LLM_PROVIDER=google and ASP_LLM_LOG_DIR=<out_dir>/... before starting python")
    rows = read_rows(a.rows_file)
    need = 150 * a.members * len(rows)   # the container's call logger stops a process at ASP_LLM_MAX_CALLS (500 if unset)
    if int(os.environ.get("ASP_LLM_MAX_CALLS", "0") or 0) < need:
        sys.exit("set ASP_LLM_MAX_CALLS to at least %d before starting python" % need)
    missing = [r for r in rows if not os.path.isfile(os.path.join(a.inputs_dir, r, "meta.json"))]
    if missing or len(set(rows)) != len(rows):
        sys.exit("rows file names inputs that are missing or repeated: %s" % (missing or "repeated row"))
    for r in rows:                      # every input is checked before the first call
        check_inputs(os.path.join(a.inputs_dir, r))
    with open(KEY_FILE) as f:
        os.environ["GOOGLE_API_KEY"] = f.read().strip()
    sys.path.insert(0, SCRIPTS)
    from google.genai import models as genai_models
    import llm_completion as lc

    meter = Meter(a.out_dir, a.cap_usd, a.model)
    genai_models.Models.generate_content = meter.wrap(genai_models.Models.generate_content)
    summary = replay(lc, meter, a.inputs_dir, a.out_dir, rows, a.members, a.admit)
    with open(os.path.join(a.out_dir, "summary_%s.json" % time.strftime("%Y%m%dT%H%M%S")), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps({k: summary[k] for k in ("spent_usd", "calls", "cap", "stop", "not_started", "skipped_done")}))


if __name__ == "__main__":
    main()
