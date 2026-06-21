"""Augmented IPW — a doubly-robust estimator (the second leg of triangulation).

IPTW relies entirely on a correct propensity model. The augmented (AIPW)
estimator adds an outcome-regression term and is *doubly robust*: it is consistent
if EITHER the propensity model OR the outcome model is correct. Reporting an
association that agrees under IPTW (propensity-only) AND AIPW (doubly robust) is
real triangulation — see DESIGN_CRITIQUE §1 and the multi-estimator roadmap.

For a binary outcome we estimate the two counterfactual means by their efficient
influence functions (EIF):

    ψ1_i = m1(X_i) + A_i/π_i · (Y_i − m1(X_i))          → μ1 = mean(ψ1)
    ψ0_i = m0(X_i) + (1−A_i)/(1−π_i) · (Y_i − m0(X_i))  → μ0 = mean(ψ0)

with π the propensity and m_a a T-learner outcome model (separate logistic fits in
each arm). The EIF gives an *analytic, semiparametric-efficient* standard error
for log(μ1/μ0):

    IF_i = (ψ1_i − μ1)/μ1 − (ψ0_i − μ0)/μ0 ,   Var(log RR) = mean(IF²)/n

No bootstrap is needed for the AIPW SE; the influence function is exact.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .iptw import OutcomeEstimate, build_design_matrix


def _fit_predict_arm(
    X_arm: np.ndarray, y_arm: np.ndarray, X_all: np.ndarray, seed: int
) -> np.ndarray | None:
    """T-learner: fit a logistic outcome model in one arm, predict for everyone.

    Returns None if the arm is degenerate (single outcome class), which the caller
    turns into a fail-loud insufficient result rather than a fabricated constant.
    """
    if np.unique(y_arm).size < 2:
        return None
    model = LogisticRegression(max_iter=1000, solver="lbfgs", random_state=seed)
    model.fit(X_arm, y_arm)
    return model.predict_proba(X_all)[:, 1]


def estimate_aipw(
    df_kept: pd.DataFrame,
    exposure: str,
    confounders: Sequence[str],
    y: np.ndarray,
    propensity: np.ndarray,
    *,
    no_impute: Sequence[str],
    seed: int,
    min_arm_events: int = 5,
) -> OutcomeEstimate:
    a = df_kept[exposure].to_numpy(dtype=int)
    n = a.size
    ev_t, ev_c = int(y[a == 1].sum()), int(y[a == 0].sum())
    if ev_t < min_arm_events or ev_c < min_arm_events:
        return OutcomeEstimate(
            "insufficient",
            f"too few events for AIPW (treated={ev_t}, control={ev_c})",
            *(None,) * 7,
        )

    X, _ = build_design_matrix(df_kept, confounders, no_impute=no_impute)
    Xv = X.to_numpy(dtype=float)

    m1 = _fit_predict_arm(Xv[a == 1], y[a == 1], Xv, seed)
    m0 = _fit_predict_arm(Xv[a == 0], y[a == 0], Xv, seed)
    if m1 is None or m0 is None:
        return OutcomeEstimate("insufficient", "degenerate outcome model in an arm", *(None,) * 7)

    ps = np.clip(propensity, 1e-6, 1 - 1e-6)
    psi1 = m1 + a / ps * (y - m1)
    psi0 = m0 + (1 - a) / (1 - ps) * (y - m0)
    mu1, mu0 = float(psi1.mean()), float(psi0.mean())
    if mu1 <= 0 or mu0 <= 0:
        return OutcomeEstimate("insufficient", "non-positive counterfactual risk (AIPW)", *(None,) * 7)

    rr = mu1 / mu0
    log_rr = float(np.log(rr))
    influence = (psi1 - mu1) / mu1 - (psi0 - mu0) / mu0
    se = float(np.sqrt(np.mean(influence**2) / n))
    ci = (float(np.exp(log_rr - 1.96 * se)), float(np.exp(log_rr + 1.96 * se)))

    return OutcomeEstimate(
        status="ok",
        reason="",
        risk_treated=round(mu1, 5),
        risk_control=round(mu0, 5),
        risk_difference=round(mu1 - mu0, 5),
        risk_ratio=round(rr, 5),
        log_rr=round(log_rr, 5),
        se_log_rr=round(se, 5),
        ci95_rr=(round(ci[0], 4), round(ci[1], 4)),
    )
