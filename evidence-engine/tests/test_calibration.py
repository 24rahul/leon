"""Empirical-null calibration recovers ~zero bias and fails loud when underpowered."""

import numpy as np

from evidence_engine.estimator.calibration import calibrate, fit_empirical_null


def test_fit_recovers_near_null():
    rng = np.random.default_rng(0)
    n = 50
    ses = rng.uniform(0.1, 0.3, n)
    # True systematic error: small positive bias mu=0.1, tau=0.05.
    estimates = rng.normal(0.1, np.sqrt(ses**2 + 0.05**2))
    null = fit_empirical_null(estimates, ses, min_controls=10)
    assert null.fitted
    assert abs(null.mu - 0.1) < 0.1
    assert null.tau >= 0


def test_underpowered_panel_fails_loud():
    null = fit_empirical_null(np.array([0.1, 0.2]), np.array([0.2, 0.2]), min_controls=10)
    assert not null.fitted
    cal = calibrate(0.5, 0.2, null)
    # Calibration refuses to produce a calibrated estimate.
    assert cal.calibrated_log_rr is None
    assert cal.calibrated_p_value is None


def test_calibration_widens_interval():
    rng = np.random.default_rng(1)
    n = 40
    ses = rng.uniform(0.1, 0.2, n)
    estimates = rng.normal(0.0, np.sqrt(ses**2 + 0.1**2))
    null = fit_empirical_null(estimates, ses, min_controls=10)
    cal = calibrate(0.6, 0.15, null)
    assert cal.calibrated_se is not None and cal.calibrated_se >= 0.15
