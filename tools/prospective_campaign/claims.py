"""Preregistered stopping-point claim gates."""
from __future__ import annotations


def claim_gate(*, complete_pairs: int, complete_block: bool, invalid_hypothesis_ok: bool,
               fp_detour_reduction: float | None, baseline_detour: float | None,
               f1_loss: float, ged_increase: float) -> dict[str, object]:
    if complete_pairs < 1:
        return {"status": "not_established", "reason": "no complete paired evidence"}
    if not complete_block:
        return {"status": "descriptive_only", "reason": "incomplete paired block"}
    if not invalid_hypothesis_ok:
        return {"status": "not_established", "reason": "invalid-hypothesis gate failed"}
    if baseline_detour == 0 or fp_detour_reduction is None:
        return {"status": "not_identifiable", "reason": "detour reduction is not identifiable"}
    if fp_detour_reduction <= 0 or f1_loss > 0.05 or ged_increase > 0.10:
        return {"status": "not_established", "reason": "combined usefulness thresholds failed"}
    return {"status": "established", "claim": "paired combined usefulness"}
