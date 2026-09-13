from __future__ import annotations

import math
from typing import Iterable, Optional, Tuple

from .models import Node, Vec3

AABB = Tuple[Vec3, Vec3]


def finite_vec(v: Optional[Vec3]) -> bool:
    return v is not None and all(math.isfinite(x) for x in v)


def aabb(node: Node) -> Optional[AABB]:
    if not finite_vec(node.center) or not finite_vec(node.dimensions):
        return None
    assert node.center is not None and node.dimensions is not None
    if any(d < 0 or not math.isfinite(d) for d in node.dimensions):
        return None
    lo = tuple(c - d / 2 for c, d in zip(node.center, node.dimensions))
    hi = tuple(c + d / 2 for c, d in zip(node.center, node.dimensions))
    return lo, hi


def overlaps(a: AABB, b: AABB, *, tolerance: float = 0.0) -> bool:
    return all(a[0][i] < b[1][i] - tolerance and b[0][i] < a[1][i] - tolerance for i in range(3))


def contains(box: AABB, point: Vec3, *, tolerance: float = 1e-6) -> bool:
    return all(box[0][i] - tolerance <= point[i] <= box[1][i] + tolerance for i in range(3))


def distance(a: Vec3, b: Vec3) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def segment_intersects_aabb(start: Vec3, end: Vec3, box: AABB) -> bool:
    """Slab test for an inclusive segment/AABB intersection."""
    t_min, t_max = 0.0, 1.0
    delta = tuple(end[i] - start[i] for i in range(3))
    for i in range(3):
        if abs(delta[i]) < 1e-12:
            if start[i] < box[0][i] or start[i] > box[1][i]:
                return False
            continue
        t1 = (box[0][i] - start[i]) / delta[i]
        t2 = (box[1][i] - start[i]) / delta[i]
        t1, t2 = min(t1, t2), max(t1, t2)
        t_min, t_max = max(t_min, t1), min(t_max, t2)
        if t_min > t_max:
            return False
    return True
