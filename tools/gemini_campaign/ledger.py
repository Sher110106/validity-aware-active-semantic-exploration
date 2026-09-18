"""Fail-closed SQLite allocation and request ledger."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from .config import (
    CAMPAIGN_CEILING_MICROUSD,
    MODEL_ID,
    NORMAL_CEILING_MICROUSD,
    PHASE_CAPS,
    PRICING_VERSION,
    RECOVERY_RESERVE_MICROUSD,
    THINKING_LEVEL,
    cost_microdollars,
)
from .errors import AccountingHalt, LedgerError

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")
_STATES = "'RESERVED','DISPATCHED','SETTLED'"
_FINISH_REASONS = {"STOP", "MAX_TOKENS", "LENGTH", "SAFETY", "OTHER"}

@dataclass(frozen=True)
class RecoveryControl:
    approved: bool
    phase_id: str
    amount_microusd: int
    purpose: str
    expires_at: int

@dataclass(frozen=True)
class Allocation:
    allocation_id: str
    phase_id: str
    amount_microusd: int

@dataclass(frozen=True)
class Reservation:
    request_id: str
    allocation_id: str
    reservation_microusd: int


class Ledger:
    def __init__(self, path: str, *, recovery_control: RecoveryControl | None = None):
        if not isinstance(path, str) or not path:
            raise LedgerError("ledger configuration is invalid")
        self.path = path
        self.recovery = self._validate_recovery(recovery_control)
        self.ceiling = CAMPAIGN_CEILING_MICROUSD
        try:
            self.db = sqlite3.connect(path, timeout=2, isolation_level=None)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA busy_timeout=2000")
            self.db.execute("PRAGMA foreign_keys=ON")
            mode = self.db.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if mode.lower() != "wal":
                raise LedgerError("ledger journal policy unavailable")
            self._init_schema()
            self._validate_schema()
            if self.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise LedgerError("ledger integrity check failed")
            self._secure_db_files()
        except LedgerError:
            if hasattr(self, "db"):
                self.db.close()
            raise
        except (sqlite3.Error, OSError):
            if hasattr(self, "db"):
                self.db.close()
            raise LedgerError("ledger unavailable")

    @staticmethod
    def _validate_recovery(control: RecoveryControl | None) -> RecoveryControl | None:
        if control is None:
            return None
        if not isinstance(control, RecoveryControl) or not control.approved:
            raise LedgerError("recovery control is invalid")
        if control.phase_id != "recovery" or not _ID.fullmatch(control.purpose):
            raise LedgerError("recovery control is invalid")
        if not isinstance(control.amount_microusd, int) or not 0 < control.amount_microusd <= RECOVERY_RESERVE_MICROUSD:
            raise LedgerError("recovery control is invalid")
        if not isinstance(control.expires_at, int) or control.expires_at <= int(time.time()):
            raise LedgerError("recovery control is invalid")
        return control

    def _init_schema(self) -> None:
        self.db.executescript(f"""
        CREATE TABLE IF NOT EXISTS allocations (
          allocation_id TEXT PRIMARY KEY,
          campaign_id TEXT NOT NULL CHECK(length(campaign_id) BETWEEN 1 AND 128),
          phase_id TEXT NOT NULL CHECK(phase_id IN ('probe','engineering','scientific','recovery')),
          amount_microusd INTEGER NOT NULL CHECK(amount_microusd > 0),
          created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS requests (
          request_id TEXT PRIMARY KEY,
          allocation_id TEXT NOT NULL REFERENCES allocations(allocation_id),
          campaign_id TEXT NOT NULL, phase_id TEXT NOT NULL,
          run_id TEXT NOT NULL, stage_id TEXT NOT NULL, member_id TEXT NOT NULL,
          tool_turn_id TEXT NOT NULL, attempt_id TEXT NOT NULL, retry_of TEXT,
          model TEXT NOT NULL CHECK(model = '{MODEL_ID}'),
          thinking_level TEXT NOT NULL CHECK(thinking_level = '{THINKING_LEVEL}'),
          max_output_tokens INTEGER NOT NULL CHECK(max_output_tokens BETWEEN 1 AND 65536),
          input_tokens INTEGER, candidate_tokens INTEGER, thought_tokens INTEGER,
          cached_tokens INTEGER, total_tokens INTEGER,
          reservation_microusd INTEGER NOT NULL CHECK(reservation_microusd > 0),
          settled_microusd INTEGER,
          provider_response_id TEXT UNIQUE, state TEXT NOT NULL CHECK(state IN ({_STATES})),
          finish_reason TEXT, service_tier TEXT, response_checksum TEXT,
          created_at INTEGER NOT NULL, dispatched_at INTEGER, settled_at INTEGER,
          error_code TEXT, pricing_version TEXT NOT NULL,
          FOREIGN KEY(retry_of) REFERENCES requests(request_id),
          UNIQUE(campaign_id, attempt_id)
        );
        CREATE INDEX IF NOT EXISTS requests_state ON requests(state);
        """)

    def _validate_schema(self) -> None:
        expected = {
            "allocation_id", "phase_id", "attempt_id", "max_output_tokens",
            "candidate_tokens", "thought_tokens", "total_tokens", "service_tier",
            "pricing_version", "state",
        }
        got = {row[1] for row in self.db.execute("PRAGMA table_info(requests)")}
        if not expected <= got:
            raise LedgerError("ledger schema is unsupported")

    def _secure_db_files(self) -> None:
        # Best effort hardening for a newly created private ledger; failure is
        # accounting-fatal rather than silently weakening the boundary.
        import os
        os.chmod(self.path, 0o600)

    def _tx(self) -> None:
        try:
            self.db.execute("BEGIN IMMEDIATE")
        except sqlite3.Error as exc:
            raise AccountingHalt("ledger lock unavailable") from exc

    def _rollback(self) -> None:
        try:
            self.db.execute("ROLLBACK")
        except sqlite3.Error:
            pass

    @staticmethod
    def _id(value: Any, name: str) -> str:
        if not isinstance(value, str) or not _ID.fullmatch(value):
            raise LedgerError(f"{name} is invalid")
        return value

    def _effective_ceiling(self) -> int:
        return NORMAL_CEILING_MICROUSD + (self.recovery.amount_microusd if self.recovery else 0)

    def _check_phase(self, phase_id: str) -> None:
        self._id(phase_id, "phase")
        if phase_id not in PHASE_CAPS:
            raise LedgerError("phase is invalid")
        if phase_id == "recovery" and self.recovery is None:
            raise AccountingHalt("recovery control required")

    def _allocated_total(self) -> int:
        return int(self.db.execute("SELECT COALESCE(SUM(amount_microusd),0) FROM allocations").fetchone()[0])

    def allocate(self, *, campaign_id: str, phase_id: str, amount_microusd: int) -> Allocation:
        self._id(campaign_id, "campaign")
        self._check_phase(phase_id)
        if not isinstance(amount_microusd, int) or amount_microusd <= 0:
            raise LedgerError("allocation amount is invalid")
        if amount_microusd > PHASE_CAPS[phase_id] or phase_id == "recovery" and amount_microusd > self.recovery.amount_microusd:
            raise AccountingHalt("phase allocation cap reached")
        aid = uuid.uuid4().hex
        self._tx()
        try:
            phase_total = int(self.db.execute("SELECT COALESCE(SUM(amount_microusd),0) FROM allocations WHERE phase_id=?", (phase_id,)).fetchone()[0])
            if phase_total + amount_microusd > PHASE_CAPS[phase_id]:
                raise AccountingHalt("phase allocation cap reached")
            if self._allocated_total() + amount_microusd > self._effective_ceiling():
                raise AccountingHalt("campaign allocation ceiling reached")
            self.db.execute("INSERT INTO allocations VALUES (?,?,?,?,?)", (aid, campaign_id, phase_id, amount_microusd, int(time.time())))
            self.db.execute("COMMIT")
            return Allocation(aid, phase_id, amount_microusd)
        except (AccountingHalt, LedgerError):
            self._rollback()
            raise
        except sqlite3.Error as exc:
            self._rollback()
            raise AccountingHalt("allocation failed; dispatch halted") from exc

    def reserve(self, *, allocation_id: str, campaign_id: str, phase_id: str, run_id: str,
                stage_id: str, member_id: str, tool_turn_id: str, attempt_id: str,
                model: str, thinking_level: str, max_output_tokens: int,
                input_bound: int, retry_of: str | None = None) -> Reservation:
        ids = ((campaign_id, "campaign"), (phase_id, "phase"), (run_id, "run"),
               (stage_id, "stage"), (member_id, "member"), (tool_turn_id, "tool turn"),
               (attempt_id, "attempt"), (allocation_id, "allocation"))
        for value, name in ids:
            self._id(value, name)
        self._check_phase(phase_id)
        if model != MODEL_ID or thinking_level != THINKING_LEVEL:
            raise LedgerError("model policy rejected")
        if not isinstance(max_output_tokens, int) or not 0 < max_output_tokens <= 65_536:
            raise LedgerError("output cap is invalid")
        if not isinstance(input_bound, int) or input_bound < 0:
            raise LedgerError("input bound is invalid")
        if retry_of is not None:
            self._id(retry_of, "retry provenance")
        reservation = cost_microdollars(input_bound, max_output_tokens)
        rid = uuid.uuid4().hex
        self._tx()
        try:
            allocation = self.db.execute("SELECT * FROM allocations WHERE allocation_id=?", (allocation_id,)).fetchone()
            if allocation is None or allocation["campaign_id"] != campaign_id or allocation["phase_id"] != phase_id:
                raise AccountingHalt("allocation is invalid")
            used = int(self.db.execute("SELECT COALESCE(SUM(reservation_microusd),0) FROM requests WHERE allocation_id=?", (allocation_id,)).fetchone()[0])
            if used + reservation > allocation["amount_microusd"]:
                raise AccountingHalt("allocation exhausted")
            if retry_of is not None:
                prior = self.db.execute("SELECT campaign_id FROM requests WHERE request_id=?", (retry_of,)).fetchone()
                if prior is None or prior["campaign_id"] != campaign_id:
                    raise AccountingHalt("retry provenance is invalid")
            self.db.execute("""INSERT INTO requests
              (request_id,allocation_id,campaign_id,phase_id,run_id,stage_id,member_id,tool_turn_id,attempt_id,retry_of,model,thinking_level,max_output_tokens,reservation_microusd,state,created_at,pricing_version)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, ?, ?)""",
              (rid, allocation_id, campaign_id, phase_id, run_id, stage_id, member_id,
               tool_turn_id, attempt_id, retry_of, model, thinking_level, max_output_tokens,
               reservation, "RESERVED", int(time.time()), PRICING_VERSION))
            self.db.execute("COMMIT")
            return Reservation(rid, allocation_id, reservation)
        except (AccountingHalt, LedgerError):
            self._rollback()
            raise
        except sqlite3.IntegrityError as exc:
            self._rollback()
            raise AccountingHalt("request identity is already used") from exc
        except sqlite3.Error as exc:
            self._rollback()
            raise AccountingHalt("reservation failed; dispatch halted") from exc

    def mark_dispatched(self, request_id: str) -> str:
        self._id(request_id, "request")
        dispatch_id = uuid.uuid4().hex
        self._tx()
        try:
            cur = self.db.execute("UPDATE requests SET state='DISPATCHED', dispatched_at=? WHERE request_id=? AND state='RESERVED'", (int(time.time()), request_id))
            if cur.rowcount != 1:
                raise AccountingHalt("request is not reservable")
            self.db.execute("COMMIT")
            return dispatch_id
        except AccountingHalt:
            self._rollback()
            raise
        except sqlite3.Error as exc:
            self._rollback()
            raise AccountingHalt("dispatch receipt failed") from exc

    def settle(self, request_id: str, *, model: str, service_tier: str,
               input_tokens: int, candidate_tokens: int, thought_tokens: int,
               cached_tokens: int, total_tokens: int, provider_response_id: str,
               finish_reason: str, response_bytes: bytes = b"",
               pricing_version: str = PRICING_VERSION) -> None:
        self._id(request_id, "request")
        self._id(provider_response_id, "provider response")
        values = (input_tokens, candidate_tokens, thought_tokens, cached_tokens, total_tokens)
        if any(not isinstance(value, int) or value < 0 for value in values):
            raise AccountingHalt("invalid usage; reservation retained")
        if model != MODEL_ID or service_tier != "standard" or pricing_version != PRICING_VERSION:
            raise AccountingHalt("response policy mismatch; reservation retained")
        if finish_reason not in _FINISH_REASONS or cached_tokens > input_tokens:
            raise AccountingHalt("response usage is invalid; reservation retained")
        if total_tokens != input_tokens + candidate_tokens + thought_tokens:
            raise AccountingHalt("response totals are inconsistent; reservation retained")
        generated = candidate_tokens + thought_tokens
        settled = cost_microdollars(input_tokens, generated)
        checksum = hashlib.sha256(response_bytes).hexdigest() if response_bytes else None
        self._tx()
        try:
            row = self.db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
            if row is None:
                raise LedgerError("request is unknown")
            immutable = (row["model"], row["pricing_version"], row["input_tokens"], row["candidate_tokens"], row["thought_tokens"], row["cached_tokens"], row["total_tokens"], row["settled_microusd"], row["provider_response_id"], row["finish_reason"], row["service_tier"], row["response_checksum"])
            incoming = (model, pricing_version, input_tokens, candidate_tokens, thought_tokens, cached_tokens, total_tokens, settled, provider_response_id, finish_reason, service_tier, checksum)
            if row["state"] == "SETTLED":
                if immutable == incoming:
                    self._rollback()
                    return
                raise AccountingHalt("conflicting duplicate settlement")
            if row["state"] != "DISPATCHED" or generated > row["max_output_tokens"] or settled > row["reservation_microusd"]:
                raise AccountingHalt("request is not settleable; reservation retained")
            cur = self.db.execute("""UPDATE requests SET state='SETTLED',input_tokens=?,candidate_tokens=?,thought_tokens=?,cached_tokens=?,total_tokens=?,settled_microusd=?,provider_response_id=?,finish_reason=?,service_tier=?,settled_at=?,response_checksum=? WHERE request_id=? AND state='DISPATCHED'""",
                (*values, settled, provider_response_id, finish_reason, service_tier, int(time.time()), checksum, request_id))
            if cur.rowcount != 1:
                raise AccountingHalt("settlement state changed; reservation retained")
            self.db.execute("COMMIT")
        except (AccountingHalt, LedgerError):
            self._rollback()
            raise
        except sqlite3.IntegrityError as exc:
            self._rollback()
            raise AccountingHalt("duplicate provider response; reservation retained") from exc
        except sqlite3.Error as exc:
            self._rollback()
            raise AccountingHalt("settlement failed; reservation retained") from exc

    def summary(self) -> dict[str, int]:
        try:
            reserved = int(self.db.execute("SELECT COALESCE(SUM(reservation_microusd),0) FROM requests WHERE state!='SETTLED'").fetchone()[0])
            settled = int(self.db.execute("SELECT COALESCE(SUM(settled_microusd),0) FROM requests WHERE state='SETTLED'").fetchone()[0])
            allocated = self._allocated_total()
            unresolved = int(self.db.execute("SELECT COUNT(*) FROM requests WHERE state!='SETTLED'").fetchone()[0])
            return {"user_cap_microusd": 200_000_000, "ceiling_microusd": self.ceiling,
                    "allocated_microusd": allocated, "reserved_microusd": reserved,
                    "settled_microusd": settled, "unresolved_requests": unresolved,
                    "remaining_microusd": self.ceiling - allocated}
        except sqlite3.Error as exc:
            raise AccountingHalt("ledger summary unavailable") from exc

    def export(self) -> dict[str, list[dict[str, Any]]]:
        try:
            return {
                "allocations": [dict(row) for row in self.db.execute("SELECT * FROM allocations ORDER BY created_at,allocation_id")],
                "requests": [dict(row) for row in self.db.execute("SELECT * FROM requests ORDER BY created_at,request_id")],
            }
        except sqlite3.Error as exc:
            raise AccountingHalt("ledger export unavailable") from exc

    def checksum(self) -> str:
        payload = json.dumps(self.export(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()

    def close(self) -> None:
        self.db.close()
