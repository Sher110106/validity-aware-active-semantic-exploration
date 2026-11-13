"""Exact statistics for the pre-registered semantic test.

The unit is a cluster (one robot run). For one hypothesis we hold, per cluster,
d_c = (LLM score) - (comparator score). The statistic is the mean of d_c.

- sign_flip_test: exact test. It tries every one of the 2^n ways to flip the
  signs of d, and the p-value is the share of ways whose mean is at least the
  observed mean. The unflipped pattern is one of them, so p >= 1/2^n. Ties
  count as "at least". A cluster with d = 0 stays in.
- sign_flip_ci: the interval found by inverting that test (see its docstring).
- intersection_union_p, holm: combine p-values across comparators and across
  hypotheses.
- verdict: the Supported / Rejected / Inconclusive rule.
- wild_cluster_bootstrap_ci: a secondary interval.
- detectable_difference: the smallest true mean difference the design can see.
- cluster_means: per-cluster means in a fixed order, for building d.

Only numpy and the standard library are used. Inference holds for the
clusters given and nothing beyond them.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

MAX_CLUSTERS = 20  # 2^20 = 1,048,576 patterns
_REL_EPS = 1e-12  # float slack when comparing sums, relative to sum(|d|)
_ALTERNATIVES = ("greater", "less", "two-sided")


@dataclass(frozen=True)
class SignFlipResult:
    p: float
    statistic: float  # the observed mean of d
    n: int  # clusters
    n_patterns: int  # 2^n


def _as_vector(d: Sequence[float], name: str = "d") -> np.ndarray:
    x = np.asarray(d, dtype=float)
    if x.ndim != 1 or x.size == 0:
        raise ValueError(f"{name} must be a non-empty 1-D sequence")
    if not np.all(np.isfinite(x)):
        raise ValueError(f"{name} must hold finite numbers")
    return x


def _check_alternative(alternative: str) -> None:
    if alternative not in _ALTERNATIVES:
        raise ValueError(f"alternative must be one of {_ALTERNATIVES}, got {alternative!r}")


def _check_level(level: float) -> None:
    if not (0.0 < level < 1.0):
        raise ValueError("level must lie strictly between 0 and 1")


def _subset_sums(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sum and size of every subset of x, 2^n entries each. Entry 0 is the empty subset."""
    sums = np.zeros(1)
    sizes = np.zeros(1, dtype=np.int64)
    for v in x:
        sums = np.concatenate([sums, sums + v])
        sizes = np.concatenate([sizes, sizes + 1])
    return sums, sizes


def sign_flip_test(d: Sequence[float], alternative: str = "greater") -> SignFlipResult:
    """Exact sign-flip test of "the true mean of d is 0".

    Flip the sign of every subset of clusters (2^n patterns, identity included).
    "greater": p = share of patterns with mean >= observed mean.
    "less": p = share with mean <= observed.
    "two-sided": p = share with |mean| >= |observed mean|.
    Ties count. n must be between 1 and 20.
    """
    _check_alternative(alternative)
    x = _as_vector(d)
    n = int(x.size)
    if n > MAX_CLUSTERS:
        raise ValueError(f"at most {MAX_CLUSTERS} clusters, got {n}")
    total = float(x.sum())
    eps = _REL_EPS * float(np.abs(x).sum())
    subset, _ = _subset_sums(x)
    flipped = total - 2.0 * subset  # sum of d after flipping each subset
    if alternative == "greater":
        hits = int(np.count_nonzero(flipped >= total - eps))
    elif alternative == "less":
        hits = int(np.count_nonzero(flipped <= total + eps))
    else:
        hits = int(np.count_nonzero(np.abs(flipped) >= abs(total) - eps))
    n_patterns = 1 << n
    return SignFlipResult(p=hits / n_patterns, statistic=total / n, n=n, n_patterns=n_patterns)


def _tail_count(alpha_tail: float, n_patterns: int) -> int:
    """Fewest patterns a one-sided p-value must count to stay at or above alpha_tail."""
    return max(1, math.ceil(alpha_tail * n_patterns - 1e-9))


def _exact_bounds(x: np.ndarray, alpha_tail: float, want_lower: bool, want_upper: bool) -> tuple[float, float]:
    n_patterns = 1 << int(x.size)
    need = _tail_count(alpha_tail, n_patterns)
    if need <= 1:  # the identity pattern alone reaches alpha_tail: no bound on either side
        return -math.inf, math.inf
    sums, sizes = _subset_sums(x)
    means = sums[1:] / sizes[1:]  # subset means, empty subset left out
    k = need - 2  # the empty subset takes the first place; place `need` is index need-2 here
    lower, upper = -math.inf, math.inf
    if want_lower:
        lower = float(np.partition(means, k)[k])
    if want_upper:
        j = means.size - 1 - k
        upper = float(np.partition(means, j)[j])
    return lower, upper


def _bisect_bounds(x: np.ndarray, alpha_tail: float, want_lower: bool, want_upper: bool, tol: float) -> tuple[float, float]:
    n_patterns = 1 << int(x.size)
    if 1.0 / n_patterns >= alpha_tail - 1e-12:
        return -math.inf, math.inf
    slack = 1e-12
    lower, upper = -math.inf, math.inf
    if want_lower:
        # p(greater) at shift delta rises with delta: find where it first reaches alpha_tail.
        lo, hi = float(x.min()) - 1.0, float(x.max())
        while hi - lo > tol:
            mid = 0.5 * (lo + hi)
            if sign_flip_test(x - mid, "greater").p >= alpha_tail - slack:
                hi = mid
            else:
                lo = mid
        lower = hi
    if want_upper:
        # p(less) falls as delta rises: find where it last stays at or above alpha_tail.
        lo, hi = float(x.min()), float(x.max()) + 1.0
        while hi - lo > tol:
            mid = 0.5 * (lo + hi)
            if sign_flip_test(x - mid, "less").p >= alpha_tail - slack:
                lo = mid
            else:
                hi = mid
        upper = lo
    return lower, upper


def sign_flip_ci(d: Sequence[float], level: float = 0.95, alternative: str = "two-sided",
                 method: str = "exact", tol: float = 1e-9) -> tuple[float, float]:
    """Confidence interval by inverting the sign-flip test.

    It is the set of shifts delta for which the test on (d - delta) does not
    reject. A test rejects when its p-value is below the tail level: 1 - level
    for one-sided, (1 - level) / 2 on each side for two-sided (this equals the
    two-sided test at 1 - level, because the sign-flip law is symmetric).
    "greater" returns (lower bound, inf); "less" returns (-inf, upper bound).

    The p-value of "greater" at shift delta is the share of subsets F with
    mean_F(d) <= delta (empty subset included), so it only changes at subset
    means. method="exact" reads the bound off the sorted subset means.
    method="bisect" searches to within `tol`; it exists to check the exact one.
    When 1/2^n is already at least the tail level, the test cannot reject
    anything, and that side is unbounded (math.inf).
    """
    _check_alternative(alternative)
    _check_level(level)
    if method not in ("exact", "bisect"):
        raise ValueError("method must be 'exact' or 'bisect'")
    x = _as_vector(d)
    if x.size > MAX_CLUSTERS:
        raise ValueError(f"at most {MAX_CLUSTERS} clusters, got {x.size}")
    two = alternative == "two-sided"
    alpha_tail = (1.0 - level) / 2.0 if two else 1.0 - level
    want_lower = alternative in ("greater", "two-sided")
    want_upper = alternative in ("less", "two-sided")
    if method == "exact":
        lower, upper = _exact_bounds(x, alpha_tail, want_lower, want_upper)
    else:
        lower, upper = _bisect_bounds(x, alpha_tail, want_lower, want_upper, tol)
    return (lower if want_lower else -math.inf), (upper if want_upper else math.inf)


def _check_p(p: float, what: str = "p-value") -> float:
    p = float(p)
    if not (0.0 <= p <= 1.0):  # also false for nan
        raise ValueError(f"{what} must lie in [0, 1], got {p}")
    return p


def intersection_union_p(pvalues: Sequence[float]) -> float:
    """The p-value of a hypothesis that must beat every comparator: the largest one."""
    ps = [_check_p(p) for p in pvalues]
    if not ps:
        raise ValueError("need at least one p-value")
    return max(ps)


def holm(pvalues_by_name: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values, under the same names and order.

    Sort p ascending as p(1) <= ... <= p(m). Adjusted p(j) is
    max over i <= j of min(1, (m - i + 1) * p(i)). So adjusted values never
    fall as raw p rises, none passes 1, and tied raw p-values get tied results.
    """
    names = list(pvalues_by_name)
    ps = {k: _check_p(pvalues_by_name[k], f"p-value for {k!r}") for k in names}
    m = len(names)
    order = sorted(names, key=lambda k: ps[k])
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, k in enumerate(order):
        running = max(running, min(1.0, (m - rank) * ps[k]))
        adjusted[k] = running
    return {k: adjusted[k] for k in names}


def verdict(adjusted_p: float, ci_upper_vs_strongest: float, delta: float, alpha: float = 0.05) -> str:
    """Supported if adjusted_p < alpha; else Rejected if the CI upper bound
    (LLM minus its strongest comparator) is below delta; else Inconclusive.
    Both comparisons are strict: p equal to alpha is not Supported, and an
    upper bound equal to delta is not Rejected."""
    for name, v in (("adjusted_p", adjusted_p), ("ci_upper_vs_strongest", ci_upper_vs_strongest),
                    ("delta", delta), ("alpha", alpha)):
        if math.isnan(v):
            raise ValueError(f"{name} is not a number")
    if adjusted_p < alpha:
        return "Supported"
    if ci_upper_vs_strongest < delta:
        return "Rejected"
    return "Inconclusive"


def wild_cluster_bootstrap_ci(d: Sequence[float], draws: int = 9999, seed: int = 0,
                              level: float = 0.95) -> tuple[float, float]:
    """Secondary interval for the mean of d, by a wild cluster bootstrap.

    Each draw multiplies every cluster's deviation from the mean by a random
    +1 or -1 (Rademacher weight), one weight per cluster, and recomputes the
    mean: mean + average(w_c * (d_c - mean)). The interval is the percentile
    pair of the draws. It is symmetric about the mean by construction and a
    little narrow at small n (its variance is (n - 1)/n of the usual). The
    exact sign-flip interval is the primary one. Fixed seed, fixed answer.
    """
    _check_level(level)
    if int(draws) != draws or draws < 1:
        raise ValueError("draws must be a positive integer")
    x = _as_vector(d)
    n = x.size
    mean = float(x.mean())
    resid = x - mean
    rng = np.random.default_rng(seed)
    weights = rng.integers(0, 2, size=(int(draws), n)) * 2 - 1
    stats = mean + (weights @ resid) / n
    a = (1.0 - level) / 2.0
    lo, hi = np.quantile(stats, [a, 1.0 - a])
    return float(lo), float(hi)


def detectable_difference(sd: float, n: int, alpha: float = 0.05, power: float = 0.8,
                          m_tests: int = 1) -> float:
    """Smallest true mean difference a one-sided test would detect.

    Normal approximation: MDD = (z[1 - alpha/m] + z[power]) * sd / sqrt(n),
    where sd is the standard deviation of the per-cluster differences d_c,
    n is the number of clusters, z[q] is the standard normal quantile, and
    m = m_tests. Dividing alpha by m is the Bonferroni worst case: it is the
    level the smallest p-value must clear in Holm's procedure. The exact test
    at small n is a little less powerful than this, so read it as a floor.
    """
    if not (math.isfinite(sd) and sd >= 0):
        raise ValueError("sd must be a finite number, 0 or more")
    if int(n) != n or n < 1:
        raise ValueError("n must be a positive integer")
    if not (0.0 < alpha < 1.0) or not (0.0 < power < 1.0):
        raise ValueError("alpha and power must lie strictly between 0 and 1")
    if int(m_tests) != m_tests or m_tests < 1:
        raise ValueError("m_tests must be a positive integer")
    z = statistics.NormalDist().inv_cdf
    return (z(1.0 - alpha / m_tests) + z(power)) * sd / math.sqrt(n)


def cluster_means(values: Sequence[float], cluster_ids: Sequence[Any]) -> tuple[list, np.ndarray]:
    """Mean of values within each cluster.

    Returns (ids, means): ids sorted ascending (they must be sortable), means
    in that order. Build d from two calls over the same clusters and the same
    ids come back in the same order.
    """
    x = _as_vector(values, "values")
    ids = list(cluster_ids)
    if len(ids) != x.size:
        raise ValueError("values and cluster_ids must have the same length")
    groups: dict[Any, list[float]] = {}
    for cid, v in zip(ids, x):
        groups.setdefault(cid, []).append(float(v))
    order = sorted(groups)
    return order, np.array([math.fsum(groups[c]) / len(groups[c]) for c in order])
