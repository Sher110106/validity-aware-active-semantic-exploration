"""Spend meter for the Claude replay: price table, cost per call, caps, ledger.

Design
- One price table (PRICES) names its source and date. A model that is not in
  the table raises UnknownModel; nothing is ever priced at zero by default.
- Haiku 5.5 has two rate cards, split by prompt length. The skill says "prompt
  is 100K tokens or fewer" and does not say whether cached tokens count, so we
  count input + cache write + cache read (the safe reading, it can only
  overcharge us on paper).
- Before each call the caller reserves an amount (the measured p99 call cost;
  DEFAULT_RESERVE_USD holds placeholders until the smoke test measures it). A
  call is refused if settled + held + reserve would pass any cap. When the call
  ends, the reserve is replaced by the real cost from `usage`.
- A call that fails after the stream may have started is booked at its reserve
  (status "failed_estimated"). A call the API rejected before generation (429,
  400, ...) is released at zero cost.
- Caps: per member, per run (this process), per model (whole ledger) and per
  campaign (whole ledger). The ledger file is read at start, so a restart
  keeps the campaign totals.
- `admit_member` gates the start of a member. It needs headroom for the
  member's expected cost and for every member already running, so a cap stop
  falls between whole members.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

PRICE_SOURCE = (
    "claude-api skill 2.1.322 (bundled): SKILL.md 'Current Models (cached: 2026-11-03)', "
    "shared/models.md, shared/model-migration.md (Opus 5.5, Sonnet 5.5, Haiku 5.5 sections). "
    "Not checked against the live pricing page: no network."
)
PRICE_DATE = "2026-11-13"

# Haiku 5.5: "$0.10 / $0.50 when the prompt is 100K tokens or fewer, $0.50 / $2.50 above".
LONG_PROMPT_TOKENS = 100_000


@dataclass(frozen=True)
class RateCard:
    """USD per million tokens."""

    input: float
    output: float
    cache_read: float
    cache_write_5m: float
    cache_write_1h: float


@dataclass(frozen=True)
class ModelPrice:
    model: str
    card: RateCard
    long_card: Optional[RateCard] = None  # used when prompt tokens > long_threshold
    long_threshold: Optional[int] = None


PRICES: dict[str, ModelPrice] = {
    # Opus 5.5: $4 / $20; 5m write $5, 1h write $8; cache read $0.20 (0.05x).
    "claude-opus-5-5": ModelPrice(
        "claude-opus-5-5",
        RateCard(input=4.00, output=20.00, cache_read=0.20, cache_write_5m=5.00, cache_write_1h=8.00),
    ),
    # Haiku 5.5: cache read 0.1x, 5m write 1.25x, 1h write 2x of the input rate of the card in force.
    "claude-haiku-5-5": ModelPrice(
        "claude-haiku-5-5",
        RateCard(input=0.10, output=0.50, cache_read=0.01, cache_write_5m=0.125, cache_write_1h=0.20),
        long_card=RateCard(input=0.50, output=2.50, cache_read=0.05, cache_write_5m=0.625, cache_write_1h=1.00),
        long_threshold=LONG_PROMPT_TOKENS,
    ),
    # Sonnet 5.5: $2 / $10; 5m write $2.50, 1h write $4; cache read $0.10. Not used by the plan (replay cut).
    "claude-sonnet-5-5": ModelPrice(
        "claude-sonnet-5-5",
        RateCard(input=2.00, output=10.00, cache_read=0.10, cache_write_5m=2.50, cache_write_1h=4.00),
    ),
}

# PLACEHOLDERS. Replace with the measured p99 call cost / member cost after the smoke test
# (plan M3). They are deliberately high.
DEFAULT_RESERVE_USD = {"claude-opus-5-5": 1.00, "claude-haiku-5-5": 0.15, "claude-sonnet-5-5": 0.50}
DEFAULT_ADMIT_USD = {"claude-opus-5-5": 2.00, "claude-haiku-5-5": 0.20, "claude-sonnet-5-5": 1.00}
DEFAULT_MEMBER_CAP_USD = {"claude-opus-5-5": 8.00, "claude-haiku-5-5": 0.80, "claude-sonnet-5-5": 4.00}


class UnknownModel(KeyError):
    pass


def get_price(model: str) -> ModelPrice:
    try:
        return PRICES[model]
    except KeyError:
        raise UnknownModel(f"no price for model {model!r}; known: {sorted(PRICES)}") from None


def _as_dict(obj) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return dict(vars(obj))


@dataclass
class Usage:
    input_tokens: int = 0
    cache_write_5m: int = 0
    cache_write_1h: int = 0
    cache_read: int = 0
    output_tokens: int = 0  # includes thinking tokens

    @property
    def cache_write(self) -> int:
        return self.cache_write_5m + self.cache_write_1h

    @property
    def prompt_tokens(self) -> int:
        return self.input_tokens + self.cache_write + self.cache_read

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "cache_write": self.cache_write,
            "cache_write_5m": self.cache_write_5m,
            "cache_write_1h": self.cache_write_1h,
            "cache_read": self.cache_read,
            "output_tokens": self.output_tokens,
            "prompt_tokens": self.prompt_tokens,
        }

    @classmethod
    def from_api(cls, usage, default_ttl: str = "5m") -> "Usage":
        """Build from an API usage object or dict. Cache writes split by TTL when the API says so."""
        d = _as_dict(usage)
        cc = _as_dict(d.get("cache_creation"))
        total_create = int(d.get("cache_creation_input_tokens") or 0)
        w5 = int(cc.get("ephemeral_5m_input_tokens") or 0)
        w1 = int(cc.get("ephemeral_1h_input_tokens") or 0)
        rest = total_create - w5 - w1
        if rest > 0:  # no breakdown (or a partial one): price the rest at the TTL we asked for
            if default_ttl == "1h":
                w1 += rest
            else:
                w5 += rest
        return cls(
            input_tokens=int(d.get("input_tokens") or 0),
            cache_write_5m=w5,
            cache_write_1h=w1,
            cache_read=int(d.get("cache_read_input_tokens") or 0),
            output_tokens=int(d.get("output_tokens") or 0),
        )


def call_cost(model: str, usage: Usage) -> tuple[float, dict]:
    """USD cost of one call and a dict naming the rate card used."""
    price = get_price(model)
    long_tier = price.long_card is not None and usage.prompt_tokens > (price.long_threshold or 0)
    card = price.long_card if long_tier else price.card
    cost = (
        usage.input_tokens * card.input
        + usage.cache_write_5m * card.cache_write_5m
        + usage.cache_write_1h * card.cache_write_1h
        + usage.cache_read * card.cache_read
        + usage.output_tokens * card.output
    ) / 1e6
    return cost, {"tier": "long" if long_tier else "standard", "prompt_tokens": usage.prompt_tokens}


class CapStop(RuntimeError):
    """A cap would be passed. `scope` is member, run, model or campaign."""

    def __init__(self, scope: str, limit: float, settled: float, held: float, need: float):
        self.scope, self.limit, self.settled, self.held, self.need = scope, limit, settled, held, need
        super().__init__(
            f"cap stop [{scope}]: settled {settled:.6f} + held {held:.6f} + need {need:.6f} > cap {limit:.6f}"
        )


@dataclass
class Caps:
    member: Optional[float] = None  # overrides the per-model default member cap when set
    run: Optional[float] = None
    campaign: Optional[float] = None
    by_model: dict = field(default_factory=dict)  # model -> cap over the whole ledger


@dataclass
class Reservation:
    rid: int
    model: str
    member_key: str
    kind: str  # "call" or "prewarm"
    amount: float


_EPS = 1e-9


class Meter:
    def __init__(self, ledger_path, *, caps: Optional[Caps] = None, reserve_usd=None, admit_usd=None,
                 clock=time.time):
        self.ledger_path = Path(ledger_path)
        self.caps = caps or Caps()
        self._reserve = {**DEFAULT_RESERVE_USD, **(reserve_usd or {})}
        self._admit = {**DEFAULT_ADMIT_USD, **(admit_usd or {})}
        self._clock = clock
        self._cond = threading.Condition(threading.RLock())
        self._next_rid = 0
        self.settled_run = 0.0
        self.settled_campaign = 0.0
        self.settled_model: dict[str, float] = {}
        self.settled_member: dict[str, float] = {}
        self.held_total = 0.0
        self.held_model: dict[str, float] = {}
        self.held_member: dict[str, float] = {}
        self._inflight_model: dict[str, int] = {}
        self.stopped: Optional[CapStop] = None
        self.ledger_bad_lines = 0
        self._load_ledger()

    # ---- ledger -------------------------------------------------------
    def _load_ledger(self) -> None:
        if not self.ledger_path.exists():
            return
        with open(self.ledger_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    cost = float(rec.get("cost", 0.0))
                except (ValueError, TypeError):
                    self.ledger_bad_lines += 1
                    continue
                self.settled_campaign += cost
                m = rec.get("model")
                if m:
                    self.settled_model[m] = self.settled_model.get(m, 0.0) + cost

    def _write(self, rec: dict) -> None:
        rec = {"ts": round(self._clock(), 3), **rec}
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_path, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())

    # ---- limits -------------------------------------------------------
    def reserve_for(self, model: str) -> float:
        get_price(model)
        return self._reserve[model]

    def admit_for(self, model: str) -> float:
        get_price(model)
        return self._admit[model]

    def member_cap_for(self, model: str) -> Optional[float]:
        if self.caps.member is not None:
            return self.caps.member
        return DEFAULT_MEMBER_CAP_USD.get(model)

    def _scopes(self, model: str, member_key: str, kind: str):
        if kind == "call":
            yield ("member", self.member_cap_for(model), self.settled_member.get(member_key, 0.0),
                   self.held_member.get(member_key, 0.0))
        yield ("run", self.caps.run, self.settled_run, self.held_total)
        yield ("model", self.caps.by_model.get(model), self.settled_model.get(model, 0.0),
               self.held_model.get(model, 0.0))
        yield ("campaign", self.caps.campaign, self.settled_campaign, self.held_total)

    # ---- calls --------------------------------------------------------
    def reserve(self, model: str, member_key: str, *, kind: str = "call", amount: Optional[float] = None) -> Reservation:
        amt = self.reserve_for(model) if amount is None else amount
        with self._cond:
            for scope, limit, settled, held in self._scopes(model, member_key, kind):
                if limit is not None and settled + held + amt > limit + _EPS:
                    err = CapStop(scope, limit, settled, held, amt)
                    if scope != "member" and self.stopped is None:
                        self.stopped = err
                    raise err
            self._next_rid += 1
            res = Reservation(self._next_rid, model, member_key, kind, amt)
            self.held_total += amt
            self.held_model[model] = self.held_model.get(model, 0.0) + amt
            self.held_member[member_key] = self.held_member.get(member_key, 0.0) + amt
            return res

    def _unhold(self, res: Reservation) -> None:
        self.held_total -= res.amount
        self.held_model[res.model] = self.held_model.get(res.model, 0.0) - res.amount
        self.held_member[res.member_key] = self.held_member.get(res.member_key, 0.0) - res.amount

    def _book(self, res: Reservation, cost: float) -> None:
        self.settled_run += cost
        self.settled_campaign += cost
        self.settled_model[res.model] = self.settled_model.get(res.model, 0.0) + cost
        self.settled_member[res.member_key] = self.settled_member.get(res.member_key, 0.0) + cost

    def settle(self, res: Reservation, usage: Usage, *, request_id=None, served_model=None, stop_reason=None,
               turn=None, extra: Optional[dict] = None) -> float:
        cost, info = call_cost(res.model, usage)
        with self._cond:
            self._unhold(res)
            self._book(res, cost)
            self._write({
                "kind": res.kind, "status": "ok", "model": res.model, "member": res.member_key, "turn": turn,
                "request_id": request_id, "served_model": served_model, "stop_reason": stop_reason,
                **usage.to_dict(), "tier": info["tier"], "cost": round(cost, 9), "reserve": res.amount,
                **(extra or {}),
            })
            self._cond.notify_all()
        return cost

    def settle_failed(self, res: Reservation, error: str, *, turn=None, extra: Optional[dict] = None) -> float:
        """The call broke after it may have been billed: book the reserve as an estimate."""
        cost = res.amount
        with self._cond:
            self._unhold(res)
            self._book(res, cost)
            self._write({
                "kind": res.kind, "status": "failed_estimated", "model": res.model, "member": res.member_key,
                "turn": turn, "error": error[:300], "cost": round(cost, 9), "reserve": res.amount,
                **(extra or {}),
            })
            self._cond.notify_all()
        return cost

    def release(self, res: Reservation, why: str, *, turn=None, extra: Optional[dict] = None) -> None:
        """The API rejected the call before generating: no charge."""
        with self._cond:
            self._unhold(res)
            self._write({
                "kind": res.kind, "status": "not_billed", "model": res.model, "member": res.member_key,
                "turn": turn, "why": why[:200], "cost": 0.0, "reserve": res.amount, **(extra or {}),
            })
            self._cond.notify_all()

    # ---- members ------------------------------------------------------
    def admit_member(self, model: str, member_key: str, *, wait: bool = True) -> None:
        """Start a member only if the caps leave room for it and for all members already running.

        If room is short and others are running, wait for one to end, then look again.
        If nothing is running and room is still short, raise CapStop (a clean stop between members).
        """
        one = self.admit_for(model)
        with self._cond:
            while True:
                running_need = sum(self._admit[m] * c for m, c in self._inflight_model.items())
                running_model = self._inflight_model.get(model, 0)
                blocked = None
                for scope, limit, settled, held, need in (
                    ("run", self.caps.run, self.settled_run, self.held_total, running_need + one),
                    ("model", self.caps.by_model.get(model), self.settled_model.get(model, 0.0),
                     self.held_model.get(model, 0.0), one * (running_model + 1)),
                    ("campaign", self.caps.campaign, self.settled_campaign, self.held_total, running_need + one),
                ):
                    if limit is not None and settled + held + need > limit + _EPS:
                        blocked = CapStop(scope, limit, settled, held, need)
                        break
                if blocked is None:
                    self._inflight_model[model] = running_model + 1
                    return
                if not wait or not self._inflight_model:  # nothing running to wait for
                    if self.stopped is None:
                        self.stopped = blocked
                    raise blocked
                self._cond.wait(timeout=0.5)

    def end_member(self, model: str, member_key: str) -> None:
        with self._cond:
            n = self._inflight_model.get(model, 0)
            if n <= 1:
                self._inflight_model.pop(model, None)
            else:
                self._inflight_model[model] = n - 1
            self._cond.notify_all()

    def summary(self) -> dict:
        with self._cond:
            return {
                "settled_run_usd": round(self.settled_run, 6),
                "settled_campaign_usd": round(self.settled_campaign, 6),
                "settled_by_model_usd": {m: round(v, 6) for m, v in self.settled_model.items()},
                "stopped": str(self.stopped) if self.stopped else None,
                "price_source": PRICE_SOURCE,
                "price_date": PRICE_DATE,
            }
