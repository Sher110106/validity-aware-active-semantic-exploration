"""Per-worker-process construction of the real ledger/transport for the
author overlay.

Deliberately NOT constructed once in LLMManager.__init__ and reused: the
pinned pipeline runs each ensemble member in its own ProcessPoolExecutor
worker (mp_context="spawn"), and a sqlite3 connection held inside a Ledger
cannot be pickled across that process boundary. Each worker opens its own
Ledger connection to the same on-disk file instead -- already proven safe
for exactly this by gemini_campaign's own concurrency tests (WAL mode plus
SQLite's own locking).

Configuration travels via environment variables, set once by whatever
launches the pipeline for one prospective attempt -- the same convention
_asp_llm_logger.py already uses for ASP_LLM_LOG_DIR/ASP_LLM_MAX_CALLS.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from gemini_campaign.credentials import load_credential
from gemini_campaign.ledger import Ledger

from prospective_integration.count_log import CountLog
from prospective_integration.ledger_budget_broker import LedgerBudgetBroker
from prospective_integration.race_instrumentation import RaceInstrumentation
from prospective_integration.raw_archive import RawResponseArchive
from prospective_runtime.transport import (
    GeminiTransport, RequestContext, conservative_input_bound, native_input_bound,
)

_REQUIRED_ENV = ("ASP_PROSPECTIVE_LEDGER_PATH", "ASP_PROSPECTIVE_CREDENTIAL_PATH",
                 "ASP_PROSPECTIVE_CAMPAIGN_ID", "ASP_PROSPECTIVE_ALLOCATION_ID",
                 "ASP_PROSPECTIVE_RUN_ID")


@dataclass(frozen=True)
class LedgerContext:
    ledger_path: str
    credential_path: str
    campaign_id: str
    phase_id: str
    allocation_id: str
    run_id: str
    max_output_tokens: int

    @classmethod
    def from_env(cls) -> Optional["LedgerContext"]:
        """None means "no prospective overlay configured"; the caller
        (llm_completion.py's patched methods) must fail closed on that,
        never silently fall back to an unaccounted call."""
        if not os.environ.get("ASP_PROSPECTIVE_LEDGER_PATH"):
            return None
        missing = [name for name in _REQUIRED_ENV if not os.environ.get(name)]
        if missing:
            raise RuntimeError(
                "ASP_PROSPECTIVE_LEDGER_PATH is set but required prospective "
                f"overlay environment variables are missing: {', '.join(missing)}"
            )
        return cls(
            ledger_path=os.environ["ASP_PROSPECTIVE_LEDGER_PATH"],
            credential_path=os.environ["ASP_PROSPECTIVE_CREDENTIAL_PATH"],
            campaign_id=os.environ["ASP_PROSPECTIVE_CAMPAIGN_ID"],
            phase_id=os.environ.get("ASP_PROSPECTIVE_PHASE_ID", "engineering"),
            allocation_id=os.environ["ASP_PROSPECTIVE_ALLOCATION_ID"],
            run_id=os.environ["ASP_PROSPECTIVE_RUN_ID"],
            max_output_tokens=int(os.environ.get("ASP_PROSPECTIVE_MAX_OUTPUT_TOKENS", "8192")),
        )


def build_transport(ledger_context: LedgerContext) -> GeminiTransport:
    ledger = Ledger(ledger_context.ledger_path)
    broker = LedgerBudgetBroker(ledger)

    def load_key() -> str:
        return load_credential(ledger_context.credential_path, forbidden_roots=())

    # Optional raw request/response archive (deliberately separate from
    # gemini_campaign/events.py's sanitized, metadata-only log) -- opt-in
    # via ASP_PROSPECTIVE_RAW_ARCHIVE_PATH, off by default.
    archive_path = os.environ.get("ASP_PROSPECTIVE_RAW_ARCHIVE_PATH")
    on_raw_response = RawResponseArchive(archive_path) if archive_path else None

    return GeminiTransport(load_key, broker=broker, on_raw_response=on_raw_response)


def build_input_bound_fn(ledger_context: LedgerContext) -> Callable[[Mapping[str, Any]], int]:
    """The real per-request token count via the free countTokens
    endpoint, falling back to the conservative byte bound on any
    failure -- see transport.native_input_bound() for why that fallback
    direction is safe (over-reserve, never under-reserve).

    Opt-in via ASP_PROSPECTIVE_NATIVE_COUNT=1, off (byte bound only,
    today's exact behavior) otherwise -- so nothing changes for an
    existing deployment until this is explicitly turned on. Measured
    live (2026-09-21): the byte bound overshoots the real count by
    ~440x on a real 6-image completion request (4,104,516 vs. 9,317),
    which is why the byte-only path alone could not run this campaign
    at any allocation size."""
    def load_key() -> str:
        return load_credential(ledger_context.credential_path, forbidden_roots=())
    if os.environ.get("ASP_PROSPECTIVE_NATIVE_COUNT") != "1":
        return conservative_input_bound

    log_path = os.environ.get("ASP_PROSPECTIVE_COUNT_LOG")
    on_count = CountLog(log_path).record if log_path else None

    def bound_fn(request: Mapping[str, Any]) -> int:
        return native_input_bound(request, credential_loader=load_key, on_count=on_count)
    return bound_fn


def record_race_instrumentation(*, scene_index: int, ensemble_index: int, graph_id: int, result_path) -> None:
    """No-op unless ASP_PROSPECTIVE_RACE_LOG is set. See race_instrumentation.py
    for why this matters: complete_scene_graph()'s as_completed() loop yields
    in completion order, so generated_graphs[0] is a race winner, not
    "ensemble member 0". Pure instrumentation, called from
    _run_single_ensemble_member regardless of success/drop -- never changes
    behavior."""
    path = os.environ.get("ASP_PROSPECTIVE_RACE_LOG")
    if not path:
        return
    RaceInstrumentation(path).record_member_finished(
        scene_index=scene_index, ensemble_index=ensemble_index,
        graph_id=graph_id, result_path=result_path,
    )


def make_context(ledger_context: LedgerContext, *, scene_index: int, ensemble_index: int,
                 call: str, pipeline_stage: str) -> RequestContext:
    """pipeline_stage must be the pinned pipeline's own stage counter
    (exploration_pipeline.py's self.stage, exposed to the overlay only via
    LLMCompletion.base_path == WORKING_DIRECTORY == BASE_DIRECTORY/<stage>,
    since the pinned file is never edited to pass it explicitly).

    Confirmed live, 2026-09-22 (real scientific-campaign block 1): omitting
    this let every stage beyond the first reconstruct the exact same
    deterministic turn_id/attempt_id as stage 0, since scene_index/
    ensemble_index/call alone repeat identically every stage. resolve_attempt_id
    (gemini_campaign/ledger.py) "resolved" every one of these as a
    same-stage retry, correctly avoiding a collision but mislabeling
    entirely new, legitimate per-stage work as redundant re-billing --
    and, more seriously, consuming the MAX_ATTEMPT_RETRY_GENERATIONS
    budget meant for real transient-failure retries, which would have
    halted every member with AccountingHalt after only 4 real stages,
    nowhere near any real path-length checkpoint. Including the real
    stage number here makes every stage's ids naturally distinct, so
    resolve_attempt_id's retry path is reserved for genuine same-stage
    retries again.

    Also folds in ledger_context.run_id, for the same reason one level up:
    confirmed live, 2026-09-22, immediately after the stage fix -- a
    multi-block campaign deliberately shares one campaign_id across all
    blocks (so one ledger file's ceiling enforces the true total cap
    globally, per DEVIATIONS.md #83), so scene/member/call/stage alone
    still collide identically across every block that reaches the same
    stage number. run_id is set fresh per block by whatever launches the
    pipeline (ASP_PROSPECTIVE_RUN_ID) and is exactly the missing
    dimension."""
    stage_id = f"scene{scene_index}"
    member_id = f"member{ensemble_index}"
    turn_id = f"{ledger_context.run_id}-stage{pipeline_stage}-{stage_id}-{member_id}-{call}"
    return RequestContext(
        allocation_id=ledger_context.allocation_id, campaign_id=ledger_context.campaign_id,
        phase_id=ledger_context.phase_id, run_id=ledger_context.run_id,
        stage_id=stage_id, member_id=member_id, turn_id=turn_id, attempt_id=turn_id,
        trusted_input_token_bound=1,  # overridden per-turn by run_author_turns/run_single_turn
    )


def deterministic_seed(ledger_context: LedgerContext, scene_index: int, ensemble_index: int,
                       turn: int, *, base_seed: int) -> int:
    key = f"{ledger_context.run_id}\x1f{scene_index}\x1f{ensemble_index}\x1f{turn}\x1f{base_seed}".encode()
    # int.from_bytes(4 bytes, "big") gives an unsigned 32-bit range
    # [0, 2**32-1], but transport.py's _validate_request requires the API's
    # signed 31-bit range [0, 2**31-1] -- masking to 31 bits, confirmed live
    # (capability pilot, 2026-09-21): about half of randomly-hashed 32-bit
    # values exceeded 2**31-1 and were rejected before any reservation.
    return int.from_bytes(hashlib.sha256(key).digest()[:4], "big") & 0x7FFFFFFF
