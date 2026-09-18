"""Bridges prospective_runtime's BudgetBroker protocol onto the real,
audited gemini_campaign.Ledger, instead of a fake/no-op broker.

This is the per-request counterpart of campaign_ledger_adapter.py: that one
lets prospective_campaign's block-level admission talk to the real ledger;
this one lets prospective_runtime's Gemini transport do the same, at the
individual-request granularity reserve()/settle() actually price.

Two field-shape translations happen here, not upstream, because they are
provider/wire-format facts about the REST response, not campaign policy:
- serviceTier comes back as "STANDARD" (validated in transport.py's own
  _parse); the ledger's settlement check is exactly lowercase "standard".
- modelVersion comes back with a provider-controlled version suffix (e.g.
  "gemini-3.8-flash-001", also validated in transport.py); the ledger's
  MODEL_ID check is the campaign's frozen, unversioned model contract, so
  the constant is passed, not the versioned string.
"""
from __future__ import annotations

from gemini_campaign.config import MODEL_ID, THINKING_LEVEL
from gemini_campaign.ledger import Ledger

from prospective_runtime.transport import DispatchReceipt, Reservation, RequestContext, UsageMetadata


class LedgerBudgetBroker:
    """Implements prospective_runtime.transport.BudgetBroker via the real Ledger."""

    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def reserve(self, *, context: RequestContext, request_hash: str,
               max_output_tokens: int) -> Reservation:
        real = self.ledger.reserve(
            allocation_id=context.allocation_id, campaign_id=context.campaign_id,
            phase_id=context.phase_id, run_id=context.run_id, stage_id=context.stage_id,
            member_id=context.member_id, tool_turn_id=context.turn_id,
            attempt_id=context.attempt_id, model=MODEL_ID, thinking_level=THINKING_LEVEL,
            max_output_tokens=max_output_tokens, input_bound=context.trusted_input_token_bound,
            retry_of=context.retry_of,
        )
        return Reservation(reservation_id=real.request_id, request_hash=request_hash)

    def dispatch(self, *, reservation: Reservation, receipt: DispatchReceipt) -> None:
        self.ledger.mark_dispatched(reservation.reservation_id)

    def settle(self, *, reservation: Reservation, usage: UsageMetadata, finish_reason: str) -> None:
        self.ledger.settle(
            reservation.reservation_id, model=MODEL_ID, service_tier=usage.service_tier.lower(),
            input_tokens=usage.prompt_tokens, candidate_tokens=usage.candidates_tokens,
            thought_tokens=usage.thoughts_tokens, cached_tokens=usage.cached_content_tokens,
            total_tokens=usage.total_tokens, provider_response_id=usage.response_id,
            finish_reason=finish_reason,
        )

    def unresolved(self, *, reservation: Reservation, reason: str) -> None:
        # The ledger already keeps an un-settled reservation retained by
        # design (no hidden retries; see Ledger.settle()/AccountingHalt).
        # There is nothing to roll back or free here.
        pass
