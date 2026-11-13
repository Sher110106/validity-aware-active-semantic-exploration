"""Tests for tools/live_policy/semantic/stats.py (exact sign-flip test, CI, Holm, verdict).

Toy data only. The module loads by file path because tools/live_policy also holds a
live_policy.py module, and other tests import that under the same name.
"""
import importlib.util
import itertools
import math
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(__file__)
STATS = os.path.join(HERE, "..", "live_policy", "semantic", "stats.py")
_spec = importlib.util.spec_from_file_location("semantic_stats_under_test", STATS)
st = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = st  # dataclasses look the module up by name
_spec.loader.exec_module(st)


def brute_p(d, alternative):
    """Independent count over all sign patterns, with itertools and plain floats."""
    d = [float(x) for x in d]
    obs = sum(d)
    hits = total = 0
    for signs in itertools.product((1, -1), repeat=len(d)):
        s = sum(a * b for a, b in zip(signs, d))
        total += 1
        if alternative == "greater":
            hits += s >= obs - 1e-9
        elif alternative == "less":
            hits += s <= obs + 1e-9
        else:
            hits += abs(s) >= abs(obs) - 1e-9
    return hits / total


# ---- hand-worked p-values -------------------------------------------------

# n = 3, d = (1, 2, 3). The 8 flip sums are 6, 4, 2, 0, 0, -2, -4, -6.
def test_n3_all_positive():
    d = [1, 2, 3]
    assert st.sign_flip_test(d, "greater").p == pytest.approx(1 / 8)
    assert st.sign_flip_test(d, "two-sided").p == pytest.approx(2 / 8)
    assert st.sign_flip_test(d, "less").p == pytest.approx(1.0)


def test_n3_all_negative():
    d = [-1, -2, -3]
    assert st.sign_flip_test(d, "greater").p == pytest.approx(1.0)
    assert st.sign_flip_test(d, "less").p == pytest.approx(1 / 8)
    assert st.sign_flip_test(d, "two-sided").p == pytest.approx(2 / 8)


# n = 3, d = (2, -1, -1). Flip sums: 4, 2, 2, 0, 0, -2, -2, -4. Observed sum is 0, which ties 2 patterns.
def test_n3_observed_tied_at_zero():
    d = [2, -1, -1]
    assert st.sign_flip_test(d, "greater").p == pytest.approx(5 / 8)
    assert st.sign_flip_test(d, "less").p == pytest.approx(5 / 8)
    assert st.sign_flip_test(d, "two-sided").p == pytest.approx(1.0)


# n = 3, d = (3, 1, 1). Flip sums: 5, 3, 3, 1, -1, -3, -3, -5.
def test_n3_three_one_one():
    d = [3, 1, 1]
    assert st.sign_flip_test(d, "greater").p == pytest.approx(1 / 8)
    assert st.sign_flip_test(d, "two-sided").p == pytest.approx(2 / 8)


# n = 4, d = (2, 2, 1, -1). Flip sums: 6, 4, 4, 2 x3, 0 x4, -2 x3, -4 x2, -6. Observed sum 4.
def test_n4_mixed_signs():
    d = [2, 2, 1, -1]
    assert st.sign_flip_test(d, "greater").p == pytest.approx(3 / 16)
    assert st.sign_flip_test(d, "less").p == pytest.approx(15 / 16)
    assert st.sign_flip_test(d, "two-sided").p == pytest.approx(6 / 16)


# n = 4 with a zero: d = (1, 1, 2, 0). The zero stays in, so each pattern on the other three counts twice.
def test_n4_zero_cluster_stays_in():
    d = [1, 1, 2, 0]
    r = st.sign_flip_test(d, "greater")
    assert r.n == 4 and r.n_patterns == 16
    assert r.p == pytest.approx(2 / 16)
    assert st.sign_flip_test(d, "two-sided").p == pytest.approx(4 / 16)


# n = 4, d = (1, 1, 1, 1): flip sums 4, 2 x4, 0 x6, -2 x4, -4.
def test_n4_all_equal_ties():
    d = [1, 1, 1, 1]
    assert st.sign_flip_test(d, "greater").p == pytest.approx(1 / 16)
    assert st.sign_flip_test(d, "two-sided").p == pytest.approx(2 / 16)
    # d = (1, 1, 1, 0): observed sum 3; only the all-plus pattern reaches it, and the zero may flip either way.
    assert st.sign_flip_test([1, 1, 1, 0], "greater").p == pytest.approx(2 / 16)


def test_result_fields():
    r = st.sign_flip_test([1.0, 2.0, 6.0], "greater")
    assert r.statistic == pytest.approx(3.0)  # the mean
    assert r.n == 3 and r.n_patterns == 8


# ---- general properties -----------------------------------------------------

def test_p_at_least_one_over_2n_and_identity_counted():
    for n in (1, 2, 5, 9):
        d = np.arange(1, n + 1, dtype=float)  # all positive: only the identity reaches the observed sum
        assert st.sign_flip_test(d, "greater").p == pytest.approx(1 / 2**n)
        assert st.sign_flip_test(d, "greater").p > 0
    rng = np.random.default_rng(3)
    for _ in range(30):
        d = rng.normal(size=7)
        for alt in ("greater", "less", "two-sided"):
            assert st.sign_flip_test(d, alt).p >= 1 / 2**7 - 1e-15


def test_matches_independent_brute_force():
    rng = np.random.default_rng(5)
    cases = [rng.normal(size=n) for n in (1, 2, 5, 8)] + [rng.integers(-2, 3, size=8).astype(float) for _ in range(5)]
    for d in cases:
        for alt in ("greater", "less", "two-sided"):
            assert st.sign_flip_test(d, alt).p == pytest.approx(brute_p(d, alt))


def test_sign_symmetry():
    rng = np.random.default_rng(7)
    for _ in range(10):
        d = rng.integers(-3, 4, size=8).astype(float)
        g = st.sign_flip_test(d, "greater").p
        l = st.sign_flip_test(-d, "less").p
        assert g == pytest.approx(l)
        assert st.sign_flip_test(-d, "greater").p == pytest.approx(st.sign_flip_test(d, "less").p)
        assert st.sign_flip_test(d, "two-sided").p == pytest.approx(st.sign_flip_test(-d, "two-sided").p)


def test_two_sided_is_twice_smaller_one_sided_capped():
    rng = np.random.default_rng(11)
    for _ in range(10):
        d = rng.normal(size=9)
        g, l = (st.sign_flip_test(d, a).p for a in ("greater", "less"))
        assert st.sign_flip_test(d, "two-sided").p == pytest.approx(min(1.0, 2 * min(g, l)))


def test_input_checks():
    with pytest.raises(ValueError):
        st.sign_flip_test([], "greater")
    with pytest.raises(ValueError):
        st.sign_flip_test([1.0, float("nan")])
    with pytest.raises(ValueError):
        st.sign_flip_test([1.0] * 21)
    with pytest.raises(ValueError):
        st.sign_flip_test([1.0, 2.0], alternative="sideways")


def test_n20_runs_fast_and_counts_patterns():
    r = st.sign_flip_test(np.linspace(0.1, 2.0, 20), "greater")
    assert r.n_patterns == 2**20
    assert r.p == pytest.approx(1 / 2**20)


# ---- confidence interval ----------------------------------------------------

def test_ci_contains_observed_mean():
    rng = np.random.default_rng(13)
    for n in (6, 8, 12):
        d = rng.normal(0.3, 1.0, size=n)
        lo, hi = st.sign_flip_ci(d, 0.95, "two-sided")
        assert lo <= d.mean() <= hi
        lo1, hi1 = st.sign_flip_ci(d, 0.95, "greater")
        assert lo1 <= d.mean() and hi1 == math.inf
        lo2, hi2 = st.sign_flip_ci(d, 0.95, "less")
        assert lo2 == -math.inf and hi2 >= d.mean()


def test_exact_and_bisection_agree():
    rng = np.random.default_rng(17)
    cases = [rng.normal(0.4, 1.0, size=n) for n in (6, 7, 9)]
    cases.append(np.array([3.0, 1.0, 1.0, 2.0, 0.0, 5.0, 2.0]))  # ties and a zero
    for d in cases:
        for level in (0.8, 0.9, 0.95):
            for alt in ("two-sided", "greater", "less"):
                ex = st.sign_flip_ci(d, level, alt, method="exact")
                bi = st.sign_flip_ci(d, level, alt, method="bisect")
                for a, b in zip(ex, bi):
                    if math.isinf(a) or math.isinf(b):
                        assert a == b
                    else:
                        assert a == pytest.approx(b, abs=2e-9)


def test_ci_is_the_inverted_test():
    rng = np.random.default_rng(19)
    d = rng.normal(0.5, 1.0, size=8)
    lo, hi = st.sign_flip_ci(d, 0.9, "two-sided")
    eps = 1e-6
    # The one-sided p in delta rises with delta (greater) or falls (less); each tail is 0.05.
    assert st.sign_flip_test(d - lo, "greater").p >= 0.05 - 1e-12  # the edge is kept
    assert st.sign_flip_test(d - (lo + eps), "greater").p >= 0.05  # inside is kept
    assert st.sign_flip_test(d - (lo - eps), "greater").p < 0.05  # just outside rejects
    assert st.sign_flip_test(d - hi, "less").p >= 0.05 - 1e-12
    assert st.sign_flip_test(d - (hi - eps), "less").p >= 0.05
    assert st.sign_flip_test(d - (hi + eps), "less").p < 0.05
    # and the two-sided test at 0.1 agrees
    assert st.sign_flip_test(d - (lo - eps), "two-sided").p < 0.1
    assert st.sign_flip_test(d - (hi + eps), "two-sided").p < 0.1
    assert st.sign_flip_test(d - (lo + eps), "two-sided").p >= 0.1
    assert st.sign_flip_test(d - (hi - eps), "two-sided").p >= 0.1


def test_ci_duality_with_test_at_zero():
    rng = np.random.default_rng(23)
    for _ in range(40):
        d = rng.normal(rng.uniform(-1, 1), 1.0, size=8)
        lo, hi = st.sign_flip_ci(d, 0.95, "two-sided")
        keeps_zero = st.sign_flip_test(d, "two-sided").p >= 0.05
        assert (lo <= 0 <= hi) == keeps_zero


def test_ci_unbounded_when_n_too_small():
    d = [0.3, 0.5, 0.2, 0.9]
    assert st.sign_flip_ci(d, 0.95, "two-sided") == (-math.inf, math.inf)
    assert st.sign_flip_ci(d, 0.95, "two-sided", method="bisect") == (-math.inf, math.inf)
    assert st.sign_flip_ci(d, 0.95, "greater")[0] == -math.inf  # 1/16 > 0.05
    assert st.sign_flip_ci(d, 0.95, "less")[1] == math.inf
    # n = 5: one-sided 95% is finite (1/32 < 0.05); two-sided 95% is still unbounded (1/32 >= 0.025).
    d5 = [0.3, 0.5, 0.2, 0.9, 0.4]
    assert math.isfinite(st.sign_flip_ci(d5, 0.95, "greater")[0])
    assert st.sign_flip_ci(d5, 0.95, "two-sided") == (-math.inf, math.inf)
    # n = 6: two-sided 95% becomes finite on both sides.
    lo, hi = st.sign_flip_ci(d5 + [0.7], 0.95, "two-sided")
    assert math.isfinite(lo) and math.isfinite(hi)


def test_ci_hand_cases():
    # n = 5, one-sided 95%: 0.05 * 32 = 1.6, so 2 patterns must stay. The empty flip set is one, and the
    # smallest subset mean (a single smallest d) is the other. The bound is min(d).
    assert st.sign_flip_ci([1.0, 2.0, 4.0, 7.0, 8.0], 0.95, "greater")[0] == pytest.approx(1.0)
    # n = 6, two-sided 95%: 0.025 * 64 = 1.6, so again 2 patterns per tail. The interval is [min, max].
    lo, hi = st.sign_flip_ci([1, 2, 3, 4, 5, 6], 0.95, "two-sided")
    assert (lo, hi) == (pytest.approx(1.0), pytest.approx(6.0))
    # n = 7, d = 1..7, two-sided 95%: 0.025 * 128 = 3.2, so 4 patterns per tail: the empty set plus the
    # three smallest subset means 1, 1.5, 2 ({1}, {1,2}, {2}); the lower end is the third, 2. Mirror: 6.
    lo, hi = st.sign_flip_ci([1, 2, 3, 4, 5, 6, 7], 0.95, "two-sided")
    assert (lo, hi) == (pytest.approx(2.0), pytest.approx(6.0))
    lo_b, hi_b = st.sign_flip_ci([1, 2, 3, 4, 5, 6, 7], 0.95, "two-sided", method="bisect")
    assert (lo_b, hi_b) == (pytest.approx(2.0, abs=2e-9), pytest.approx(6.0, abs=2e-9))


def test_ci_input_checks():
    with pytest.raises(ValueError):
        st.sign_flip_ci([1.0, 2.0, 3.0], level=1.0)
    with pytest.raises(ValueError):
        st.sign_flip_ci([1.0, 2.0, 3.0], method="magic")


def test_exact_coverage_over_all_sign_patterns():
    # Under symmetry about 0, each sign pattern of one fixed d0 is equally likely, so coverage is exact to count.
    d0 = np.array([0.31, 0.77, 1.12, 0.05, 0.58, 0.9, 1.4, 0.2, 0.66, 0.43])
    covered = rejected = total = 0
    for signs in itertools.product((1.0, -1.0), repeat=len(d0)):
        x = np.array(signs) * d0
        lo, hi = st.sign_flip_ci(x, 0.95, "two-sided")
        covered += lo <= 0.0 <= hi
        rejected += st.sign_flip_test(x, "greater").p < 0.05
        total += 1
    assert covered / total >= 0.95
    assert rejected / total <= 0.05


def test_seeded_simulation_coverage_and_size():
    rng = np.random.default_rng(20261113)
    n, true_shift = 12, 0.5
    reps = 300
    covered = 0
    for _ in range(reps):
        d = true_shift + rng.standard_t(5, size=n)
        lo, hi = st.sign_flip_ci(d, 0.95, "two-sided")
        covered += lo <= true_shift <= hi
    cov = covered / reps
    assert 0.91 <= cov <= 1.0, cov

    reps = 1000
    rejected = sum(st.sign_flip_test(rng.normal(size=n), "greater").p < 0.05 for _ in range(reps))
    rate = rejected / reps
    assert rate <= 0.05 + 3 * math.sqrt(0.05 * 0.95 / reps), rate
    assert rate > 0.02, rate  # the exact test is not far below its level at n = 12


# ---- intersection-union and Holm -------------------------------------------

def test_intersection_union_is_max():
    assert st.intersection_union_p([0.01, 0.2, 0.03]) == 0.2
    assert st.intersection_union_p([0.04]) == 0.04
    assert st.intersection_union_p((0.5, 0.5)) == 0.5
    with pytest.raises(ValueError):
        st.intersection_union_p([])
    with pytest.raises(ValueError):
        st.intersection_union_p([0.1, 1.2])


def test_holm_hand_example_and_monotone_rule():
    out = st.holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.005})
    # sorted: d .005 -> 4x = .02; a .01 -> 3x = .03; c .03 -> 2x = .06; b .04 -> 1x = .04, lifted to .06.
    assert out == pytest.approx({"a": 0.03, "b": 0.06, "c": 0.06, "d": 0.02})
    assert list(out) == ["a", "b", "c", "d"]  # same names, same order as the input


def test_holm_ties_and_cap():
    out = st.holm({"x": 0.02, "y": 0.02, "z": 0.5})
    assert out == pytest.approx({"x": 0.06, "y": 0.06, "z": 0.5})
    # tied inputs give tied outputs whatever the dict order
    rev = st.holm({"z": 0.5, "y": 0.02, "x": 0.02})
    assert rev["x"] == rev["y"] == pytest.approx(0.06)
    capped = st.holm({"a": 0.4, "b": 0.4, "c": 0.9})
    assert capped == pytest.approx({"a": 1.0, "b": 1.0, "c": 1.0})
    assert max(capped.values()) <= 1.0


def test_holm_properties():
    rng = np.random.default_rng(29)
    for _ in range(50):
        p = {f"h{i}": float(x) for i, x in enumerate(rng.uniform(0, 0.2, size=12))}
        adj = st.holm(p)
        assert set(adj) == set(p)
        for k in p:
            assert p[k] <= adj[k] <= 1.0
        order = sorted(p, key=p.get)
        vals = [adj[k] for k in order]
        assert vals == sorted(vals)  # monotone in the raw p order
        assert min(adj.values()) == pytest.approx(min(1.0, 12 * min(p.values())))


def test_holm_edges():
    assert st.holm({}) == {}
    assert st.holm({"only": 0.03}) == {"only": 0.03}
    with pytest.raises(ValueError):
        st.holm({"a": -0.1})
    with pytest.raises(ValueError):
        st.holm({"a": float("nan")})


# ---- verdict ----------------------------------------------------------------

def test_verdict_branches_and_edges():
    assert st.verdict(0.01, 0.5, 0.05) == "Supported"  # Supported wins even if the CI is wide
    assert st.verdict(0.2, 0.01, 0.05) == "Rejected"
    assert st.verdict(0.2, 0.08, 0.05) == "Inconclusive"
    # edges
    assert st.verdict(0.05, 0.0, 0.05) == "Rejected"  # p exactly alpha is not Supported
    assert st.verdict(0.05, 0.9, 0.05) == "Inconclusive"
    assert st.verdict(0.0499999, 0.9, 0.05) == "Supported"
    assert st.verdict(0.3, 0.05, 0.05) == "Inconclusive"  # upper bound equal to delta is not below it
    assert st.verdict(0.3, 0.0499999, 0.05) == "Rejected"
    assert st.verdict(0.3, math.inf, 0.05) == "Inconclusive"
    assert st.verdict(0.3, -0.2, 0.03, alpha=0.01) == "Rejected"
    assert st.verdict(0.02, 0.5, 0.03, alpha=0.01) == "Inconclusive"
    with pytest.raises(ValueError):
        st.verdict(float("nan"), 0.0, 0.05)
    with pytest.raises(ValueError):
        st.verdict(0.1, float("nan"), 0.05)


# ---- bootstrap, detectable difference, cluster means -------------------------

def test_bootstrap_is_deterministic_for_a_seed():
    d = [0.1, -0.2, 0.4, 0.3, 0.0, 0.25, 0.15, -0.05, 0.35, 0.2, 0.1, 0.3]
    a = st.wild_cluster_bootstrap_ci(d, seed=5)
    b = st.wild_cluster_bootstrap_ci(d, seed=5)
    c = st.wild_cluster_bootstrap_ci(d, seed=6)
    assert a == b
    assert a != c
    lo, hi = a
    assert lo < np.mean(d) < hi
    wide = st.wild_cluster_bootstrap_ci(d, seed=5, level=0.99)
    assert wide[0] <= lo and wide[1] >= hi
    with pytest.raises(ValueError):
        st.wild_cluster_bootstrap_ci(d, draws=0)


def test_bootstrap_degenerate_and_scale():
    assert st.wild_cluster_bootstrap_ci([0.2] * 6, seed=1) == (pytest.approx(0.2), pytest.approx(0.2))
    rng = np.random.default_rng(31)
    d = rng.normal(0.0, 1.0, size=12)
    lo, hi = st.wild_cluster_bootstrap_ci(d, seed=0)
    se = d.std(ddof=1) / math.sqrt(12)
    assert 1.4 * se < (hi - lo) / 2 < 2.2 * se  # about 1.96 se


def test_detectable_difference_formula():
    nd = __import__("statistics").NormalDist()
    sd, n = 0.1, 12
    expected = (nd.inv_cdf(0.95) + nd.inv_cdf(0.8)) * sd / math.sqrt(n)
    assert st.detectable_difference(sd, n) == pytest.approx(expected)
    assert st.detectable_difference(sd, n) == pytest.approx(0.0718, abs=1e-3)
    # Bonferroni: the one-sided level shrinks to alpha / m
    expected12 = (nd.inv_cdf(1 - 0.05 / 12) + nd.inv_cdf(0.8)) * sd / math.sqrt(n)
    assert st.detectable_difference(sd, n, m_tests=12) == pytest.approx(expected12)
    assert st.detectable_difference(sd, n, m_tests=12) > st.detectable_difference(sd, n)
    # more clusters, smaller; more power, larger
    assert st.detectable_difference(sd, 48) == pytest.approx(st.detectable_difference(sd, 12) / 2)
    assert st.detectable_difference(sd, n, power=0.9) > st.detectable_difference(sd, n, power=0.8)
    with pytest.raises(ValueError):
        st.detectable_difference(sd, 0)
    with pytest.raises(ValueError):
        st.detectable_difference(-1.0, 5)
    with pytest.raises(ValueError):
        st.detectable_difference(sd, 5, m_tests=0)


def test_cluster_means_fixed_order():
    ids, means = st.cluster_means([1.0, 3.0, 10.0, 20.0, 5.0], ["b", "b", "a", "a", "c"])
    assert ids == ["a", "b", "c"]
    assert means == pytest.approx([15.0, 2.0, 5.0])
    # row order does not change the output order
    ids2, means2 = st.cluster_means([5.0, 20.0, 1.0, 10.0, 3.0], ["c", "a", "b", "a", "b"])
    assert ids2 == ids and means2 == pytest.approx(means)
    # integer ids sort numerically
    ids3, _ = st.cluster_means([1, 2, 3], [10, 2, 1])
    assert ids3 == [1, 2, 10]
    with pytest.raises(ValueError):
        st.cluster_means([1.0, 2.0], ["a"])
    with pytest.raises(ValueError):
        st.cluster_means([], [])
    with pytest.raises(ValueError):
        st.cluster_means([float("nan")], ["a"])


def test_cluster_means_builds_d():
    ids, llm = st.cluster_means([0.5, 0.7, 0.4, 0.6], ["r1", "r1", "r2", "r2"])
    ids_b, base = st.cluster_means([0.3, 0.3, 0.5, 0.5], ["r1", "r1", "r2", "r2"])
    assert ids == ids_b
    d = np.asarray(llm) - np.asarray(base)
    assert d == pytest.approx([0.3, 0.0])


# ---- reliability helpers (§11 readout 3)

def test_brier_and_ece_by_hand():
    p, y = [0.25, 0.25, 0.5, 1.0], [0, 1, 1, 1]
    assert st.brier_score(p, y) == pytest.approx((0.0625 + 0.5625 + 0.25 + 0.0) / 4)
    curve = st.reliability_curve(p, y)
    assert [(b["lo"], b["n"], b["mean_y"]) for b in curve] == [(0.25, 2, 0.5), (0.5, 1, 1.0), (1.0, 1, 1.0)]
    assert st.expected_calibration_error(p, y) == pytest.approx((2 * 0.25 + 1 * 0.5 + 0) / 4)
    assert st.expected_calibration_error([0.5, 0.5], [0, 1]) == 0.0           # calibrated
    with pytest.raises(ValueError):
        st.brier_score([0.5], [1, 0])


def test_reliability_curve_uses_equal_width_bins_when_there_are_many_values():
    p = [i / 20 for i in range(21)]
    curve = st.reliability_curve(p, [1 if x > 0.5 else 0 for x in p], max_bins=5)
    assert sum(b["n"] for b in curve) == 21 and len(curve) == 5 and curve[0]["lo"] == 0.0 and curve[-1]["hi"] == 1.0


def test_isotonic_map_pools_violators_and_is_monotone():
    f = st.IsotonicMap([0.25, 0.5, 0.75, 1.0], [1, 0, 1, 1])
    assert [f(x) for x in (0.25, 0.5, 0.75, 1.0)] == [0.5, 0.5, 1.0, 1.0]      # 0.25 and 0.5 pooled
    vals = [f(x / 10) for x in range(0, 13)]
    assert vals == sorted(vals)
    g = st.IsotonicMap([0.5, 0.5, 1.0], [0, 1, 1])                            # equal scores pool first
    assert g(0.5) == 0.5 and g(0.9) == 1.0 and g(2.0) == 1.0
