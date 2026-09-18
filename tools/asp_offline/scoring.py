from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from .geometry import distance


def score_viewpoint(
    *,
    object_gain: float,
    room_gain: float,
    distance_m: float,
    visible_predictions: Iterable[float] = (),
    lambda_room: float = 1.0,
    lambda_distance: float = 0.2,
    beta: float = 0.0,
    calibrator: Optional[Callable[[float], float]] = None,
) -> float:
    """Compute U(x)=I_object+lambda_room I_room-lambda_d d-beta R.

    lambda_room/lambda_distance default to the author's own values, not
    invented ones - read from active_semantic_perception/exploration/
    config/pipeline_config.yaml on tyrone: UNCERTAINTY_ROOM_WEIGHT=1.0,
    MOVE_COST_LAMBDA=0.2. beta is the proposed risk term's own weight
    (not an ASP parameter - 0.0 recovers plain ASP scoring).

    `calibrator` is an uncalibrated-support passthrough when None: `supports`
    is used as raw ensemble support s_j (fraction of K completions
    containing a node), with no monotone map applied. A real calibrator
    reaches this argument via `fit_leave_one_scene_out`/`fit_loso_calibrator`
    (calibration.py/support_policy.py), which requires reference graphs for
    at least 4 scenes rotated 3-vs-1 per IMPLEMENTATION_RESEARCH.md section
    4.2 - as of 2026-09-15 all 4 scenes (00069, 00573, 00853, 00871) have
    one, so a real LOSO fit is computable and used by
    `extension_policy_replay.py`/`decision_replay.py` (DEVIATIONS.md
    #61-62/#65-66). Any run that passes calibrator=None is still reporting
    an UNCALIBRATED support-threshold policy, not the paper's proposed
    calibration - label it that way in any output/report, never as
    "calibration-only"."""
    supports = list(visible_predictions)
    if calibrator is not None:
        supports = [calibrator(s) for s in supports]
    risk = sum(1.0 - max(0.0, min(1.0, s)) for s in supports) / len(supports) if supports else 0.0
    return float(object_gain) + lambda_room * float(room_gain) - lambda_distance * float(distance_m) - beta * risk
