"""G-computation / standardization (outcome-model based, no propensity at all).

Fit a single outcome model Q(A, X) = P(Y=1 | A, X), then standardize: predict the
counterfactual risk for *every* unit under treatment and under control, and average.

    μ1 = mean_i Q(1, X_i),   μ0 = mean_i Q(0, X_i),   RR = μ1 / μ0

This relies entirely on the outcome model being correct — the opposite dependency
to IPTW (which relies on the propensity model). That is exactly why it belongs in a
concurrence panel: it can only agree with IPTW by luck if both models are wrong in
the same direction. The SE is a seeded nonparametric bootstrap, which honestly
reflects the uncertainty of the standardization step (a parametric delta method
would understate it).
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .iptw import OutcomeEstimate, build_design_matrix

_Z = 1.959964


def _standardized_rr(Xv: np.ndarray, a: np.ndarray, y: np.ndarray, seed: int) -> float | None:
    design = np.column_stack([Xv, a.astype(float)])
    if np.unique(y).size < 2:
        return None
    model = LogisticRegression(max_iter=1000, solver="lbfgs", random_state=seed)
    model.fit(design, y)
    x1 = np.column_stack([Xv, np.ones(Xv.shape[0])])
    x0 = np.column_stack([Xv, np.zeros(Xv.shape[0])])
    mu1 = float(model.predict_proba(x1)[:, 1].mean())
    mu0 = float(model.predict_proba(x0)[:, 1].mean())
    if mu0 <= 0 or mu1 <= 0:
        return None
    return mu1 / mu0


def estimate_gcomputation(
    df_kept: pd.DataFrame,
    exposure: str,
    confounders: Sequence[str],
    y: np.ndarray,
    *,
    no_impute: Sequence[str],
    seed: int,
    n_boot: int = 200,
    min_arm_events: int = 5,
) -> OutcomeEstimate:
    a = df_kept[exposure].to_numpy(dtype=int)
    if y[a == 1].sum() < min_arm_events or y[a == 0].sum() < min_arm_events:
        return OutcomeEstimate("insufficient", "too few events for g-computation", *(None,) * 7)

    X, _ = build_design_matrix(df_kept, confounders, no_impute=no_impute)
    Xv = X.to_numpy(dtype=float)
    point = _standardized_rr(Xv, a, y, seed)
    if point is None:
        return OutcomeEstimate("insufficient", "degenerate outcome model", *(None,) * 7)

    rng = np.random.default_rng(seed)
    n = Xv.shape[0]
    logs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        rr_b = _standardized_rr(Xv[idx], a[idx], y[idx], seed)
        if rr_b is not None:
            logs.append(math.log(rr_b))
    if len(logs) < max(20, n_boot // 2):
        return OutcomeEstimate("insufficient", "g-computation bootstrap unstable", *(None,) * 7)

    arr = np.array(logs)
    se = float(arr.std(ddof=1))
    log_rr = math.log(point)
    lo, hi = np.percentile(arr, [2.5, 97.5])
    return OutcomeEstimate(
        status="ok",
        reason=f"standardization, {len(logs)} bootstrap resamples",
        risk_treated=None,
        risk_control=None,
        risk_difference=None,
        risk_ratio=round(point, 5),
        log_rr=round(log_rr, 5),
        se_log_rr=round(se, 5),
        ci95_rr=(round(float(np.exp(lo)), 4), round(float(np.exp(hi)), 4)),
    )
