"""SQLite ledger with conservative, transactional reservations."""
from __future__ import annotations
import hashlib, json, sqlite3, time, uuid
from dataclasses import dataclass, asdict
from .config import CAMPAIGN_CEILING_MICROUSD, NORMAL_CEILING_MICROUSD, MODEL_ID, THINKING_LEVEL, cost_microdollars, PRICING_VERSION
from .errors import AccountingHalt, LedgerError

@dataclass(frozen=True)
class Reservation:
    request_id: str
    reservation_microusd: int

class Ledger:
    def __init__(self, path: str, ceiling_microusd: int = CAMPAIGN_CEILING_MICROUSD,
                 recovery_enabled: bool = False):
        self.path = path
        self.ceiling = ceiling_microusd
        self.recovery_enabled = recovery_enabled
        if ceiling_microusd <= 0: raise ValueError("ceiling must be positive")
        try:
            self.db = sqlite3.connect(path, timeout=5, isolation_level=None)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA busy_timeout=5000")
            self.db.execute("PRAGMA foreign_keys=ON")
            self._init_schema()
            if self.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok": raise LedgerError("ledger integrity check failed")
        except (sqlite3.Error, OSError) as exc:
            raise LedgerError("ledger unavailable") from exc

    def _init_schema(self):
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS requests (
          request_id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, phase_id TEXT NOT NULL,
          run_id TEXT NOT NULL, stage_id TEXT NOT NULL, member_id TEXT NOT NULL,
          tool_turn_id TEXT NOT NULL, attempt_id TEXT NOT NULL, retry_of TEXT,
          model TEXT NOT NULL, thinking_level TEXT NOT NULL, input_tokens INTEGER,
          output_tokens INTEGER, thought_tokens INTEGER, cached_tokens INTEGER,
          reservation_microusd INTEGER NOT NULL, settled_microusd INTEGER,
          provider_request_id TEXT UNIQUE, provider_response_id TEXT UNIQUE,
          state TEXT NOT NULL, created_at REAL NOT NULL, dispatched_at REAL,
          settled_at REAL, error_code TEXT, response_checksum TEXT,
          pricing_version TEXT NOT NULL,
          FOREIGN KEY(retry_of) REFERENCES requests(request_id)
        );
        CREATE INDEX IF NOT EXISTS requests_state ON requests(state);
        """)

    def _tx(self):
        try: self.db.execute("BEGIN IMMEDIATE")
        except sqlite3.Error as exc: raise AccountingHalt("ledger lock unavailable") from exc
    def _rollback(self):
        try: self.db.execute("ROLLBACK")
        except sqlite3.Error: pass

    def reserved_total(self) -> int:
        row = self.db.execute("SELECT COALESCE(SUM(reservation_microusd),0) n FROM requests WHERE state NOT IN ('SETTLED','RELEASED')").fetchone()
        return int(row[0])
    def settled_total(self) -> int:
        return int(self.db.execute("SELECT COALESCE(SUM(settled_microusd),0) n FROM requests WHERE state='SETTLED'").fetchone()[0])

    def reserve(self, *, campaign_id, phase_id, run_id, stage_id, member_id, tool_turn_id, attempt_id,
                model, thinking_level, reservation_microusd, retry_of=None) -> Reservation:
        if reservation_microusd <= 0: raise LedgerError("reservation must be positive")
        if model != MODEL_ID or thinking_level != THINKING_LEVEL:
            raise LedgerError("model policy rejected")
        rid = uuid.uuid4().hex
        self._tx()
        try:
            current = self.reserved_total() + self.settled_total()
            allowed = self.ceiling if self.recovery_enabled else min(self.ceiling, NORMAL_CEILING_MICROUSD)
            if current + reservation_microusd > allowed: raise AccountingHalt("campaign ceiling reached")
            self.db.execute("INSERT INTO requests (request_id,campaign_id,phase_id,run_id,stage_id,member_id,tool_turn_id,attempt_id,retry_of,model,thinking_level,input_tokens,output_tokens,thought_tokens,cached_tokens,reservation_microusd,settled_microusd,provider_request_id,provider_response_id,state,created_at,dispatched_at,settled_at,error_code,response_checksum,pricing_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (rid,campaign_id,phase_id,run_id,stage_id,member_id,tool_turn_id,attempt_id,retry_of,
               model,thinking_level,None,None,None,None,reservation_microusd,None,None,None,'RESERVED',time.time(),None,None,None,None,PRICING_VERSION))
            self.db.execute("COMMIT")
            return Reservation(rid, reservation_microusd)
        except AccountingHalt:
            self._rollback(); raise
        except sqlite3.Error as exc:
            self._rollback(); raise AccountingHalt("reservation failed; dispatch halted") from exc

    def mark_dispatched(self, request_id: str, provider_request_id: str):
        if not provider_request_id or not isinstance(provider_request_id, str): raise LedgerError("provider request ID required")
        self._tx()
        try:
            cur=self.db.execute("UPDATE requests SET state='DISPATCHED', dispatched_at=?, provider_request_id=? WHERE request_id=? AND state='RESERVED'",(time.time(),provider_request_id,request_id))
            if cur.rowcount != 1: raise AccountingHalt("request is not reservable")
            self.db.execute("COMMIT")
        except AccountingHalt: self._rollback(); raise
        except sqlite3.Error as exc: self._rollback(); raise AccountingHalt("dispatch accounting failed") from exc

    def settle(self, request_id: str, *, model: str, input_tokens: int, output_tokens: int, thought_tokens: int,
               cached_tokens: int, provider_response_id: str, finish_reason: str, response_bytes: bytes = b"",
               pricing_version: str = PRICING_VERSION):
        values=(input_tokens,output_tokens,thought_tokens,cached_tokens)
        if not all(isinstance(x,int) and x >= 0 for x in values) or not provider_response_id: raise AccountingHalt("invalid usage; reservation retained")
        settled=cost_microdollars(input_tokens,output_tokens,thought_tokens)
        checksum=hashlib.sha256(response_bytes).hexdigest() if response_bytes else None
        self._tx()
        try:
            row=self.db.execute("SELECT * FROM requests WHERE request_id=?",(request_id,)).fetchone()
            if row is None: raise LedgerError("unknown request")
            if row['state']=='SETTLED':
                if row['provider_response_id']==provider_response_id: self._rollback(); return
                raise AccountingHalt("duplicate request has conflicting response")
            if model != row['model'] or pricing_version != row['pricing_version'] or settled > row['reservation_microusd'] or not finish_reason:
                raise AccountingHalt("response failed accounting validation")
            self.db.execute("UPDATE requests SET state='SETTLED', input_tokens=?, output_tokens=?, thought_tokens=?, cached_tokens=?, settled_microusd=?, provider_response_id=?, settled_at=?, response_checksum=? WHERE request_id=? AND state IN ('RESERVED','DISPATCHED')",(*values,settled,provider_response_id,time.time(),checksum,request_id))
            self.db.execute("COMMIT")
        except (AccountingHalt,LedgerError): self._rollback(); raise
        except sqlite3.Error as exc: self._rollback(); raise AccountingHalt("settlement failed; reservation retained") from exc

    def summary(self) -> dict:
        reserved=self.reserved_total(); settled=self.settled_total()
        unresolved=int(self.db.execute("SELECT COUNT(*) FROM requests WHERE state NOT IN ('SETTLED','RELEASED')").fetchone()[0])
        effective=min(self.ceiling, NORMAL_CEILING_MICROUSD) if not self.recovery_enabled else self.ceiling
        return {'ceiling_microusd':self.ceiling,'effective_ceiling_microusd':effective,
                'reserved_microusd':reserved,'settled_microusd':settled,
                'unresolved_requests':unresolved,'remaining_microusd':self.ceiling-reserved-settled,
                'remaining_effective_microusd':effective-reserved-settled}
    def export(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM requests ORDER BY created_at,request_id")]
    def checksum(self) -> str:
        payload=json.dumps(self.export(),sort_keys=True,separators=(',',':')).encode()
        return hashlib.sha256(payload).hexdigest()
    def close(self): self.db.close()
