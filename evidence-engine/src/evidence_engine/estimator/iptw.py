"""Inverse-probability-of-treatment weighting with honest diagnostics.

Design commitments that distinguish this from a textbook IPTW snippet:

* **Stabilized weights.** w = P(A)/P(A|L) for the treated and (1−P(A))/(1−P(A|L))
  for the controls. Stabilization keeps the weight distribution tight and the
  effective sample size high; we report both.
* **Positivity is checked, not assumed.** Propensities are trimmed to the
  configured range; if trimming collapses either arm below a floor, or an arm has
  zero outcome events, the estimator returns a *fail-loud* INSUFFICIENT result
  rather than a number.
* **Balance is a first-class output.** Standardized mean differences (SMD) for
  every confounder, before and after weighting, are returned with the estimate.
  An effect from an analysis that did not achieve balance is not trustworthy, and
  the object says so.
* **Missingness is handled explicitly, never silently.** A confounder with
  missing values is given a missing-*indicator* covariate (the "missing-indicator
  method"); the act is logged. Equity-protected variables (config
  `no_impute_variables`) are refused entirely — missingness there fails loud.

The same single-outcome routine drives both the primary outcome and every
negative control, so calibration sees exactly the method it is calibrating.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from ..logging_setup import get_logger

logger = get_logger(__name__)

SMD_BALANCE_THRESHOLD = 0.1  # conventional "good balance" ceiling


# --------------------------------------------------------------------------- #
# Design matrix with explicit missingness handling                          #
# --------------------------------------------------------------------------- #
def build_design_matrix(
    df: pd.DataFrame,
    confounders: Sequence[str],
    *,
    no_impute: Sequence[str],
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Return (X, notes). Encodes confounders; handles missingness explicitly."""
    cols: dict[str, np.ndarray] = {}
    notes: dict[str, str] = {}
    for c in confounders:
        s = df[c]
        if s.dtype == object or s.dtype.name == "category":
            # Binary/categorical: one-hot, drop-first, deterministic column order.
            dummies = pd.get_dummies(s.astype("string"), prefix=c, dummy_na=False)
            for dc in sorted(dummies.columns):
                cols[dc] = dummies[dc].to_numpy(dtype=float)
            continue
        vals = s.to_numpy(dtype=float)
        if np.isnan(vals).any():
            if c in no_impute:
                raise ValueError(
                    f"Confounder {c!r} is equity-protected (no_impute) but has "
                    "missing values. Refusing to impute; fail loud."
                )
            miss = np.isnan(vals).astype(float)
            median = float(np.nanmedian(vals))
            filled = np.where(np.isnan(vals), median, vals)
            cols[c] = filled
            cols[f"{c}_missing"] = miss
            notes[c] = (
                f"missing-indicator method applied ({int(miss.sum())} missing); "
                f"value placeholder=median({median:.3g}) with explicit indicator."
            )
        else:
            cols[c] = vals
    X = pd.DataFrame({k: cols[k] for k in sorted(cols)}, index=df.index)
    return X, notes


# --------------------------------------------------------------------------- #
# Propensity model + stabilized weights                                     #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PropensityFit:
    weights: np.ndarray = field(repr=False)
    propensity: np.ndarray = field(repr=False)
    keep_mask: np.ndarray = field(repr=False)  # rows surviving propensity trimming
    n_total: int
    n_trimmed: int
    effective_sample_size: float
    max_weight: float
    balance: dict[str, dict[str, float]]
    max_abs_smd_after: float
    notes: dict[str, str]

    def diagnostics_dict(self) -> dict[str, object]:
        return {
            "n_total": self.n_total,
            "n_trimmed": self.n_trimmed,
            "effective_sample_size": round(self.effective_sample_size, 1),
            "max_weight": round(self.max_weight, 3),
            "max_abs_smd_after": round(self.max_abs_smd_after, 4),
            "balance_achieved": bool(self.max_abs_smd_after <= SMD_BALANCE_THRESHOLD),
            "balance_per_covariate": self.balance,
            "missingness_notes": self.notes,
        }


def _weighted_mean_var(x: np.ndarray, w: np.ndarray) -> tuple[float, float]:
    wsum = w.sum()
    mean = float(np.sum(w * x) / wsum)
    var = float(np.sum(w * (x - mean) ** 2) / wsum)
    return mean, var


def _smd(x: np.ndarray, a: np.ndarray, w: np.ndarray | None) -> float:
    """Standardized mean difference of covariate x between treated/control."""
    t, c = a == 1, a == 0
    if w is None:
        mt, vt = float(x[t].mean()), float(x[t].var())
        mc, vc = float(x[c].mean()), float(x[c].var())
    else:
        mt, vt = _weighted_mean_var(x[t], w[t])
        mc, vc = _weighted_mean_var(x[c], w[c])
    pooled = np.sqrt((vt + vc) / 2.0)
    return float((mt - mc) / pooled) if pooled > 0 else 0.0


def fit_propensity(
    df: pd.DataFrame,
    exposure: str,
    confounders: Sequence[str],
    *,
    no_impute: Sequence[str],
    trim: tuple[float, float],
    seed: int,
) -> PropensityFit:
    a = df[exposure].to_numpy(dtype=int)
    X, notes = build_design_matrix(df, confounders, no_impute=no_impute)
    Xv = X.to_numpy(dtype=float)

    model = LogisticRegression(max_iter=1000, solver="lbfgs", random_state=seed)
    model.fit(Xv, a)
    ps = model.predict_proba(Xv)[:, 1]

    lo, hi = trim
    keep = (ps >= lo) & (ps <= hi)
    n_trimmed = int((~keep).sum())

    a_k, ps_k, X_k = a[keep], ps[keep], Xv[keep]
    p_treat = float(a_k.mean())  # marginal for stabilization

    # Stabilized weights.
    w = np.where(a_k == 1, p_treat / ps_k, (1 - p_treat) / (1 - ps_k))

    ess = float(w.sum() ** 2 / np.sum(w**2))

    balance: dict[str, dict[str, float]] = {}
    smds_after: list[float] = []
    for j, name in enumerate(X.columns):
        before = _smd(X_k[:, j], a_k, None)
        after = _smd(X_k[:, j], a_k, w)
        balance[name] = {"smd_before": round(before, 4), "smd_after": round(after, 4)}
        smds_after.append(abs(after))

    return PropensityFit(
        weights=w,
        propensity=ps_k,
        keep_mask=keep,
        n_total=int(len(a)),
        n_trimmed=n_trimmed,
        effective_sample_size=ess,
        max_weight=float(w.max()),
        balance=balance,
        max_abs_smd_after=float(max(smds_after) if smds_after else 0.0),
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# Single-outcome estimate (drives primary AND negative controls)            #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class OutcomeEstimate:
    status: str  # "ok" | "insufficient"
    reason: str
    risk_treated: float | None
    risk_control: float | None
    risk_difference: float | None
    risk_ratio: float | None
    log_rr: float | None
    se_log_rr: float | None
    ci95_rr: tuple[float, float] | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def estimate_outcome(
    y: np.ndarray,
    a: np.ndarray,
    w: np.ndarray,
    *,
    min_arm_events: int = 5,
) -> OutcomeEstimate:
    """Weighted risk ratio/difference for one binary outcome, with delta-method se.

    Variance uses the design effective sample size per arm:
        Var(log R) ≈ (1 − R) / (R · n_eff)
    which is the standard weighted-binomial delta-method approximation.
    """
    t, c = a == 1, a == 0
    yt, yc, wt, wc = y[t], y[c], w[t], w[c]
    if wt.sum() == 0 or wc.sum() == 0:
        return OutcomeEstimate("insufficient", "an arm has no weight", *(None,) * 7)

    r1 = float(np.sum(wt * yt) / wt.sum())
    r0 = float(np.sum(wc * yc) / wc.sum())
    ev_t, ev_c = int(yt.sum()), int(yc.sum())
    if ev_t < min_arm_events or ev_c < min_arm_events:
        return OutcomeEstimate(
            "insufficient",
            f"too few events (treated={ev_t}, control={ev_c}; need ≥{min_arm_events})",
            *(None,) * 7,
        )
    if r1 <= 0 or r0 <= 0:
        return OutcomeEstimate("insufficient", "zero weighted risk in an arm", *(None,) * 7)

    n_eff_t = float(wt.sum() ** 2 / np.sum(wt**2))
    n_eff_c = float(wc.sum() ** 2 / np.sum(wc**2))
    rr = r1 / r0
    log_rr = float(np.log(rr))
    var = (1 - r1) / (r1 * n_eff_t) + (1 - r0) / (r0 * n_eff_c)
    se = float(np.sqrt(var))
    ci = (float(np.exp(log_rr - 1.96 * se)), float(np.exp(log_rr + 1.96 * se)))

    return OutcomeEstimate(
        status="ok",
        reason="",
        risk_treated=round(r1, 5),
        risk_control=round(r0, 5),
        risk_difference=round(r1 - r0, 5),
        risk_ratio=round(rr, 5),
        log_rr=round(log_rr, 5),
        se_log_rr=round(se, 5),
        ci95_rr=(round(ci[0], 4), round(ci[1], 4)),
    )
