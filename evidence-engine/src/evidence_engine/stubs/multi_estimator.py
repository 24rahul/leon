"""STUB — multi-estimator concurrence check (Harm (a): a wrong answer reaching a
patient).

A single estimator is a single set of modelling assumptions. An association that
appears only under its author's favourite method is far weaker than one that
survives IPTW, propensity matching, and a doubly-robust outcome model alike.
Concurrence across estimators with *different* failure modes is real triangulation.

Intended contract (slots in alongside the IPTW path in the pipeline):
  * Run a panel of estimators sharing the sealed protocol and DAG: IPTW (built),
    propensity matching, standardization / g-computation, and a doubly-robust
    (AIPW/TMLE) estimator.
  * Report agreement in sign, overlap of calibrated intervals, and disagreement
    diagnostics.
  * Downgrade the evidence tier when estimators materially disagree; this becomes
    an additional pessimistic gate in `honesty.evidence_object`.

ROADMAP: Phase 2. Not yet implemented.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConcurrenceCheck(Protocol):
    def run(self, cohort: Any, sealed_protocol: Any, token: Any) -> dict[str, Any]:
        """Estimate under multiple methods; return per-method and agreement stats."""
        ...


class NotImplementedConcurrenceCheck:
    _MSG = (
        "Multi-estimator concurrence is a Phase-2 stub (stubs/multi_estimator.py). "
        "The prototype reports a single IPTW estimate. See ROADMAP.md."
    )

    def run(self, cohort: Any, sealed_protocol: Any, token: Any) -> dict[str, Any]:
        raise NotImplementedError(self._MSG)
