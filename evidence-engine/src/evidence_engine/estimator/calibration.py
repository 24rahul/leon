"""Empirical-null calibration from a negative-control panel (Schuemie et al. 2014).

A real (non-null) estimate is only believable to the extent the *same method*
returns null on a panel of controls whose true effect is known to be zero. This
module fits the method's empirical systematic-error distribution from that panel
and recalibrates the real estimate against it. See DESIGN_CRITIQUE §1.3 for why
this is categorically stronger than a refutation test alone.

Model (on the log–rate-ratio scale): for a negative control i with true effect
0, the observed estimate and its standard error satisfy

        θ̂_i  ~  Normal( μ ,  s_i² + τ² )

where μ is the method's systematic bias and τ² is its excess (over-dispersion)
variance beyond the random error s_i². We fit (μ, τ) by maximum likelihood over
the panel. A perfectly calibrated method has μ = 0, τ = 0.

Calibration of a real estimate θ̂ (se s):
    calibrated point   = θ̂ − μ
    calibrated se      = sqrt(s² + τ²)
    calibrated p-value = 2 · Φ(−|θ̂ − μ| / sqrt(s² + τ²))

We refuse to calibrate (fail loud) when the panel is too small for a stable null.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from scipy import optimize, stats


@dataclass(frozen=True)
class EmpiricalNull:
    mu: float          # systematic bias on the log scale
    tau: float         # residual SD (over-dispersion) on the log scale
    n_controls: int
    fitted: bool
    note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CalibratedEstimate:
    raw_log_rr: float
    raw_p_value: float
    calibrated_log_rr: float | None
    calibrated_se: float | None
    calibrated_p_value: float | None
    calibrated_ci95: tuple[float, float] | None  # on the RR (exp) scale
    empirical_null: EmpiricalNull

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["empirical_null"] = self.empirical_null.to_dict()
        return d


def _neg_log_likelihood(params: np.ndarray, theta: np.ndarray, s2: np.ndarray) -> float:
    mu, log_tau = params
    tau2 = math.exp(log_tau) ** 2
    var = s2 + tau2
    # Gaussian NLL up to constant.
    return float(0.5 * np.sum(np.log(2 * math.pi * var) + (theta - mu) ** 2 / var))


def fit_empirical_null(
    estimates: np.ndarray, ses: np.ndarray, *, min_controls: int
) -> EmpiricalNull:
    """Fit (μ, τ) by MLE over the negative-control panel."""
    theta = np.asarray(estimates, dtype=float)
    s = np.asarray(ses, dtype=float)
    mask = np.isfinite(theta) & np.isfinite(s) & (s > 0)
    theta, s = theta[mask], s[mask]
    n = int(theta.size)

    if n < min_controls:
        return EmpiricalNull(
            mu=float("nan"),
            tau=float("nan"),
            n_controls=n,
            fitted=False,
            note=(
                f"Only {n} usable negative controls (< {min_controls}); the "
                "empirical null is underpowered. Refusing to certify calibration."
            ),
        )

    s2 = s**2
    x0 = np.array([float(np.mean(theta)), math.log(max(np.std(theta), 1e-3))])
    res = optimize.minimize(
        _neg_log_likelihood, x0, args=(theta, s2), method="Nelder-Mead"
    )
    mu = float(res.x[0])
    tau = float(math.exp(res.x[1]))
    return EmpiricalNull(
        mu=round(mu, 5),
        tau=round(tau, 5),
        n_controls=n,
        fitted=bool(res.success),
        note="Empirical systematic-error distribution fitted from negative controls.",
    )


def calibrate(
    raw_log_rr: float,
    raw_se: float,
    null: EmpiricalNull,
) -> CalibratedEstimate:
    """Recalibrate a real estimate against the fitted empirical null."""
    z_raw = raw_log_rr / raw_se if raw_se > 0 else float("inf")
    raw_p = float(2 * stats.norm.sf(abs(z_raw)))

    if not null.fitted:
        return CalibratedEstimate(
            raw_log_rr=round(raw_log_rr, 5),
            raw_p_value=round(raw_p, 6),
            calibrated_log_rr=None,
            calibrated_se=None,
            calibrated_p_value=None,
            calibrated_ci95=None,
            empirical_null=null,
        )

    cal_point = raw_log_rr - null.mu
    cal_se = math.sqrt(raw_se**2 + null.tau**2)
    z_cal = cal_point / cal_se if cal_se > 0 else float("inf")
    cal_p = float(2 * stats.norm.sf(abs(z_cal)))
    lo = math.exp(cal_point - 1.96 * cal_se)
    hi = math.exp(cal_point + 1.96 * cal_se)

    return CalibratedEstimate(
        raw_log_rr=round(raw_log_rr, 5),
        raw_p_value=round(raw_p, 6),
        calibrated_log_rr=round(cal_point, 5),
        calibrated_se=round(cal_se, 5),
        calibrated_p_value=round(cal_p, 6),
        calibrated_ci95=(round(lo, 4), round(hi, 4)),
        empirical_null=null,
    )
