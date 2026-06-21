"""PARTIALLY IMPLEMENTED — multi-estimator concurrence (Harm (a): a wrong answer
reaching a patient).

A single estimator is a single set of modelling assumptions. An association that
appears only under its author's favourite method is far weaker than one that
survives IPTW, propensity matching, and a doubly-robust outcome model alike.

WHAT IS BUILT: IPTW (`estimator/iptw.py`) and a doubly-robust AIPW estimator
(`estimator/aipw.py`) are compared in `estimator/concurrence.py`, and their
agreement (sign + interval overlap) is a live pessimistic gate in
`honesty.evidence_object`. That is genuine two-estimator triangulation.

WHAT REMAINS (this stub): a *broader* panel sharing the sealed protocol and DAG —
propensity matching, standardization / g-computation, and TMLE — plus concurrence
on the *calibrated* intervals. The interface below is the shape the broader panel
will satisfy.

ROADMAP: Phase 2. Two-estimator concurrence is live; the full panel is not.
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
