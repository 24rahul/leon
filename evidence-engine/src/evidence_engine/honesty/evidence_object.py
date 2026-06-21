"""The evidence object — the single structured result the engine emits.

It carries the estimate, the empirical-null calibration, the E-value, the
falsification probes, the Phase-0 audit caveats, the equity breakdown, the
explicit identifying assumptions (each with what would invalidate it), and an
evidence tier — then serializes ONLY through the controlled-vocabulary guard.

The tier is decided by a set of *pessimistic gates*. Each gate names the strongest
stance it is willing to support; the final stance is the WEAKEST across all gates
(`claims.weakest`). The default floor is INSUFFICIENT_EVIDENCE. A finding climbs
only by clearing every gate — exactly the "default to skepticism" invariant. The
per-gate rationale is recorded so the tier is auditable, not oracular.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .claims import Claim, Stance, weakest
from .vocabulary_guard import guard_object
from ..estimator.calibration import CalibratedEstimate
from ..estimator.evalue import EValue
from ..estimator.iptw import OutcomeEstimate, PropensityFit, SMD_BALANCE_THRESHOLD

# Robustness thresholds for the E-value of the CI limit (RR scale).
EVALUE_TRIAL_WORTHY = 1.5
EVALUE_HYPOTHESIS = 1.25


# --- the standing identifying assumptions of any target-trial emulation ----
def _standard_assumptions() -> list[dict[str, str]]:
    return [
        {
            "assumption": "Exchangeability (no unmeasured confounding given the "
            "specified covariates).",
            "what_would_invalidate": "Any unmeasured common antecedent of both "
            "exposure and outcome. Partially bounded by the E-value; not bounded "
            "against selection or measurement bias.",
        },
        {
            "assumption": "Positivity (every covariate stratum could receive either "
            "treatment).",
            "what_would_invalidate": "Deterministic treatment in some stratum; "
            "monitored via propensity trimming and the Kish design sample size.",
        },
        {
            "assumption": "Consistency / well-defined intervention.",
            "what_would_invalidate": "An ambiguous or heterogeneous exposure "
            "definition that maps to multiple real interventions.",
        },
        {
            "assumption": "Unbiased measurement of exposure, outcome, covariates.",
            "what_would_invalidate": "Differential measurement by group — e.g. the "
            "pulse-oximetry bias surfaced in the Phase-0 audit.",
        },
        {
            "assumption": "No selection bias at or after time zero.",
            "what_would_invalidate": "Differential eligibility or loss to follow-up "
            "across arms after t0.",
        },
        {
            "assumption": "Correct model specification (propensity / outcome).",
            "what_would_invalidate": "Misspecified functional form; partially "
            "checked by covariate balance (SMD) and the refutation probes.",
        },
    ]


@dataclass
class EvidenceObject:
    claim: Claim
    estimate: OutcomeEstimate
    propensity_diagnostics: dict[str, Any]
    calibration: CalibratedEstimate
    evalue: EValue
    refutations: list[dict[str, Any]]
    audit_caveats: list[str]
    equity: dict[str, Any]
    assumptions: list[dict[str, str]]
    evidence_tier: str
    tier_rationale: list[str]
    provenance: dict[str, Any]
    artifact_root: str
    is_synthetic: bool
    negative_controls: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "evidence_tier": self.evidence_tier,
            "tier_rationale": self.tier_rationale,
            "estimate": self.estimate.to_dict(),
            "propensity_diagnostics": self.propensity_diagnostics,
            "empirical_calibration": self.calibration.to_dict(),
            "e_value": self.evalue.to_dict(),
            "refutations": self.refutations,
            "negative_controls": self.negative_controls,
            "equity": self.equity,
            "audit_caveats": self.audit_caveats,
            "assumptions": self.assumptions,
            "provenance": self.provenance,
            "artifact_root": self.artifact_root,
            "data_is_synthetic": self.is_synthetic,
        }

    def serialize(self) -> dict[str, Any]:
        """Return the dict ONLY after the controlled-vocabulary guard passes."""
        return guard_object(self.to_dict())


# --------------------------------------------------------------------------- #
# Tier decision (pessimistic gates)                                          #
# --------------------------------------------------------------------------- #
def _decide_tier(
    estimate: OutcomeEstimate,
    propensity: PropensityFit,
    calibration: CalibratedEstimate,
    evalue: EValue,
    placebo_alarmed: bool,
    equity: dict[str, Any],
) -> tuple[Stance, list[str]]:
    rationale: list[str] = []

    if estimate.status != "ok":
        return Stance.INSUFFICIENT_EVIDENCE, [f"estimate: {estimate.reason}"]

    gates: list[Stance] = []

    # Gate 1 — calibrated signal.
    cal = calibration
    if not cal.empirical_null.fitted:
        gates.append(Stance.INSUFFICIENT_EVIDENCE)
        rationale.append("calibration: empirical null underpowered → insufficient.")
    elif cal.calibrated_ci95 and not (cal.calibrated_ci95[0] <= 1.0 <= cal.calibrated_ci95[1]):
        gates.append(Stance.REQUIRES_CONFIRMATORY_TRIAL)
        rationale.append("calibrated CI excludes the null after empirical calibration.")
    else:
        gates.append(Stance.INSUFFICIENT_EVIDENCE)
        rationale.append("calibrated CI contains the null → insufficient signal.")

    # Gate 2 — covariate balance.
    if propensity.max_abs_smd_after <= SMD_BALANCE_THRESHOLD:
        gates.append(Stance.REQUIRES_CONFIRMATORY_TRIAL)
        rationale.append(
            f"balance achieved (max |SMD|={propensity.max_abs_smd_after:.3f} ≤ "
            f"{SMD_BALANCE_THRESHOLD})."
        )
    else:
        gates.append(Stance.CONSISTENT_WITH)
        rationale.append(
            f"residual imbalance (max |SMD|={propensity.max_abs_smd_after:.3f}) caps "
            "the stance at 'consistent with'."
        )

    # Gate 3 — robustness to unmeasured confounding (CI-limit E-value).
    ev = evalue.ci_limit if evalue.ci_limit is not None else 1.0
    if ev >= EVALUE_TRIAL_WORTHY:
        gates.append(Stance.REQUIRES_CONFIRMATORY_TRIAL)
        rationale.append(f"CI E-value={ev:.2f} ≥ {EVALUE_TRIAL_WORTHY} (robust).")
    elif ev >= EVALUE_HYPOTHESIS:
        gates.append(Stance.HYPOTHESIS_GENERATING)
        rationale.append(f"CI E-value={ev:.2f} in [{EVALUE_HYPOTHESIS},{EVALUE_TRIAL_WORTHY}).")
    else:
        gates.append(Stance.CONSISTENT_WITH)
        rationale.append(f"CI E-value={ev:.2f} < {EVALUE_HYPOTHESIS} (fragile to confounding).")

    # Gate 4 — falsification (placebo).
    if placebo_alarmed:
        gates.append(Stance.INSUFFICIENT_EVIDENCE)
        rationale.append("placebo refuter produced a non-trivial effect → downgrade.")
    else:
        gates.append(Stance.REQUIRES_CONFIRMATORY_TRIAL)
        rationale.append("placebo refuter near null (no falsification).")

    # Gate 5 — equity transfer.
    silent = equity.get("silent_in", [])
    present = equity.get("evidence_present_in", [])
    absent = equity.get("evidence_absent_in", [])
    if present and not silent:
        gates.append(Stance.REQUIRES_CONFIRMATORY_TRIAL)
        rationale.append("evidence consistent across all estimable groups.")
    elif present and silent:
        gates.append(Stance.HYPOTHESIS_GENERATING)
        rationale.append(f"signal present in {present} but silent in {silent}.")
    else:
        gates.append(Stance.CONSISTENT_WITH)
        rationale.append("no group carries a clear within-group signal.")
    if absent:
        rationale.append(f"NOTE: evidence absent (not null) for {absent}.")

    return weakest(*gates), rationale


def build_evidence_object(
    *,
    exposure: str,
    outcome: str,
    scope: str,
    estimate: OutcomeEstimate,
    propensity: PropensityFit,
    calibration: CalibratedEstimate,
    evalue: EValue,
    refutations: list[dict[str, Any]],
    placebo_alarmed: bool,
    audit_caveats: list[str],
    equity: dict[str, Any],
    provenance: dict[str, Any],
    artifact_root: str,
    is_synthetic: bool,
    negative_controls: dict[str, Any],
) -> EvidenceObject:
    stance, rationale = _decide_tier(
        estimate, propensity, calibration, evalue, placebo_alarmed, equity
    )
    claim = Claim(stance=stance, exposure=exposure, outcome=outcome, scope=scope)
    return EvidenceObject(
        claim=claim,
        estimate=estimate,
        propensity_diagnostics=propensity.diagnostics_dict(),
        calibration=calibration,
        evalue=evalue,
        refutations=refutations,
        audit_caveats=audit_caveats,
        equity=equity,
        assumptions=_standard_assumptions(),
        evidence_tier=stance.name,
        tier_rationale=rationale,
        provenance=provenance,
        artifact_root=artifact_root,
        is_synthetic=is_synthetic,
        negative_controls=negative_controls,
    )
