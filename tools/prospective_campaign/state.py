"""Versioned persistent paired state; restart never trusts memory or partial work."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from .contract import BASELINE, EXPERIMENTAL, ContractError
from .control import Control, EventLog, Telemetry, SLUG, atomic_json, can_continue, validate_artifacts, HEX64


class Phase(str, Enum):
    READY = "ready"; RESERVED = "reserved"; RUNNING = "running"; PAUSED = "paused"; COMPLETE = "complete"; INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class PairState:
    version: int
    campaign_id: str
    block_id: str
    pair_id: str
    run_id: str
    attempt: int
    allocation_id: str
    start_state_hash: str
    policy_hash: str
    ordered_policies: tuple[str, str]
    completed_members: tuple[str, ...]
    phase: str
    transition_sequence: int


def save_state(path: Path, state: PairState) -> None:
    if state.version != 2 or state.attempt not in (1, 2) or set(state.ordered_policies) != {BASELINE, EXPERIMENTAL}:
        raise ContractError("invalid immutable pair state")
    if any(not SLUG.fullmatch(value) for value in (state.campaign_id, state.block_id, state.pair_id, state.run_id, state.allocation_id)):
        raise ContractError("unsafe state identifier")
    if not HEX64.fullmatch(state.start_state_hash) or not HEX64.fullmatch(state.policy_hash):
        raise ContractError("invalid state hash")
    atomic_json(path, asdict(state))


def load_state(path: Path) -> PairState:
    try: raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc: raise ContractError("state cannot be loaded") from exc
    try:
        raw["ordered_policies"] = tuple(raw["ordered_policies"])
        raw["completed_members"] = tuple(raw["completed_members"])
        state = PairState(**raw)
    except (TypeError, ValueError) as exc: raise ContractError("state schema invalid") from exc
    if state.version != 2 or state.attempt not in (1, 2) or state.phase not in {p.value for p in Phase}:
        raise ContractError("state version/phase invalid")
    if set(state.ordered_policies) != {BASELINE, EXPERIMENTAL} or len(state.completed_members) > 2:
        raise ContractError("state pair members invalid")
    if any(not SLUG.fullmatch(value) for value in (state.campaign_id, state.block_id, state.pair_id, state.run_id, state.allocation_id)):
        raise ContractError("unsafe state identifier")
    if not HEX64.fullmatch(state.start_state_hash) or not HEX64.fullmatch(state.policy_hash):
        raise ContractError("invalid state hash")
    return state


class CampaignSupervisor:
    def __init__(self, status_path: Path, event_log: EventLog, runner):
        self.status_path, self.events, self.runner = status_path, event_log, runner
        self.state = load_state(status_path) if status_path.exists() else None

    def start(self, state: PairState, *, telemetry: Telemetry, control: Control) -> bool:
        if self.state is not None and self.state != state: raise ContractError("immutable state mismatch on restart")
        okay, reason = can_continue(telemetry=telemetry, control=control)
        if not okay:
            self.state = PairState(**{**asdict(state), "phase": Phase.PAUSED.value})
            save_state(self.status_path, self.state); self.events.append("pause", sequence=state.transition_sequence, run_id=state.run_id, allocation_id=state.allocation_id)
            return False
        self.state = PairState(**{**asdict(state), "phase": Phase.RUNNING.value})
        save_state(self.status_path, self.state)
        self.events.append("launch_intent", sequence=state.transition_sequence, run_id=state.run_id, allocation_id=state.allocation_id)
        return True

    def certify_member(self, run_path: Path, required: tuple[str, ...], member: str) -> bool:
        if self.state is None or member not in self.state.ordered_policies:
            return False
        if member in self.state.completed_members:
            return True  # already certified; idempotent no-op, no duplicate event
        if self.state.phase not in (Phase.RUNNING.value, Phase.RESERVED.value):
            # RUNNING: no member certified yet. RESERVED: exactly one is; the
            # other must still be certifiable or a pair could never complete.
            return False
        ok, _ = validate_artifacts(run_path, required)
        if not ok: return False
        members = tuple(dict.fromkeys((*self.state.completed_members, member)))
        self.state = PairState(**{**asdict(self.state), "completed_members": members,
                                  "phase": Phase.COMPLETE.value if len(members) == 2 else Phase.RESERVED.value,
                                  "transition_sequence": self.state.transition_sequence + 1})
        save_state(self.status_path, self.state)
        self.events.append("complete", sequence=self.state.transition_sequence, run_id=self.state.run_id, allocation_id=self.state.allocation_id)
        return True
