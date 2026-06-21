"""Cross-estimator concurrence (a partial, honest realization of the
multi-estimator stub).

Two estimators with *different* failure modes — IPTW (propensity-only) and AIPW
(doubly robust) — are compared. An association is far more credible when both
agree than when only one does. We check:

  * sign agreement: do both put the risk ratio on the same side of 1?
  * interval overlap: do the 95% CIs intersect?
  * relative magnitude gap: |log RR_a − log RR_b| / max(|log RR|, ε)

The result feeds a pessimistic gate in `honesty.evidence_object`: material
disagreement downgrades the tier. This implements IPTW-vs-AIPW concurrence;
propensity matching and TMLE remain on the roadmap (`stubs/multi_estimator.py`).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .iptw import OutcomeEstimate


@dataclass(frozen=True)
class Concurrence:
    estimators: dict[str, dict[str, Any]]
    sign_agree: bool | None
    ci_overlap: bool | None
    abs_log_rr_gap: float | None
    concordant: bool
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sign(rr: float) -> int:
    if rr > 1.0:
        return 1
    if rr < 1.0:
        return -1
    return 0


def compare(named: dict[str, OutcomeEstimate]) -> Concurrence:
    ok = {k: v for k, v in named.items() if v.status == "ok" and v.ci95_rr is not None}
    estimators = {k: v.to_dict() for k, v in named.items()}

    if len(ok) < 2:
        return Concurrence(
            estimators=estimators,
            sign_agree=None,
            ci_overlap=None,
            abs_log_rr_gap=None,
            concordant=False,
            note="Fewer than two estimable estimators; concurrence cannot be assessed.",
        )

    keys = list(ok)
    a, b = ok[keys[0]], ok[keys[1]]
    # Narrowed by the `ok` filter (status == "ok" guarantees these are populated).
    assert a.risk_ratio is not None and b.risk_ratio is not None
    assert a.ci95_rr is not None and b.ci95_rr is not None
    assert a.log_rr is not None and b.log_rr is not None
    sign_agree = _sign(a.risk_ratio) == _sign(b.risk_ratio)
    lo_a, hi_a = a.ci95_rr
    lo_b, hi_b = b.ci95_rr
    ci_overlap = not (hi_a < lo_b or hi_b < lo_a)
    gap = abs(a.log_rr - b.log_rr)
    concordant = bool(sign_agree and ci_overlap)

    return Concurrence(
        estimators=estimators,
        sign_agree=bool(sign_agree),
        ci_overlap=bool(ci_overlap),
        abs_log_rr_gap=round(float(gap), 5),
        concordant=concordant,
        note=(
            f"{keys[0]} vs {keys[1]}: "
            + ("concordant" if concordant else "DISCORDANT")
            + f" (sign_agree={'yes' if sign_agree else 'no'}, "
            + f"ci_overlap={'yes' if ci_overlap else 'no'})."
        ),
    )
