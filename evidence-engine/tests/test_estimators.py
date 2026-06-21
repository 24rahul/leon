"""AIPW doubly-robustness, cross-estimator concurrence, and bootstrap CI."""

import numpy as np
import pandas as pd

from evidence_engine.estimator.aipw import estimate_aipw
from evidence_engine.estimator.concurrence import compare
from evidence_engine.estimator.iptw import (
    bootstrap_rr_ci,
    estimate_outcome,
    fit_propensity,
)


def _synthetic_confounded(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    age = rng.normal(0, 1, n)
    sev = rng.gamma(2.0, 1.0, n)
    ps = 1 / (1 + np.exp(-(0.6 * sev + 0.3 * age - 1.0)))
    a = (rng.random(n) < ps).astype(int)
    # True log-OR of exposure on outcome ~ 0.4; confounders raise risk too.
    logit = -2.0 + 0.5 * sev + 0.2 * age + 0.4 * a
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(float)
    df = pd.DataFrame({"x": a, "age": age, "sev": sev})
    return df, y


def test_iptw_and_aipw_recover_positive_direction():
    df, y = _synthetic_confounded()
    fit = fit_propensity(df, "x", ["age", "sev"], no_impute=[], trim=(0.02, 0.98), seed=0)
    keep = fit.keep_mask
    iptw = estimate_outcome(y[keep], df["x"].to_numpy()[keep], fit.weights)
    aipw = estimate_aipw(
        df.loc[keep], "x", ["age", "sev"], y[keep], fit.propensity, no_impute=[], seed=0
    )
    assert iptw.status == "ok" and aipw.status == "ok"
    assert iptw.risk_ratio > 1.0  # planted positive association
    assert aipw.risk_ratio > 1.0


def test_concurrence_flags_agreement_and_disagreement():
    df, y = _synthetic_confounded()
    fit = fit_propensity(df, "x", ["age", "sev"], no_impute=[], trim=(0.02, 0.98), seed=0)
    keep = fit.keep_mask
    iptw = estimate_outcome(y[keep], df["x"].to_numpy()[keep], fit.weights)
    aipw = estimate_aipw(
        df.loc[keep], "x", ["age", "sev"], y[keep], fit.propensity, no_impute=[], seed=0
    )
    agree = compare({"iptw": iptw, "aipw": aipw})
    assert agree.concordant is True
    assert agree.sign_agree is True


def test_concurrence_not_assessable_with_one_estimator():
    df, y = _synthetic_confounded()
    fit = fit_propensity(df, "x", ["age", "sev"], no_impute=[], trim=(0.02, 0.98), seed=0)
    iptw = estimate_outcome(y[fit.keep_mask], df["x"].to_numpy()[fit.keep_mask], fit.weights)
    from evidence_engine.estimator.iptw import OutcomeEstimate

    bad = OutcomeEstimate("insufficient", "n/a", *(None,) * 7)
    res = compare({"iptw": iptw, "aipw": bad})
    assert res.concordant is False
    assert res.sign_agree is None  # cannot assess


def test_bootstrap_ci_is_deterministic_and_excludes_null():
    df, y = _synthetic_confounded()
    kw = dict(no_impute=[], trim=(0.02, 0.98), seed=0, n_boot=80)
    b1 = bootstrap_rr_ci(df, "x", y, ["age", "sev"], **kw)
    b2 = bootstrap_rr_ci(df, "x", y, ["age", "sev"], **kw)
    assert b1 == b2  # same seed -> identical
    assert b1["status"] == "ok"
    assert b1["ci95_rr"][0] > 1.0  # planted positive effect excludes the null


# --- full estimator panel: matching, g-computation, TMLE -------------------
def _fit_kept(df):
    from evidence_engine.estimator.iptw import fit_propensity

    fit = fit_propensity(df, "x", ["age", "sev"], no_impute=[], trim=(0.02, 0.98), seed=0)
    return fit, fit.keep_mask


def test_matching_recovers_direction():
    from evidence_engine.estimator.matching import estimate_matching

    df, y = _synthetic_confounded()
    fit, keep = _fit_kept(df)
    est = estimate_matching(df.loc[keep], "x", y[keep], fit.propensity)
    assert est.status == "ok"
    assert est.risk_ratio > 1.0


def test_gcomputation_recovers_direction_and_is_deterministic():
    from evidence_engine.estimator.gcomputation import estimate_gcomputation

    df, y = _synthetic_confounded()
    fit, keep = _fit_kept(df)
    kw = dict(no_impute=[], seed=0, n_boot=60)
    e1 = estimate_gcomputation(df.loc[keep], "x", ["age", "sev"], y[keep], **kw)
    e2 = estimate_gcomputation(df.loc[keep], "x", ["age", "sev"], y[keep], **kw)
    assert e1.status == "ok" and e1.risk_ratio > 1.0
    assert e1.to_dict() == e2.to_dict()  # seeded bootstrap is reproducible


def test_tmle_recovers_direction_with_eif_se():
    from evidence_engine.estimator.tmle import estimate_tmle

    df, y = _synthetic_confounded()
    fit, keep = _fit_kept(df)
    est = estimate_tmle(
        df.loc[keep], "x", ["age", "sev"], y[keep], fit.propensity, no_impute=[], seed=0
    )
    assert est.status == "ok"
    assert est.risk_ratio > 1.0
    assert est.se_log_rr is not None and est.se_log_rr > 0


def test_panel_concurrence_over_five_estimators():
    from evidence_engine.estimator.aipw import estimate_aipw
    from evidence_engine.estimator.gcomputation import estimate_gcomputation
    from evidence_engine.estimator.matching import estimate_matching
    from evidence_engine.estimator.tmle import estimate_tmle

    df, y = _synthetic_confounded()
    fit, keep = _fit_kept(df)
    yk, ak = y[keep], df["x"].to_numpy()[keep]
    kf = df.loc[keep]
    panel = {
        "iptw": estimate_outcome(yk, ak, fit.weights),
        "aipw": estimate_aipw(kf, "x", ["age", "sev"], yk, fit.propensity, no_impute=[], seed=0),
        "matching": estimate_matching(kf, "x", yk, fit.propensity),
        "gcomputation": estimate_gcomputation(kf, "x", ["age", "sev"], yk, no_impute=[], seed=0, n_boot=60),
        "tmle": estimate_tmle(kf, "x", ["age", "sev"], yk, fit.propensity, no_impute=[], seed=0),
    }
    res = compare(panel)
    assert res.sign_agree is True  # all five agree on direction
    assert res.concordant is True
