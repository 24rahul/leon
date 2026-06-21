"""Render the validation study to a markdown report and diagnostic plots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .simulation import CalibrationResult, ScenarioResult, Verdict  # noqa: E402


def render_markdown(
    recovery: list[ScenarioResult],
    calibration: CalibrationResult,
    verdict: Verdict,
    *,
    n: int,
    reps: int,
) -> str:
    badge = "✅ PASS" if verdict.passed else "❌ FAIL"
    lines: list[str] = []
    lines.append("# Pipeline validation report\n")
    lines.append(
        f"**Overall verdict: {badge}** — Monte Carlo study, n={n} patients/replication, "
        f"{reps} replications/scenario. Estimators driven are the engine's own "
        "`fit_propensity` + `estimate_outcome` (IPTW), `estimate_aipw` (AIPW), and the "
        "empirical-null calibration — compared against a crude unadjusted estimator and "
        "the data-generating process's known marginal causal effect.\n"
    )

    lines.append("## 1. Recovery of known truth, by scenario\n")
    lines.append(
        "For each true risk ratio we report bias (log scale; 0 = unbiased), 95% CI "
        "coverage (should be ≈0.95), and the rejection rate (= **Type I error** when "
        "true RR=1, = **power** otherwise).\n"
    )
    for sc in recovery:
        lines.append(f"### True RR = {sc.true_rr:.3f}  (log = {sc.true_log_rr:+.3f})\n")
        lines.append("| estimator | bias(log) | RMSE | coverage | reject rate | mean CI width | n |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for name in ("crude", "iptw", "aipw"):
            m = sc.metrics[name]
            lines.append(
                f"| {name} | {m.bias_log:+.3f} | {m.rmse_log:.3f} | {m.coverage:.3f} | "
                f"{m.reject_rate:.3f} | {m.mean_ci_width:.3f} | {m.n_ok} |"
            )
        lines.append(
            f"\nIPTW/AIPW sign concordance: **{sc.sign_concordance_iptw_aipw:.3f}**.\n"
        )

    lines.append("## 2. Empirical-null calibration under residual confounding\n")
    lines.append(
        "Negative-control outcomes have a TRUE null effect (RR=1) but share an "
        "*unmeasured* confounder the estimator never sees. Raw intervals therefore "
        "under-cover the null; calibration should restore it.\n"
    )
    lines.append("| metric | value |")
    lines.append("|---|---:|")
    lines.append(f"| negative-control estimates | {calibration.n_control_estimates} |")
    lines.append(f"| raw 95% CI coverage of RR=1 | {calibration.coverage_raw:.3f} |")
    lines.append(f"| **calibrated** 95% CI coverage of RR=1 | **{calibration.coverage_calibrated:.3f}** |")
    lines.append(f"| estimated systematic bias μ (log) | {calibration.mean_systematic_bias_mu:+.3f} |")
    lines.append("")

    lines.append("## 3. Pass/fail checks\n")
    lines.append("| check | result | detail |")
    lines.append("|---|:--:|---|")
    for c in verdict.checks:
        mark = "✅" if c["pass"] else "❌"
        lines.append(f"| {c['check']} | {mark} | {c['detail']} |")
    lines.append("")

    lines.append("## How to read this\n")
    lines.append(
        "- The **crude** rows are the control group: a naive analyst. Their large bias "
        "and 0% coverage are the confounding the pipeline must remove.\n"
        "- IPTW and AIPW bias near 0 with ≈95% coverage means the engine recovers the "
        "true causal effect and its uncertainty is honest.\n"
        "- Type I error ≈0.05 at the null means it does not manufacture findings; high "
        "power at real effects means it can still find them.\n"
        "- Calibration lifting negative-control coverage back toward 0.95 shows the "
        "empirical-null machinery corrects residual (unmeasured) confounding."
    )
    return "\n".join(lines) + "\n"


def plot_operating_characteristics(
    recovery: list[ScenarioResult], calibration: CalibrationResult, out_path: Path
) -> None:
    rrs = [sc.true_rr for sc in recovery]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    colors = {"crude": "#c0392b", "iptw": "#2b6cb0", "aipw": "#27795b"}

    # (a) bias
    ax = axes[0, 0]
    for name, c in colors.items():
        ax.plot(rrs, [sc.metrics[name].bias_log for sc in recovery], "o-", color=c, label=name)
    ax.axhline(0, color="k", lw=0.8, ls="--")
    ax.set_title("(a) Bias of log risk ratio\n(0 = unbiased)")
    ax.set_xlabel("true risk ratio")
    ax.set_ylabel("mean estimated − true (log)")
    ax.legend()

    # (b) coverage
    ax = axes[0, 1]
    for name, c in colors.items():
        ax.plot(rrs, [sc.metrics[name].coverage for sc in recovery], "o-", color=c, label=name)
    ax.axhline(0.95, color="k", lw=0.8, ls="--")
    ax.set_ylim(0, 1.02)
    ax.set_title("(b) 95% CI coverage\n(nominal = 0.95)")
    ax.set_xlabel("true risk ratio")
    ax.set_ylabel("coverage")
    ax.legend()

    # (c) rejection rate (Type I error / power)
    ax = axes[1, 0]
    for name, c in colors.items():
        ax.plot(rrs, [sc.metrics[name].reject_rate for sc in recovery], "o-", color=c, label=name)
    ax.axhline(0.05, color="k", lw=0.8, ls="--")
    ax.set_ylim(0, 1.02)
    ax.set_title("(c) Rejection rate\n(α at RR=1; power otherwise)")
    ax.set_xlabel("true risk ratio")
    ax.set_ylabel("P(CI excludes null)")
    ax.legend()

    # (d) calibration coverage bar
    ax = axes[1, 1]
    ax.bar(["raw", "calibrated"], [calibration.coverage_raw, calibration.coverage_calibrated],
           color=["#c0392b", "#27795b"])
    ax.axhline(0.95, color="k", lw=0.8, ls="--")
    ax.set_ylim(0, 1.02)
    ax.set_title("(d) Negative-control coverage of RR=1\nunder unmeasured confounding")
    ax.set_ylabel("coverage")

    fig.suptitle("Evidence Engine — pipeline operating characteristics", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
