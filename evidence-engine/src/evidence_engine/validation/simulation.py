"""Monte Carlo operating-characteristics study driving the REAL estimators.

Two studies:
  * `recovery_study` — across a grid of true effects, does the pipeline recover the
    truth (low bias), is its 95% CI honest (≈95% coverage), does it control Type I
    error at the null and have power at real effects, and does it remove the
    confounding the crude estimate suffers?
  * `calibration_study` — under residual (unmeasured) confounding, does empirical-
    null calibration restore nominal coverage on a negative-control panel?

Everything is seeded and deterministic.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..estimator.aipw import estimate_aipw
from ..estimator.calibration import calibrate, fit_empirical_null
from ..estimator.iptw import OutcomeEstimate, estimate_outcome, fit_propensity
from ..estimator.units import LogRiskRatio
from .dgp import DGP

_Z = 1.959964


# --- single-dataset estimators --------------------------------------------
def _crude(df, names) -> OutcomeEstimate:
    a = df["treat"].to_numpy()
    y = df["y"].to_numpy()
    n1, n0 = int((a == 1).sum()), int((a == 0).sum())
    if n1 == 0 or n0 == 0:
        return OutcomeEstimate("insufficient", "empty arm", *(None,) * 7)
    r1, r0 = y[a == 1].mean(), y[a == 0].mean()
    if r1 <= 0 or r0 <= 0:
        return OutcomeEstimate("insufficient", "zero events", *(None,) * 7)
    log_rr = math.log(r1 / r0)
    se = math.sqrt((1 - r1) / (n1 * r1) + (1 - r0) / (n0 * r0))
    ci = (math.exp(log_rr - _Z * se), math.exp(log_rr + _Z * se))
    return OutcomeEstimate("ok", "", round(r1, 5), round(r0, 5), round(r1 - r0, 5),
                           round(r1 / r0, 5), round(log_rr, 5), round(se, 5),
                           (round(ci[0], 4), round(ci[1], 4)))


def _fit_once(df, names, seed):
    return fit_propensity(df, "treat", names, no_impute=[], trim=(0.02, 0.98), seed=seed)


def estimate_all(df, names, seed) -> dict[str, OutcomeEstimate]:
    """Crude, IPTW, and AIPW estimates for one dataset (PS fitted once)."""
    out: dict[str, OutcomeEstimate] = {"crude": _crude(df, names)}
    fit = _fit_once(df, names, seed)
    keep = fit.keep_mask
    y = df["y"].to_numpy()[keep]
    a = df["treat"].to_numpy()[keep]
    out["iptw"] = estimate_outcome(y, a, fit.weights)
    out["aipw"] = estimate_aipw(
        df.loc[keep], "treat", names, y, fit.propensity, no_impute=[], seed=seed
    )
    return out


# --- recovery study --------------------------------------------------------
@dataclass
class EstimatorMetrics:
    estimator: str
    bias_log: float
    rmse_log: float
    coverage: float
    reject_rate: float       # Type I error at null; power at a true effect
    mean_ci_width: float
    n_ok: int

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class ScenarioResult:
    true_rr: float
    true_log_rr: float
    metrics: dict[str, EstimatorMetrics]
    sign_concordance_iptw_aipw: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "true_rr": round(self.true_rr, 5),
            "true_log_rr": round(self.true_log_rr, 5),
            "sign_concordance_iptw_aipw": round(self.sign_concordance_iptw_aipw, 4),
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
        }


def _aggregate(est_logs, truths, ci_los, ci_his, truth_rr, name) -> EstimatorMetrics:
    e = np.array(est_logs)
    t = np.array(truths)
    err = e - t
    lo = np.array(ci_los)
    hi = np.array(ci_his)
    covered = (lo <= truth_rr) & (truth_rr <= hi)
    rejects = (lo > 1.0) | (hi < 1.0)  # CI excludes RR=1
    return EstimatorMetrics(
        estimator=name,
        bias_log=round(float(err.mean()), 5),
        rmse_log=round(float(np.sqrt((err**2).mean())), 5),
        coverage=round(float(covered.mean()), 4),
        reject_rate=round(float(rejects.mean()), 4),
        mean_ci_width=round(float((np.log(hi) - np.log(lo)).mean()), 4),
        n_ok=int(e.size),
    )


def recovery_study(
    base: DGP,
    true_rrs: tuple[float, ...] = (1.0, 1.25, 1.6, 2.0),
    *,
    n: int = 3000,
    reps: int = 300,
    seed: int = 20240617,
) -> list[ScenarioResult]:
    results: list[ScenarioResult] = []
    for s_idx, rr in enumerate(true_rrs):
        dgp = dataclasses.replace(base, rr_cond=rr)
        truth_rr = dgp.true_marginal_rr()
        truth_log = math.log(truth_rr)

        acc: dict[str, dict[str, list[float]]] = {
            name: {"log": [], "truth": [], "lo": [], "hi": []}
            for name in ("crude", "iptw", "aipw")
        }
        sign_agree: list[bool] = []
        for rep in range(reps):
            df = dgp.sample(n, seed=seed + 1000 * s_idx + rep)
            ests = estimate_all(df, dgp.names(), seed=seed)
            for name, est in ests.items():
                if est.status == "ok" and est.ci95_rr is not None and est.log_rr is not None:
                    acc[name]["log"].append(est.log_rr)
                    acc[name]["truth"].append(truth_log)
                    acc[name]["lo"].append(est.ci95_rr[0])
                    acc[name]["hi"].append(est.ci95_rr[1])
            i, ap = ests["iptw"], ests["aipw"]
            if i.status == "ok" and ap.status == "ok":
                sign_agree.append(((i.risk_ratio - 1) * (ap.risk_ratio - 1)) >= 0)  # type: ignore[operator]

        metrics = {
            name: _aggregate(d["log"], d["truth"], d["lo"], d["hi"], truth_rr, name)
            for name, d in acc.items()
        }
        results.append(
            ScenarioResult(
                true_rr=truth_rr,
                true_log_rr=truth_log,
                metrics=metrics,
                sign_concordance_iptw_aipw=float(np.mean(sign_agree)) if sign_agree else 0.0,
            )
        )
    return results


# --- calibration study -----------------------------------------------------
@dataclass
class CalibrationResult:
    n_control_estimates: int
    coverage_raw: float        # fraction of raw 95% CIs covering the true null RR=1
    coverage_calibrated: float  # after leave-one-out empirical-null calibration
    mean_systematic_bias_mu: float

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def calibration_study(
    *,
    n: int = 4000,
    n_controls: int = 50,
    datasets: int = 10,
    gamma_u: float = 0.5,
    seed: int = 7,
) -> CalibrationResult:
    """Negative controls have true RR=1 but share an UNMEASURED confounder U.

    IPTW (adjusting only for measured X) leaves residual confounding, so raw CIs
    under-cover RR=1. Empirical-null calibration should restore coverage.
    """
    base = DGP(gamma_a_u=gamma_u, gamma_y_u=gamma_u)
    names = base.names()
    raw_cover: list[bool] = []
    cal_cover: list[bool] = []
    mus: list[float] = []

    for d in range(datasets):
        df = base.sample(n, seed=seed + d, n_neg_controls=n_controls)
        fit = _fit_once(df, names, seed=seed)
        keep = fit.keep_mask
        a = df["treat"].to_numpy()[keep]

        logs: list[float] = []
        ses: list[float] = []
        cis: list[tuple[float, float]] = []
        for j in range(n_controls):
            y = df[f"nc_{j}"].to_numpy()[keep]
            est = estimate_outcome(y, a, fit.weights)
            if est.status == "ok" and est.log_rr is not None and est.ci95_rr is not None:
                logs.append(est.log_rr)
                ses.append(est.se_log_rr)  # type: ignore[arg-type]
                cis.append(est.ci95_rr)

        arr_log, arr_se = np.array(logs), np.array(ses)
        for j in range(len(logs)):
            raw_cover.append(cis[j][0] <= 1.0 <= cis[j][1])
            # Leave-one-out: fit the null on the OTHER controls, calibrate this one.
            mask = np.arange(len(logs)) != j
            null = fit_empirical_null(arr_log[mask], arr_se[mask], min_controls=10)
            if null.fitted:
                mus.append(null.mu)
                cal = calibrate(LogRiskRatio(logs[j]), ses[j], null)
                if cal.calibrated_ci95 is not None:
                    cal_cover.append(cal.calibrated_ci95[0] <= 1.0 <= cal.calibrated_ci95[1])

    return CalibrationResult(
        n_control_estimates=len(raw_cover),
        coverage_raw=round(float(np.mean(raw_cover)), 4) if raw_cover else 0.0,
        coverage_calibrated=round(float(np.mean(cal_cover)), 4) if cal_cover else 0.0,
        mean_systematic_bias_mu=round(float(np.mean(mus)), 4) if mus else 0.0,
    )


# --- verdicts --------------------------------------------------------------
@dataclass
class Verdict:
    checks: list[dict[str, Any]] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str) -> None:
        self.checks.append({"check": name, "pass": bool(passed), "detail": detail})

    @property
    def passed(self) -> bool:
        return all(c["pass"] for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {"overall_pass": self.passed, "checks": self.checks}


def judge(
    recovery: list[ScenarioResult],
    calibration: CalibrationResult,
    *,
    max_adj_bias: float = 0.07,
    coverage_band: tuple[float, float] = (0.90, 0.98),
    max_type1: float = 0.10,
    min_power_at_max: float = 0.70,
    min_confounding_removed: float = 0.07,
) -> Verdict:
    v = Verdict()

    for sc in recovery:
        for name in ("iptw", "aipw"):
            m = sc.metrics[name]
            v.add(
                f"{name} unbiased @RR={sc.true_rr:.2f}",
                abs(m.bias_log) <= max_adj_bias,
                f"bias(log)={m.bias_log:+.3f} (≤{max_adj_bias})",
            )
            v.add(
                f"{name} coverage @RR={sc.true_rr:.2f}",
                coverage_band[0] <= m.coverage <= coverage_band[1],
                f"coverage={m.coverage:.3f} in [{coverage_band[0]},{coverage_band[1]}]",
            )

    null_sc = min(recovery, key=lambda s: abs(s.true_rr - 1.0))
    for name in ("iptw", "aipw"):
        t1 = null_sc.metrics[name].reject_rate
        v.add(f"{name} Type I error", t1 <= max_type1, f"α̂={t1:.3f} (≤{max_type1})")

    max_sc = max(recovery, key=lambda s: s.true_rr)
    for name in ("iptw", "aipw"):
        pw = max_sc.metrics[name].reject_rate
        v.add(
            f"{name} power @RR={max_sc.true_rr:.2f}",
            pw >= min_power_at_max,
            f"power={pw:.3f} (≥{min_power_at_max})",
        )

    # The crude estimator must be visibly more biased than the adjusted ones —
    # otherwise the pipeline isn't earning its keep.
    confounded = max(recovery, key=lambda s: abs(s.metrics["crude"].bias_log))
    crude_b = abs(confounded.metrics["crude"].bias_log)
    adj_b = abs(confounded.metrics["iptw"].bias_log)
    v.add(
        "confounding actually removed (crude vs IPTW)",
        (crude_b - adj_b) >= min_confounding_removed,
        f"|crude bias|={crude_b:.3f} vs |IPTW bias|={adj_b:.3f} "
        f"(gap≥{min_confounding_removed})",
    )

    v.add(
        "calibration restores coverage under residual confounding",
        calibration.coverage_calibrated >= 0.90
        and calibration.coverage_calibrated > calibration.coverage_raw,
        f"raw={calibration.coverage_raw:.3f} → calibrated="
        f"{calibration.coverage_calibrated:.3f}",
    )

    return v
