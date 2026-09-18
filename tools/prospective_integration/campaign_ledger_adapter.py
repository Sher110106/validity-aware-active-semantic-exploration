"""Bridges prospective_campaign's block-level ledger protocol to the real,
audited gemini_campaign.Ledger, instead of duplicating its accounting.

reserve_block() maps 1:1 onto a real gemini_campaign Allocation, addressed by
the campaign's own block id (idempotent: a repeat call with the same id fails
closed rather than silently re-allocating -- see Ledger.allocate()).

draw() is a separate, coarser fixed-amount debit against that same
allocation. It deliberately does not go through Ledger.reserve(): that method
prices a request from token bounds via the campaign's exact pricing formula,
not an arbitrary caller-supplied microUSD amount, and forcing a fixed amount
through it would require inventing token counts that don't correspond to any
real request. draw() shares the ledger's own SQLite connection and
transaction discipline (BEGIN IMMEDIATE / COMMIT / ROLLBACK) so both
bookkeeping layers stay consistent, including across a crash and restart
against the same database file.
"""
from __future__ import annotations

import re
import sqlite3
import time

from gemini_campaign.errors import AccountingHalt, LedgerError
from gemini_campaign.ledger import Ledger

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")


class CampaignLedgerAdapter:
    """Implements prospective_campaign.queue.GeminiLedger against the real ledger."""

    def __init__(self, ledger: Ledger, *, campaign_id: str, phase_id: str = "scientific"):
        self.ledger, self.campaign_id, self.phase_id = ledger, campaign_id, phase_id
        self.ledger.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS block_draws (
              allocation_id TEXT NOT NULL REFERENCES allocations(allocation_id),
              request_id TEXT NOT NULL,
              amount_microusd INTEGER NOT NULL CHECK(amount_microusd >= 0),
              created_at INTEGER NOT NULL,
              PRIMARY KEY (allocation_id, request_id)
            );
            """
        )

    def available_micro_usd(self) -> int:
        return self.ledger.summary()["remaining_microusd"]

    def reserve_block(self, allocation_id: str, amount_micro_usd: int) -> bool:
        if not isinstance(amount_micro_usd, int) or amount_micro_usd <= 0:
            return False
        try:
            self.ledger.allocate(campaign_id=self.campaign_id, phase_id=self.phase_id,
                                 amount_microusd=amount_micro_usd, allocation_id=allocation_id)
            return True
        except (AccountingHalt, LedgerError):
            return False

    def draw(self, allocation_id: str, request_id: str, amount_micro_usd: int) -> bool:
        if (not isinstance(amount_micro_usd, int) or amount_micro_usd < 0
                or not isinstance(allocation_id, str) or not _ID.fullmatch(allocation_id)
                or not isinstance(request_id, str) or not _ID.fullmatch(request_id)):
            return False
        db = self.ledger.db
        try:
            db.execute("BEGIN IMMEDIATE")
        except sqlite3.Error:
            return False
        try:
            allocation = db.execute(
                "SELECT amount_microusd FROM allocations WHERE allocation_id=? AND campaign_id=?",
                (allocation_id, self.campaign_id),
            ).fetchone()
            if allocation is None:
                db.execute("ROLLBACK")
                return False
            used = int(db.execute(
                "SELECT COALESCE(SUM(amount_microusd),0) FROM block_draws WHERE allocation_id=?",
                (allocation_id,),
            ).fetchone()[0])
            if used + amount_micro_usd > allocation[0]:
                db.execute("ROLLBACK")
                return False
            db.execute("INSERT INTO block_draws VALUES (?,?,?,?)",
                      (allocation_id, request_id, amount_micro_usd, int(time.time())))
            db.execute("COMMIT")
            return True
        except sqlite3.Error:
            db.execute("ROLLBACK")
            return False
