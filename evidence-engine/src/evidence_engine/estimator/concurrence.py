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

    keys = sorted(ok)
    # The `ok` filter guarantees status == "ok"; assert the fields are populated so
    # the type checker can narrow away the Optionals.
    rrs, los, his, logs = [], [], [], []
    for k in keys:
        e = ok[k]
        assert e.risk_ratio is not None and e.ci95_rr is not None and e.log_rr is not None
        rrs.append(e.risk_ratio)
        los.append(e.ci95_rr[0])
        his.append(e.ci95_rr[1])
        logs.append(e.log_rr)

    sign_agree = len({_sign(r) for r in rrs}) == 1
    # All N intervals share a common point iff the largest lower bound is below the
    # smallest upper bound.
    ci_overlap = max(los) <= min(his)
    gap = max(logs) - min(logs)
    concordant = bool(sign_agree and ci_overlap)

    return Concurrence(
        estimators=estimators,
        sign_agree=bool(sign_agree),
        ci_overlap=bool(ci_overlap),
        abs_log_rr_gap=round(float(gap), 5),
        concordant=concordant,
        note=(
            f"panel [{', '.join(keys)}]: "
            + ("concordant" if concordant else "DISCORDANT")
            + f" (sign_agree={'yes' if sign_agree else 'no'}, "
            + f"ci_overlap={'yes' if ci_overlap else 'no'}, "
            + f"max_log_rr_gap={gap:.3f})."
        ),
    )

