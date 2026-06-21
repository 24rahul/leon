"""E-values (VanderWeele & Ding, *Ann. Intern. Med.* 2017).

The E-value is the minimum strength of association — on the risk-ratio scale —
that an unmeasured confounder would need to have with *both* the exposure and the
outcome, above and beyond the measured confounders, to fully explain away an
observed association. It is a sensitivity statement about ONE threat
(unmeasured confounding); see DESIGN_CRITIQUE §1.4 for why it is necessary but
never reported alone.

Closed forms implemented:
  * RR ≥ 1:  E = RR + sqrt(RR · (RR − 1))
  * RR < 1:  apply the formula to 1/RR (symmetry).
  * The E-value for the confidence interval uses the CI limit *closest to the
    null*. If the interval contains the null (1), the CI E-value is 1.0 — i.e. no
    unmeasured confounding is required for the data to be compatible with no
    association. This CI E-value is the one that actually constrains an
    interpretation; the point-estimate E-value alone can flatter a fragile result.

Approximate conversions to the RR scale (also from VanderWeele & Ding):
  * Odds ratio, rare outcome:   RR ≈ OR
  * Odds ratio, common outcome: RR ≈ sqrt(OR)   (square-root transformation)
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .units import RiskRatio


@dataclass(frozen=True)
class EValue:
    point: float
    ci_limit: float | None  # E-value at the CI bound nearest the null (None if no CI)
    rr_used: float          # the risk ratio the point E-value was computed from
    note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _evalue_rr_scalar(rr: float) -> float:
    """E-value for a single risk-ratio point (handles RR<1 by symmetry)."""
    if rr <= 0:
        raise ValueError("Risk ratio must be positive.")
    if rr < 1.0:
        rr = 1.0 / rr
    if math.isclose(rr, 1.0):
        return 1.0
    return rr + math.sqrt(rr * (rr - 1.0))


def evalue_for_rr(
    rr: RiskRatio,
    ci_low: RiskRatio | None = None,
    ci_high: RiskRatio | None = None,
) -> EValue:
    """E-value for a risk ratio and (optionally) its confidence interval."""
    point = _evalue_rr_scalar(rr)

    ci_limit: float | None = None
    if ci_low is not None and ci_high is not None:
        if ci_low <= 1.0 <= ci_high:
            # The null is inside the interval: nothing needs explaining away.
            ci_limit = 1.0
        else:
            # Use the bound nearer the null.
            limit = ci_low if rr > 1.0 else ci_high
            ci_limit = _evalue_rr_scalar(limit)

    return EValue(
        point=round(point, 4),
        ci_limit=round(ci_limit, 4) if ci_limit is not None else None,
        rr_used=round(rr, 4),
        note=(
            "Minimum unmeasured exposure–outcome confounding (RR scale) needed to "
            "explain the estimate; the CI-limit E-value bounds the interval."
        ),
    )


def rr_from_or(odds_ratio: float, *, rare_outcome: bool) -> float:
    """Approximate the risk ratio from an odds ratio for E-value purposes."""
    if odds_ratio <= 0:
        raise ValueError("Odds ratio must be positive.")
    return odds_ratio if rare_outcome else math.sqrt(odds_ratio)
