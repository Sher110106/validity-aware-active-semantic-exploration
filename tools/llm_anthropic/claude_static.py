"""Replay saved scene-graph inputs through Claude with the author's tool loop.

    ANTHROPIC_API_KEY=... python tools/llm_anthropic/claude_static.py INPUTS_DIR OUT_DIR \
        --models haiku,opus --members 4 --cap-model opus=280 --cap-model haiku=20 --cap-campaign 330 \
        --order order.txt --resume --prewarm

    python tools/llm_anthropic/claude_static.py INPUTS_DIR OUT_DIR --dry-run     # builds requests, calls nothing

Input folder (one per input, the folder name is the input id):
    prompt.txt   graph.yaml   slices/*.jpg (6 JPEGs)   meta.json {"run":..,"scene":..,"stage":..,"track":..}
Output: OUT_DIR/<model>/<input>/member_<k>/{record.json, final.txt}, OUT_DIR/usage.jsonl, OUT_DIR/summary.json
The key is read from ANTHROPIC_API_KEY at run time. It is never printed or written.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

if __package__ in (None, ""):  # run as a script: make `llm_anthropic` importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm_anthropic import claude_loop, meter as meter_mod  # noqa: E402
from llm_anthropic.author_tool import (  # noqa: E402
    DEFAULT_AUTHOR_SOURCE, author_import_report, default_callback_factory,
)

ALIASES = {"opus": "claude-opus-5-5", "haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5"}
META_KEYS = ("run", "scene", "stage", "track")
DEFAULT_MODELS = "haiku,opus"  # Haiku first in each round (plan M4)


def resolve_model(name: str) -> str:
    m = ALIASES.get(name, name)
    meter_mod.get_price(m)  # unknown model: stop before any spend
    return m


# ---- inputs ------------------------------------------------------------------------------------

@dataclass
class InputSpec:
    id: str
    root: Path
    prompt: str
    yaml: str
    images: list
    meta: dict


def load_input(root, expect_images: int = 6) -> InputSpec:
    root = Path(root)
    for name in ("prompt.txt", "graph.yaml", "meta.json"):
        if not (root / name).is_file():
            raise ValueError(f"{root}: missing {name}")
    images = sorted((p for p in (root / "slices").glob("*") if p.suffix.lower() in (".jpg", ".jpeg")),
                    key=lambda p: p.name) if (root / "slices").is_dir() else []
    if expect_images and len(images) != expect_images:
        raise ValueError(f"{root}: expected {expect_images} JPEGs in slices/, found {len(images)}")
    for p in images:
        if p.read_bytes()[:3] != b"\xff\xd8\xff":
            raise ValueError(f"{p}: not a JPEG")
    meta = json.loads((root / "meta.json").read_text())
    missing = [k for k in META_KEYS if k not in meta]
    if missing:
        raise ValueError(f"{root}/meta.json: missing {missing}")
    return InputSpec(root.name, root, (root / "prompt.txt").read_text(), (root / "graph.yaml").read_text(),
                     images, meta)


def load_inputs(inputs_dir, only: Optional[list] = None, expect_images: int = 6) -> dict:
    inputs_dir = Path(inputs_dir)
    ids = sorted(p.name for p in inputs_dir.iterdir() if p.is_dir())
    if only:
        unknown = [i for i in only if i not in ids]
        if unknown:
            raise ValueError(f"unknown input ids: {unknown}")
        ids = [i for i in ids if i in only]
    return {i: load_input(inputs_dir / i, expect_images) for i in ids}


def parse_order(text: str, known_ids) -> list:
    """Round order file: one input id per line, '#' starts a comment, a blank line ends a round."""
    rounds, cur = [], []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            if cur:
                rounds.append(cur)
                cur = []
            continue
        if line not in known_ids:
            raise ValueError(f"order file names unknown input {line!r}")
        cur.append(line)
    if cur:
        rounds.append(cur)
    flat = [i for r in rounds for i in r]
    if len(flat) != len(set(flat)):
        raise ValueError("order file lists an input twice")
    return rounds


def plan_rounds(ids, order_text: Optional[str]) -> list:
    ids = sorted(ids)
    return parse_order(order_text, set(ids)) if order_text is not None else [ids]


# ---- output ------------------------------------------------------------------------------------

def member_dir(out_dir, model: str, input_id: str, k: int) -> Path:
    return Path(out_dir) / model / input_id / f"member_{k}"


def member_key(model: str, input_id: str, k: int) -> str:
    return f"{model}|{input_id}|{k}"


def is_finished(mdir: Path) -> bool:
    try:
        rec = json.loads((mdir / "record.json").read_text())
    except (OSError, ValueError):
        return False
    return rec.get("status") in claude_loop.FINAL_STATUSES


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def write_member(mdir: Path, rec: dict) -> None:
    if rec.get("final_text") is not None:
        _atomic_write(mdir / "final.txt", rec["final_text"])
    _atomic_write(mdir / "record.json", json.dumps(rec, indent=1, sort_keys=True))  # last: marks the member done


# ---- campaign ----------------------------------------------------------------------------------

class _PrewarmGate:
    """Run the pre-warm once per (model, input); other members of that input wait for it."""

    def __init__(self):
        self._guard = threading.Lock()
        self._entries: dict = {}

    def ensure(self, key, fn):
        with self._guard:
            e = self._entries.setdefault(key, {"lock": threading.Lock(), "done": False, "ok": False, "info": None})
        with e["lock"]:
            if not e["done"]:
                try:
                    e["info"] = fn()
                    e["ok"] = True
                except Exception as ex:  # CapStop, MemberAbort, anything: members of this input are skipped
                    e["info"] = {"error": repr(ex)[:300]}
                    e["ok"] = False
                    e["exc"] = ex
                finally:
                    e["done"] = True
        return e["ok"], e["info"], e.get("exc")


def run_campaign(*, client, specs: dict, rounds: list, models: list, members: int,
                 settings: claude_loop.LoopSettings, meter, out_dir, concurrency: int = 4, resume: bool = True,
                 do_prewarm: bool = False, callback_factory: Callable, feasibility_sha: Optional[str] = None,
                 gate=None, sleep=time.sleep, rng=None, log: Callable[[str], None] = lambda s: None) -> dict:
    import random
    rng = rng or random.random
    out_dir = Path(out_dir)
    stop = threading.Event()
    lock = threading.Lock()
    outcomes: list = []
    warnings: list = []
    pw = _PrewarmGate()
    gate = gate or claude_loop.RateGate(sleep=sleep)

    def note(model, input_id, k, status, cost=None, **kw):
        with lock:
            outcomes.append({"model": model, "input": input_id, "member": k, "status": status, "cost_usd": cost, **kw})

    def task(model, spec, k):
        mdir = member_dir(out_dir, model, spec.id, k)
        if resume and is_finished(mdir):
            note(model, spec.id, k, "resumed")
            return
        if stop.is_set():
            note(model, spec.id, k, "skipped_cap")
            return
        key = member_key(model, spec.id, k)
        try:
            meter.admit_member(model, key)
        except meter_mod.CapStop as e:
            stop.set()
            note(model, spec.id, k, "skipped_cap", scope=e.scope)
            return
        try:
            if do_prewarm:
                def _pre():
                    r = claude_loop.prewarm(client, model, spec.prompt, spec.yaml, spec.images, settings,
                                            meter=meter, member_key=f"{model}|{spec.id}|prewarm", gate=gate,
                                            sleep=sleep, rng=rng)
                    log(f"[prewarm] {model} {spec.id}: wrote {r['usage']['cache_write']} tokens, "
                        f"read {r['usage']['cache_read']}")
                    if not r["cache_written"] and not r["cache_read"]:
                        with lock:
                            warnings.append(f"prewarm wrote no cache: {model} {spec.id}")
                    return r
                ok, info, exc = pw.ensure((model, spec.id), _pre)
                if not ok:
                    if isinstance(exc, meter_mod.CapStop):
                        stop.set()
                        note(model, spec.id, k, "skipped_cap", scope=exc.scope)
                    else:
                        note(model, spec.id, k, "skipped_prewarm_failed", error=info)
                    return
            rec = claude_loop.run_member(
                client, model, spec.prompt, spec.yaml, spec.images, callback_factory(spec.yaml), settings,
                meter=meter, member_key=key, gate=gate, sleep=sleep, rng=rng,
                meta={**spec.meta, "input": spec.id, "member": k, "feasibility_sha256": feasibility_sha})
            rec["input"], rec["member"] = spec.id, k
            if do_prewarm and rec["calls"]:
                if rec["calls"][0]["usage"]["cache_read"] <= 0:
                    rec["flags"].append("first_call_no_cache_read")
                    with lock:
                        warnings.append(f"first call read no cache: {model} {spec.id} member {k}")
            if rec["status"] == "cap_stopped":
                stop.set()
            write_member(mdir, rec)
            note(model, spec.id, k, rec["status"], rec["cost_usd"], flags=list(rec["flags"]))
            log(f"[member] {model} {spec.id} m{k}: {rec['status']} ${rec['cost_usd']:.4f} turns={rec['turns']}")
            for f in rec["flags"]:
                if f.startswith("served_model_mismatch"):
                    with lock:
                        warnings.append(f"{f}: {model} {spec.id} member {k}")
        except Exception as e:  # a bug in our code must not kill the campaign
            note(model, spec.id, k, "crashed", error=repr(e)[:300])
        finally:
            meter.end_member(model, key)

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        for ri, round_ids in enumerate(rounds):
            for model in models:
                log(f"[round {ri + 1}] {model}: {len(round_ids)} inputs")
                futs = [pool.submit(task, model, specs[i], k) for i in round_ids for k in range(members)]
                for f in futs:
                    f.result()

    counts: dict = {}
    for o in outcomes:
        counts[o["status"]] = counts.get(o["status"], 0) + 1
    summary = {
        "rounds": len(rounds), "models": models, "members_per_input": members, "counts": counts,
        "stopped_by_cap": stop.is_set(), "warnings": warnings, "meter": meter.summary(),
        "outcomes": outcomes, "rate_gate_trips": gate.trips,
    }
    _atomic_write(out_dir / "summary.json", json.dumps(summary, indent=1, sort_keys=True))
    return summary


# ---- dry run -----------------------------------------------------------------------------------

def dry_run(specs: dict, rounds: list, models: list, members: int, settings, out_dir, resume: bool,
            out=print) -> None:
    out(f"dry run: nothing is sent. token counts need the network (count_tokens), so none are shown.")
    out(f"price table: {meter_mod.PRICE_DATE}; {meter_mod.PRICE_SOURCE}")
    for ri, round_ids in enumerate(rounds):
        out(f"round {ri + 1}: {', '.join(round_ids)}")
    for model in models:
        for ri, round_ids in enumerate(rounds):
            for i in round_ids:
                spec = specs[i]
                images = claude_loop.read_images(spec.images)
                first = {"role": "user", "content": claude_loop.build_first_content(spec.prompt, spec.yaml, images, settings)}
                kw = claude_loop.build_request(model, [first], settings)
                size = len(json.dumps(kw["messages"]))
                todo = [k for k in range(members) if not (resume and is_finished(member_dir(out_dir, model, i, k)))]
                kinds = [b["type"] for b in first["content"]]
                out(f"  {model} {i}: round {ri + 1}, images={kinds.count('image')}, first-message JSON bytes={size}, "
                    f"prompt chars={len(spec.prompt)}, yaml chars={len(spec.yaml)}, members to run={len(todo)}/{members}")
    sample = claude_loop.build_request(models[0], [{"role": "user", "content": "..."}], settings)
    show = {k: v for k, v in sample.items() if k != "messages"}
    out("request settings: " + json.dumps(show, sort_keys=True))


# ---- CLI ---------------------------------------------------------------------------------------

def _kv(items, what):
    out = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"{what}: expected MODEL=USD, got {it!r}")
        k, v = it.split("=", 1)
        out[resolve_model(k)] = float(v)
    return out


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inputs_dir")
    p.add_argument("out_dir")
    p.add_argument("--models", default=DEFAULT_MODELS, help="comma list; order = run order in a round")
    p.add_argument("--members", type=int, default=4)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--only", help="comma list of input ids")
    p.add_argument("--order", help="round order file (one id per line; blank line ends a round)")
    p.add_argument("--resume", action="store_true", help="skip members that finished (key: model, input, member)")
    p.add_argument("--prewarm", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--effort", default="medium", choices=claude_loop.EFFORTS)
    p.add_argument("--max-tokens", type=int, default=64000)
    p.add_argument("--max-turns", type=int, default=50)
    p.add_argument("--cache-ttl", default="5m", choices=["5m", "1h"])
    p.add_argument("--thinking-display", choices=["summarized", "omitted", "updates"])
    p.add_argument("--block-binding", default="error", choices=["error", "drop_block", "off"])
    p.add_argument("--expect-images", type=int, default=6, help="0 turns the check off")
    p.add_argument("--cap-member", type=float, help="USD per member (overrides the per-model default)")
    p.add_argument("--cap-run", type=float, help="USD for this process, all models")
    p.add_argument("--cap-campaign", type=float, help="USD over the whole ledger, all models")
    p.add_argument("--cap-model", action="append", metavar="MODEL=USD", help="USD over the whole ledger, one model")
    p.add_argument("--reserve", action="append", metavar="MODEL=USD", help="reserve per call (measured p99)")
    p.add_argument("--admit", action="append", metavar="MODEL=USD", help="expected cost of one member")
    p.add_argument("--author-source", default=str(DEFAULT_AUTHOR_SOURCE))
    p.add_argument("--check-author", action="store_true", help="report what the author's file needs, then exit")
    return p


def main(argv=None, *, client_factory: Optional[Callable] = None, sleep=time.sleep) -> int:
    args = build_parser().parse_args(argv)
    if args.check_author:
        print(json.dumps({"author_source": args.author_source, "imports_resolve": author_import_report(Path(args.author_source))},
                         indent=1))
        _, feas = default_callback_factory(Path(args.author_source))
        print(f"validate_feasibility loads verbatim (needs numpy and json only); sha256 {feas.sha256}")
        return 0
    models = [resolve_model(m) for m in args.models.split(",") if m]
    settings = claude_loop.LoopSettings(
        effort=args.effort, max_tokens=args.max_tokens, max_turns=args.max_turns, cache_ttl=args.cache_ttl,
        thinking_display=args.thinking_display,
        block_binding=None if args.block_binding == "off" else args.block_binding)
    specs = load_inputs(args.inputs_dir, args.only.split(",") if args.only else None, args.expect_images)
    if not specs:
        raise SystemExit("no inputs found")
    order_text = Path(args.order).read_text() if args.order else None
    rounds = plan_rounds(specs.keys(), order_text)
    if order_text is not None:
        unlisted = sorted(set(specs) - {i for r in rounds for i in r})
        if unlisted:
            print(f"warning: {len(unlisted)} input(s) not in the order file will not run: {unlisted}", file=sys.stderr)
        specs = {i: specs[i] for r in rounds for i in r}
    out_dir = Path(args.out_dir)

    if args.dry_run:
        dry_run(specs, rounds, models, args.members, settings, out_dir, args.resume)
        return 0

    caps = meter_mod.Caps(member=args.cap_member, run=args.cap_run, campaign=args.cap_campaign,
                          by_model=_kv(args.cap_model, "--cap-model"))
    if caps.run is None and caps.campaign is None:
        raise SystemExit("refusing a live run without --cap-run or --cap-campaign")
    if not args.resume and any(is_finished(p.parent) for p in out_dir.glob("*/*/member_*/record.json")):
        raise SystemExit(f"{out_dir} already holds finished members; pass --resume (never pay twice) or use a new OUT_DIR")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if client_factory is None:
        if not key:
            raise SystemExit("ANTHROPIC_API_KEY is not set")
        client_factory = lambda s: claude_loop.make_client(key, s)  # noqa: E731
    client = client_factory(settings)
    mt = meter_mod.Meter(out_dir / "usage.jsonl", caps=caps, reserve_usd=_kv(args.reserve, "--reserve"),
                         admit_usd=_kv(args.admit, "--admit"))
    factory, feas = default_callback_factory(Path(args.author_source))

    def log(s):
        print(s, file=sys.stderr, flush=True)

    summary = run_campaign(client=client, specs=specs, rounds=rounds, models=models, members=args.members,
                           settings=settings, meter=mt, out_dir=out_dir, concurrency=args.concurrency,
                           resume=args.resume, do_prewarm=args.prewarm, callback_factory=factory,
                           feasibility_sha=feas.sha256, sleep=sleep, log=log)
    print(json.dumps({"counts": summary["counts"], "stopped_by_cap": summary["stopped_by_cap"],
                      "warnings": summary["warnings"], "meter": summary["meter"]}, indent=1))
    return 2 if summary["stopped_by_cap"] else 0


if __name__ == "__main__":
    sys.exit(main())
