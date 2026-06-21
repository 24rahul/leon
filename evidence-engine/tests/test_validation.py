"""The validation harness must itself be correct: known truth, biased crude,
unbiased adjusted, improved calibration, and a passing overall verdict."""

import math

import pytest

from evidence_engine.validation.dgp import DGP
from evidence_engine.validation.simulation import (
    calibration_study,
    judge,
    recovery_study,
)


def test_dgp_truth_matches_conditional_rr_without_clipping():
    # With low baseline risk and modest RR there is no probability clipping, so the
    # marginal RR equals the conditional multiplier to high precision.
    dgp = DGP(rr_cond=1.6)
    assert math.isclose(dgp.true_marginal_rr(), 1.6, rel_tol=0.02)


def test_crude_is_biased_and_adjustment_removes_it():
    dgp = DGP(rr_cond=1.6)
    res = recovery_study(dgp, true_rrs=(1.6,), n=2500, reps=40, seed=11)[0]
    crude_bias = abs(res.metrics["crude"].bias_log)
    iptw_bias = abs(res.metrics["iptw"].bias_log)
    aipw_bias = abs(res.metrics["aipw"].bias_log)
    assert crude_bias > 0.15, "crude should be visibly confounded"
    assert iptw_bias < 0.05, "IPTW should be ~unbiased"
    assert aipw_bias < 0.05, "AIPW should be ~unbiased"
    assert crude_bias > iptw_bias + 0.07


def test_adjusted_coverage_is_near_nominal():
    dgp = DGP(rr_cond=1.3)
    res = recovery_study(dgp, true_rrs=(1.3,), n=2500, reps=60, seed=5)[0]
    # Loose band for the small replication count used in the test.
    assert 0.88 <= res.metrics["iptw"].coverage <= 0.99


def test_calibration_improves_negative_control_coverage():
    cal = calibration_study(n=3000, n_controls=40, datasets=3, gamma_u=0.5, seed=2)
    assert cal.coverage_raw < 0.9, "residual confounding should hurt raw coverage"
    assert cal.coverage_calibrated > cal.coverage_raw
    assert cal.coverage_calibrated >= 0.9


@pytest.mark.slow
def test_overall_verdict_passes():
    recovery = recovery_study(DGP(), n=3000, reps=120, seed=20240617)
    calibration = calibration_study(datasets=6)
    verdict = judge(recovery, calibration)
    failed = [c for c in verdict.checks if not c["pass"]]
    assert verdict.passed, f"validation checks failed: {failed}"
