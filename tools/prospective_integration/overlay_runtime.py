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
from typing import Optional

from gemini_campaign.credentials import load_credential
from gemini_campaign.ledger import Ledger

from prospective_integration.ledger_budget_broker import LedgerBudgetBroker
from prospective_runtime.transport import GeminiTransport, RequestContext

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

    return GeminiTransport(load_key, broker=broker)


def make_context(ledger_context: LedgerContext, *, scene_index: int, ensemble_index: int,
                 call: str) -> RequestContext:
    stage_id = f"scene{scene_index}"
    member_id = f"member{ensemble_index}"
    turn_id = f"{stage_id}-{member_id}-{call}"
    return RequestContext(
        allocation_id=ledger_context.allocation_id, campaign_id=ledger_context.campaign_id,
        phase_id=ledger_context.phase_id, run_id=ledger_context.run_id,
        stage_id=stage_id, member_id=member_id, turn_id=turn_id, attempt_id=turn_id,
        trusted_input_token_bound=1,  # overridden per-turn by run_author_turns/run_single_turn
    )


def deterministic_seed(ledger_context: LedgerContext, scene_index: int, ensemble_index: int,
                       turn: int, *, base_seed: int) -> int:
    key = f"{ledger_context.run_id}\x1f{scene_index}\x1f{ensemble_index}\x1f{turn}\x1f{base_seed}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:4], "big")
