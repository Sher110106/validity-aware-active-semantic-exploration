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
    lambda_distance: float = 1.0,
    beta: float = 0.0,
    calibrator: Optional[Callable[[float], float]] = None,
) -> float:
    """Compute U(x)=I_object+lambda_room I_room-lambda_d d-beta R."""
    supports = list(visible_predictions)
    if calibrator is not None:
        supports = [calibrator(s) for s in supports]
    risk = sum(1.0 - max(0.0, min(1.0, s)) for s in supports) / len(supports) if supports else 0.0
    return float(object_gain) + lambda_room * float(room_gain) - lambda_distance * float(distance_m) - beta * risk
