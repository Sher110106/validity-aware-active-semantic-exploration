"""Waypoint logic for coverage_tour.py (the author-protocol reference, APR).

Everything here is plain Python and numpy. The simulator enters only through
two callables, so tests run without habitat or ROS:
  snap(point)  -> the nearest navmesh point (non-finite if there is none)
  dist(a, b)   -> geodesic distance from a to b (inf if no path)
Points are habitat-frame (x, y, z) with y up. "Horizontal" means x and z.
Python 3.9 compatible: the host container runs 3.9.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

import numpy as np

MODES = ("a", "b")
DEFAULT_SPACING_M = 1.5
DEFAULT_ARCHIVE_EVERY = 10
FLOOR_TOLERANCE_M = 0.5   # kept points lie within this of the start floor
MAX_SNAP_M = 0.75         # a grid point may move at most this far to reach the navmesh
MIN_SEPARATION_M = 0.75   # a point this close to a kept point is a duplicate


@dataclass(frozen=True)
class TourSettings:
    mode: str = "a"
    spacing: float = DEFAULT_SPACING_M
    archive_every: int = DEFAULT_ARCHIVE_EVERY
    max_waypoints: Optional[int] = None
    waypoints_out: Optional[str] = None
    summary_out: Optional[str] = None


def _env_value(environ, name):
    value = environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse(environ, name, default, cast):
    raw = _env_value(environ, name)
    if raw is None:
        return default
    try:
        return cast(raw)
    except ValueError:
        raise ValueError(f"{name} must be {cast.__name__}, got {raw!r}") from None


def read_settings(environ) -> TourSettings:
    """Read the APR_* variables. An unset or empty variable takes its default."""
    mode = (_env_value(environ, "APR_MODE") or "a").lower()
    if mode not in MODES:
        raise ValueError(f"APR_MODE must be 'a' or 'b', got {mode!r}")
    spacing = _parse(environ, "APR_SPACING", DEFAULT_SPACING_M, float)
    if not (math.isfinite(spacing) and spacing > 0):
        raise ValueError(f"APR_SPACING must be a positive number, got {spacing!r}")
    archive_every = _parse(environ, "APR_ARCHIVE_EVERY", DEFAULT_ARCHIVE_EVERY, int)
    if archive_every < 1:
        raise ValueError(f"APR_ARCHIVE_EVERY must be at least 1, got {archive_every!r}")
    max_waypoints = _parse(environ, "APR_MAX_WAYPOINTS", None, int)
    if max_waypoints is not None and max_waypoints < 1:
        raise ValueError(f"APR_MAX_WAYPOINTS must be at least 1, got {max_waypoints!r}")
    return TourSettings(
        mode=mode,
        spacing=spacing,
        archive_every=archive_every,
        max_waypoints=max_waypoints,
        waypoints_out=_env_value(environ, "APR_WAYPOINTS_OUT"),
        summary_out=_env_value(environ, "APR_SUMMARY_OUT"),
    )


def _axis(lo, hi, spacing):
    if not (math.isfinite(lo) and math.isfinite(hi)) or hi < lo:
        return np.empty(0)
    count = int(math.floor((hi - lo) / spacing + 1e-9)) + 1
    return lo + spacing * np.arange(count)


def grid_points(lower, upper, spacing, y) -> np.ndarray:
    """Grid over the x and z bounds at height y, x-major. Shape (N, 3)."""
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    xs = _axis(float(lower[0]), float(upper[0]), spacing)
    zs = _axis(float(lower[2]), float(upper[2]), spacing)
    gx, gz = np.meshgrid(xs, zs, indexing="ij")
    return np.column_stack([gx.ravel(), np.full(gx.size, float(y)), gz.ravel()])


def horizontal_distance(a, b) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[2]) - float(b[2]))


def select_waypoints(grid, snap, dist_from_start, floor_y,
                     floor_tolerance=FLOOR_TOLERANCE_M, max_snap=MAX_SNAP_M,
                     min_separation=MIN_SEPARATION_M):
    """Snap each grid point and keep the usable ones, in grid order.

    A point is dropped when, checked in this order:
      not navigable: the snap is not finite, or its height is not within
        floor_tolerance of floor_y, or it moved more than max_snap horizontally;
      unreachable:   dist_from_start(snapped) is not finite;
      duplicate:     it lies within min_separation (horizontal, inclusive) of a kept point.
    Returns (kept points as an (K, 3) array of snapped points, counts).
    """
    kept: List[np.ndarray] = []
    counts = {"grid_points": int(len(grid)), "dropped_not_navigable": 0,
              "dropped_unreachable": 0, "dropped_duplicates": 0}
    for point in grid:
        snapped = np.asarray(snap(point), dtype=float)
        if snapped.shape != (3,) or not np.all(np.isfinite(snapped)):
            counts["dropped_not_navigable"] += 1
        elif abs(snapped[1] - floor_y) >= floor_tolerance:
            counts["dropped_not_navigable"] += 1
        elif horizontal_distance(snapped, point) > max_snap:
            counts["dropped_not_navigable"] += 1
        elif not math.isfinite(float(dist_from_start(snapped))):
            counts["dropped_unreachable"] += 1
        elif any(horizontal_distance(snapped, k) <= min_separation for k in kept):
            counts["dropped_duplicates"] += 1
        else:
            kept.append(snapped)
    counts["kept"] = len(kept)
    return (np.array(kept) if kept else np.empty((0, 3))), counts


def order_waypoints(points, start, dist: Callable, mode="a") -> List[int]:
    """Visit order, as indices into points.

    Mode "a": greedy nearest by dist, chaining from start.
    Mode "b": the first stop is the point farthest from start; then greedy nearest.
    Ties go to the lower index. A non-finite distance never wins a nearest or
    farthest pick unless nothing else is left.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be 'a' or 'b', got {mode!r}")
    pts = [np.asarray(p, dtype=float) for p in points]
    remaining = list(range(len(pts)))
    order: List[int] = []
    here = np.asarray(start, dtype=float)

    def nearness(i):
        d = float(dist(here, pts[i]))
        return d if math.isfinite(d) else math.inf

    def farness(i):
        d = float(dist(here, pts[i]))
        return d if math.isfinite(d) else -math.inf

    if mode == "b" and remaining:
        first = max(remaining, key=farness)
        remaining.remove(first)
        order.append(first)
        here = pts[first]
    while remaining:
        nxt = min(remaining, key=nearness)
        remaining.remove(nxt)
        order.append(nxt)
        here = pts[nxt]
    return order


def plan_tour(lower, upper, start, floor_y, snap, dist, spacing=DEFAULT_SPACING_M,
              mode="a", max_waypoints=None):
    """Grid, filter, dedupe and order. Returns (waypoints (K, 3) in visit order, counts).

    max_waypoints keeps only the first stops of the full order, for a short dry run.
    """
    start = np.asarray(start, dtype=float)
    grid = grid_points(lower, upper, spacing, floor_y)
    kept, counts = select_waypoints(grid, snap, lambda p: dist(start, p), floor_y)
    order = order_waypoints(kept, start, dist, mode)
    if max_waypoints is not None:
        order = order[:max_waypoints]
    counts.update({"mode": mode, "spacing_m": float(spacing), "floor_y": float(floor_y),
                   "listed": len(order), "max_waypoints": max_waypoints})
    return (kept[order] if order else np.empty((0, 3))), counts


def densify(points, step=0.1) -> List[np.ndarray]:
    """Points every step metres or less along a polyline, ends included."""
    pts = [np.asarray(p, dtype=float) for p in points]
    out = pts[:1]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.ceil(float(np.linalg.norm(b - a)) / step)))
        out.extend(a + (b - a) * (k / n) for k in range(1, n + 1))
    return out


def should_copy_dsg(stage: int, every: int, final: bool = False) -> bool:
    """Copy the DSG files at stages 0, every, 2*every, ... and at the final stage."""
    return final or stage % every == 0


def tally(outcomes: Iterable[str]) -> Dict[str, int]:
    """Count waypoint outcomes: reached, unreachable, and the rest (pending, navigating)."""
    counts = {"reached": 0, "unreachable": 0, "unfinished": 0}
    for outcome in outcomes:
        if outcome in ("reached", "unreachable"):
            counts[outcome] += 1
        else:
            counts["unfinished"] += 1
    return counts


def _json_default(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"not JSON serializable: {type(obj).__name__}")


def write_json_atomic(path: str, data, indent=None) -> None:
    """Write JSON next to path, then rename, so a reader never sees half a file.

    indent=None gives the same bytes as json.dump(data, f), which the explorer uses.
    """
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=indent, default=_json_default)
    os.replace(tmp, path)
