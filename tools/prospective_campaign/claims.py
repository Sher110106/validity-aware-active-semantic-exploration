"""Finite, typed preregistered scientific claim gates."""
from __future__ import annotations

import math
from .contract import EXPERIMENTAL


def _metric(value: object, *, nonnegative: bool = False) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value): return None
    if nonnegative and value < 0: return None
    return float(value)


def claim_gate(*, experimental_policy: str, complete_pairs: int, complete_block: bool,
               invalid_hypothesis_ok: bool, detour_receipt_valid: bool,
               fp_detour_reduction: object, baseline_detour: object,
               f1_loss: object, ged_increase: object) -> dict[str, str]:
    if experimental_policy != EXPERIMENTAL: return {"status": "not_established", "reason": "wrong experimental policy"}
    if complete_pairs != 3 or not complete_block: return {"status": "descriptive_only", "reason": "not exactly three complete pairs"}
    if not invalid_hypothesis_ok: return {"status": "not_established", "reason": "invalid-hypothesis gate failed"}
    reduction = _metric(fp_detour_reduction); baseline = _metric(baseline_detour, nonnegative=True)
    loss = _metric(f1_loss, nonnegative=True); ged = _metric(ged_increase, nonnegative=True)
    if not detour_receipt_valid or reduction is None or baseline is None or baseline <= 0:
        return {"status": "not_identifiable", "reason": "validated positive detour evidence is required"}
    if reduction <= 0 or loss is None or ged is None or loss > .05 or ged > .10:
        return {"status": "not_established", "reason": "combined usefulness thresholds failed"}
    return {"status": "established", "claim": "validator_plus_unanimity_raw_tau_1_0 paired usefulness"}
