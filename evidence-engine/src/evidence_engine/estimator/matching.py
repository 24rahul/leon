"""Propensity-score matching estimator (a different failure mode from weighting).

1:1 greedy nearest-neighbour matching on the logit of the propensity score, within
a caliper of 0.2 standard deviations of the logit PS (the Austin convention).
Matching and IPTW fail differently — matching discards unmatched units and is
sensitive to caliper choice; IPTW reweights and is sensitive to extreme weights —
so agreement between them is informative triangulation, not redundancy.

The SE uses the delta method on the matched cohort's two-by-two risks. This treats
the matched set as a cohort, which slightly understates uncertainty (it ignores the
matching step); for the concurrence panel — where the question is sign and rough
magnitude agreement — that is adequate and clearly documented.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd

from .iptw import OutcomeEstimate

_Z = 1.959964


def estimate_matching(
    df_kept: pd.DataFrame,
    exposure: str,
    y: np.ndarray,
    propensity: np.ndarray,
    *,
    caliper_sd: float = 0.2,
    min_arm_events: int = 5,
) -> OutcomeEstimate:
    a = df_kept[exposure].to_numpy(dtype=int)
    ps = np.clip(propensity, 1e-6, 1 - 1e-6)
    logit = np.log(ps / (1 - ps))
    caliper = caliper_sd * float(np.std(logit))
    if caliper <= 0:
        return OutcomeEstimate("insufficient", "degenerate propensity (no spread)", *(None,) * 7)

    treated = np.where(a == 1)[0]
    control = np.where(a == 0)[0]
    if treated.size == 0 or control.size == 0:
        return OutcomeEstimate("insufficient", "an arm is empty", *(None,) * 7)

    # Greedy 1:1 nearest-neighbour without replacement, treated processed in a
    # deterministic order (by logit PS) so the result is reproducible.
    order = treated[np.argsort(logit[treated])]
    ctrl_logit = logit[control]
    used = np.zeros(control.size, dtype=bool)
    m_treated: list[int] = []
    m_control: list[int] = []
    for t in order:
        diffs = np.abs(ctrl_logit - logit[t])
        diffs[used] = np.inf
        j = int(np.argmin(diffs))
        if diffs[j] <= caliper:
            used[j] = True
            m_treated.append(int(t))
            m_control.append(int(control[j]))

    n_pairs = len(m_treated)
    if n_pairs < 10:
        return OutcomeEstimate("insufficient", f"only {n_pairs} matched pairs", *(None,) * 7)

    yt = y[np.array(m_treated)]
    yc = y[np.array(m_control)]
    if yt.sum() < min_arm_events or yc.sum() < min_arm_events:
        return OutcomeEstimate("insufficient", "too few matched events", *(None,) * 7)

    r1, r0 = float(yt.mean()), float(yc.mean())
    if r1 <= 0 or r0 <= 0:
        return OutcomeEstimate("insufficient", "zero matched risk", *(None,) * 7)

    log_rr = math.log(r1 / r0)
    se = math.sqrt((1 - r1) / (n_pairs * r1) + (1 - r0) / (n_pairs * r0))
    ci = (math.exp(log_rr - _Z * se), math.exp(log_rr + _Z * se))
    return OutcomeEstimate(
        status="ok",
        reason=f"{n_pairs} matched pairs (caliper={caliper:.3g} on logit PS)",
        risk_treated=round(r1, 5),
        risk_control=round(r0, 5),
        risk_difference=round(r1 - r0, 5),
        risk_ratio=round(r1 / r0, 5),
        log_rr=round(log_rr, 5),
        se_log_rr=round(se, 5),
        ci95_rr=(round(ci[0], 4), round(ci[1], 4)),
    )
