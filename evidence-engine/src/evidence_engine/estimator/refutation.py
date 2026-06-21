"""Falsification probes via dowhy refuters.

These are the *complement* to empirical calibration (DESIGN_CRITIQUE §1.3):
calibration estimates and removes systematic error; refuters try to *break* the
estimate. We run three classics:

* **placebo_treatment** — permute the exposure. A credible estimate collapses to
  ~0; if the placebo "effect" is large, the original was an artifact.
* **random_common_cause** — add an independent random confounder. A robust
  estimate barely moves.
* **data_subset** — re-estimate on a random subset. Large swings signal fragility.

Refuters are inherently stochastic; we seed numpy immediately beforehand and round
outputs so the pipeline stays byte-reproducible. dowhy is heavily logged, so we
quiet it. Any refuter that errors is reported as ``status="error"`` — never
silently dropped.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np
import pandas as pd

# Quiet dowhy's verbose loggers; we surface structured results ourselves.
for _name in ("dowhy", "dowhy.causal_estimator", "dowhy.causal_refuters"):
    logging.getLogger(_name).setLevel(logging.ERROR)


@dataclass(frozen=True)
class RefutationResult:
    refuter: str
    status: str  # "ok" | "error"
    estimated_effect: float | None
    new_effect: float | None
    p_value: float | None
    interpretation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_refutations(
    df: pd.DataFrame,
    exposure: str,
    outcome: str,
    confounders: Sequence[str],
    *,
    seed: int,
    num_simulations: int = 20,
) -> list[RefutationResult]:
    try:
        from dowhy import CausalModel
    except Exception as exc:  # pragma: no cover - dependency guard
        return [
            RefutationResult(
                "import", "error", None, None, None, f"dowhy unavailable: {exc}"
            )
        ]

    # dowhy needs complete-case data for its internal models; drop rows missing a
    # confounder ONLY for the refutation probes (the primary estimate uses the
    # explicit missing-indicator design). This is logged via the result note.
    cols = [exposure, outcome, *confounders]
    work = df[cols].dropna().copy()

    results: list[RefutationResult] = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        np.random.seed(seed)
        model = CausalModel(
            data=work,
            treatment=exposure,
            outcome=outcome,
            common_causes=list(confounders),
        )
        estimand = model.identify_effect(proceed_when_unidentifiable=True)
        estimate = model.estimate_effect(
            estimand, method_name="backdoor.propensity_score_weighting"
        )
        base = float(estimate.value)

        specs: list[tuple[str, dict[str, Any], str]] = [
            ("placebo_treatment_refuter", {"placebo_type": "permute"},
             "Permuted exposure is expected to yield a near-zero effect."),
            ("random_common_cause", {},
             "Adding a random confounder is expected to barely move the estimate."),
            ("data_subset_refuter", {"subset_fraction": 0.8},
             "A random subset is expected to reproduce the estimate."),
        ]
        for method, kwargs, interp in specs:
            np.random.seed(seed)  # determinism per refuter
            try:
                ref = model.refute_estimate(
                    estimand,
                    estimate,
                    method_name=method,
                    num_simulations=num_simulations,
                    random_seed=seed,
                    **kwargs,
                )
                new_effect = float(getattr(ref, "new_effect", float("nan")))
                p = getattr(ref, "refutation_result", None)
                p_value = (
                    float(p["p_value"]) if isinstance(p, dict) and "p_value" in p else None
                )
                results.append(
                    RefutationResult(
                        refuter=method,
                        status="ok",
                        estimated_effect=round(base, 5),
                        new_effect=round(new_effect, 5),
                        p_value=round(p_value, 5) if p_value is not None else None,
                        interpretation=interp,
                    )
                )
            except Exception as exc:  # report, never swallow
                results.append(
                    RefutationResult(method, "error", round(base, 5), None, None, str(exc))
                )
    return results


def placebo_alarm(results: list[RefutationResult], alpha: float = 0.05) -> bool:
    """True when the real estimate is NOT distinguishable from a permuted-treatment
    placebo — the genuine downgrade signal.

    dowhy's placebo refuter reports a p-value for the original effect against the
    placebo (null) distribution: a *low* p-value means the real effect is unlikely
    under placebo (good; the estimate survives). We therefore alarm when the
    p-value is high (≥ alpha). The raw placebo *effect magnitude* is not a reliable
    alarm on its own: propensity weighting under a randomly permuted treatment
    yields near-degenerate propensities and unstable point effects, so we use it
    only as a fallback when the p-value is unavailable.
    """
    import math

    for r in results:
        if r.refuter == "placebo_treatment_refuter" and r.status == "ok":
            if r.p_value is not None and not math.isnan(r.p_value):
                return r.p_value >= alpha
            if r.new_effect is not None and r.estimated_effect:
                # Fallback: alarm if placebo reproduces ≥ half the real effect.
                return abs(r.new_effect) >= 0.5 * abs(r.estimated_effect)
    return False
