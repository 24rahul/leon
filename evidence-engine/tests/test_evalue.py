"""E-value closed form (VanderWeele & Ding)."""

import math

import pytest

from evidence_engine.estimator.evalue import evalue_for_rr, rr_from_or


def test_point_evalue_known_value():
    # RR=2 -> E = 2 + sqrt(2*1) = 3.4142...
    ev = evalue_for_rr(2.0)
    assert ev.point == pytest.approx(2 + math.sqrt(2), rel=1e-4)


def test_symmetry_below_one():
    # RR=0.5 should give the same E-value as RR=2 (1/0.5).
    assert evalue_for_rr(0.5).point == pytest.approx(evalue_for_rr(2.0).point, rel=1e-6)


def test_ci_containing_null_gives_unit_evalue():
    ev = evalue_for_rr(1.8, ci_low=0.9, ci_high=3.0)
    assert ev.ci_limit == 1.0


def test_ci_excluding_null_uses_near_bound():
    ev = evalue_for_rr(2.0, ci_low=1.2, ci_high=3.5)
    # CI E-value is computed at the lower bound 1.2 (nearer the null).
    expected = 1.2 + math.sqrt(1.2 * 0.2)
    assert ev.ci_limit == pytest.approx(expected, rel=1e-4)


def test_or_to_rr_conversions():
    assert rr_from_or(4.0, rare_outcome=True) == 4.0
    assert rr_from_or(4.0, rare_outcome=False) == pytest.approx(2.0)
