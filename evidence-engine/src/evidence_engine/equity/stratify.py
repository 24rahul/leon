"""Equity-stratified estimation (mandatory; never optional).

A population-average effect must NEVER be assumed to transfer to an
under-represented group. So for every finding we re-estimate within each level of
the protected stratifier and classify the evidence per group into exactly one of:

    PRESENT  — estimable and the 95% interval excludes the null
    SILENT   — estimable but the interval contains the null (no signal here)
    ABSENT   — not estimable (too few subjects/events): evidence is *missing*,
               which is reported as missing, not as a null

The summary states explicitly which groups carry evidence, which are silent, and
crucially which have NO evidence at all — the populations on whom the finding
says nothing. This is the operationalization of Harm (b) in the three-harm model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Sequence

from ..cohort.builder import Cohort
from ..protocol.schema import OutcomeAccessToken
from ..estimator.iptw import fit_propensity, estimate_outcome


@dataclass(frozen=True)
class GroupEvidence:
    group: str
    n: int
    classification: str  # PRESENT | SILENT | ABSENT
    risk_ratio: float | None
    ci95_rr: tuple[float, float] | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class EquityReport:
    stratifier: str
    groups: list[GroupEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        present = [g.group for g in self.groups if g.classification == "PRESENT"]
        silent = [g.group for g in self.groups if g.classification == "SILENT"]
        absent = [g.group for g in self.groups if g.classification == "ABSENT"]
        return {
            "stratifier": self.stratifier,
            "evidence_present_in": present,
            "silent_in": silent,
            "evidence_absent_in": absent,
            "holds_across_all_estimable_groups": bool(present) and not silent,
            "per_group": [g.to_dict() for g in self.groups],
        }


def stratified_estimates(
    cohort: Cohort,
    outcome: str,
    token: OutcomeAccessToken,
    confounders: Sequence[str],
    *,
    stratifier: str,
    no_impute: Sequence[str],
    trim: tuple[float, float],
    seed: int,
    min_stratum_n: int,
) -> EquityReport:
    df = cohort.frame
    exposure = cohort.sealed.protocol.exposure
    # Do not condition on the stratifier within its own strata.
    sub_confounders = [c for c in confounders if c != stratifier]

    report = EquityReport(stratifier=stratifier)
    for group, g in df.groupby(stratifier, dropna=False):
        n = len(g)
        if n < min_stratum_n:
            report.groups.append(
                GroupEvidence(str(group), n, "ABSENT", None, None,
                              f"n={n} < min_stratum_n={min_stratum_n}")
            )
            continue
        try:
            fit = fit_propensity(
                g, exposure, sub_confounders,
                no_impute=no_impute, trim=trim, seed=seed,
            )
            keep = fit.keep_mask
            y = g.loc[keep, outcome].to_numpy(dtype=float)
            a = g.loc[keep, exposure].to_numpy(dtype=int)
            est = estimate_outcome(y, a, fit.weights)
        except Exception as exc:  # estimation can fail in a thin stratum: report it
            report.groups.append(
                GroupEvidence(str(group), n, "ABSENT", None, None, f"estimation failed: {exc}")
            )
            continue

        if est.status != "ok" or est.ci95_rr is None:
            report.groups.append(
                GroupEvidence(str(group), n, "ABSENT", None, None, est.reason)
            )
            continue
        lo, hi = est.ci95_rr
        classification = "SILENT" if lo <= 1.0 <= hi else "PRESENT"
        report.groups.append(
            GroupEvidence(str(group), n, classification, est.risk_ratio, est.ci95_rr, "")
        )
    return report
