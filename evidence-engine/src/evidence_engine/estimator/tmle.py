"""Targeted maximum likelihood estimation (TMLE) — doubly robust, EIF inference.

TMLE combines an outcome model and the propensity into a single targeted estimate
that is (a) doubly robust — consistent if either model is right — and (b)
asymptotically efficient, with a standard error read directly off the efficient
influence function. It updates an initial outcome fit with a one-dimensional
"fluctuation" along the clever covariate so the efficient-influence-function score
is solved exactly.

    Q0(a, X) = P(Y=1 | A=a, X)            initial outcome model
    g(X)     = P(A=1 | X)                  propensity (reused from the IPTW fit)
    H(a, X)  = a/g(X) − (1−a)/(1−g(X))     clever covariate
    logit Q*(a,X) = logit Q0(a,X) + ε·H(a,X)   ε from a no-intercept logistic fit
    μ_a = mean_i Q*(a, X_i),  RR = μ1/μ0

The log-RR influence function combines the two arms' efficient influence functions
exactly as in AIPW, giving an analytic SE (no bootstrap).
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .iptw import OutcomeEstimate, build_design_matrix

_Z = 1.959964


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _expit(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


def estimate_tmle(
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
    if y[a == 1].sum() < min_arm_events or y[a == 0].sum() < min_arm_events:
        return OutcomeEstimate("insufficient", "too few events for TMLE", *(None,) * 7)
    if np.unique(y).size < 2:
        return OutcomeEstimate("insufficient", "degenerate outcome", *(None,) * 7)

    X, _ = build_design_matrix(df_kept, confounders, no_impute=no_impute)
    Xv = X.to_numpy(dtype=float)
    g = np.clip(propensity, 1e-6, 1 - 1e-6)

    # Initial outcome model Q0 over [X, A].
    design = np.column_stack([Xv, a.astype(float)])
    q_model = LogisticRegression(max_iter=1000, solver="lbfgs", random_state=seed)
    q_model.fit(design, y)
    q_aX = q_model.predict_proba(design)[:, 1]
    q1 = q_model.predict_proba(np.column_stack([Xv, np.ones(n)]))[:, 1]
    q0 = q_model.predict_proba(np.column_stack([Xv, np.zeros(n)]))[:, 1]

    # Clever covariate and targeting fluctuation (no-intercept logistic on H with
    # offset logit(Q0)). Solve for epsilon by a short Newton iteration.
    h_aX = np.where(a == 1, 1.0 / g, -1.0 / (1.0 - g))
    h1 = 1.0 / g
    h0 = -1.0 / (1.0 - g)
    offset = _logit(q_aX)
    eps = 0.0
    for _ in range(50):
        p = _expit(offset + eps * h_aX)
        score = float(np.sum(h_aX * (y - p)))
        info = float(np.sum(h_aX**2 * p * (1 - p)))
        if info < 1e-12:
            break
        step = score / info
        eps += step
        if abs(step) < 1e-10:
            break

    q_aX_star = _expit(offset + eps * h_aX)
    q1_star = _expit(_logit(q1) + eps * h1)
    q0_star = _expit(_logit(q0) + eps * h0)
    mu1, mu0 = float(q1_star.mean()), float(q0_star.mean())
    if mu1 <= 0 or mu0 <= 0:
        return OutcomeEstimate("insufficient", "non-positive TMLE risk", *(None,) * 7)

    # Efficient influence functions for each counterfactual mean.
    eif1 = h1 * (a == 1) * (y - q_aX_star) + q1_star - mu1
    eif0 = (-h0) * (a == 0) * (y - q_aX_star) + q0_star - mu0
    # (a==1)/g and (a==0)/(1-g) recovered via h1, -h0 indicators above.
    rr = mu1 / mu0
    log_rr = math.log(rr)
    influence = eif1 / mu1 - eif0 / mu0
    se = float(np.sqrt(np.mean(influence**2) / n))
    ci = (math.exp(log_rr - _Z * se), math.exp(log_rr + _Z * se))
    return OutcomeEstimate(
        status="ok",
        reason=f"targeted (epsilon={eps:.3g})",
        risk_treated=round(mu1, 5),
        risk_control=round(mu0, 5),
        risk_difference=round(mu1 - mu0, 5),
        risk_ratio=round(rr, 5),
        log_rr=round(log_rr, 5),
        se_log_rr=round(se, 5),
        ci95_rr=(round(ci[0], 4), round(ci[1], 4)),
    )
