"""STUB — human DAG-approval gate (Harm (c): don't concentrate the power to
declare causal structure).

The causal DAG encodes which variables are confounders, mediators, or colliders —
and that choice *determines the answer*. Letting the analyst silently pick the DAG
is exactly the concentration of epistemic power the three-harm model warns about.
This gate makes the DAG an explicit, signed, human-approved artifact that the
estimator refuses to run without.

Intended contract (already shaped to drop in ahead of `cohort.build_cohort`):
  * Accept a proposed DAG (e.g. a `networkx.DiGraph` over the protocol's
    variables) plus the sealed protocol.
  * Require sign-off from ≥2 named domain reviewers (clinician + someone from an
    affected population, per the README's "after it runs" note).
  * Persist an immutable, hash-chained approval record into the provenance ledger.
  * Verify the DAG is acyclic, that every protocol confounder is a backdoor node,
    and that no adjustment set conditions on a collider or mediator.

ROADMAP: Phase 2. Not yet implemented.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DagApprovalGate(Protocol):
    def submit(self, dag: Any, sealed_protocol: Any) -> str:
        """Submit a DAG for review; return an approval-request id."""
        ...

    def is_approved(self, request_id: str) -> bool:
        """True only once the required human reviewers have signed off."""
        ...

    def approval_record(self, request_id: str) -> dict[str, Any]:
        """The immutable, hash-chained record of who approved what, when."""
        ...


class NotImplementedDagGate:
    """Placeholder. Every method fails loud — the core must not silently proceed."""

    _MSG = (
        "DAG-approval gate is a Phase-2 stub (stubs/dag_gate.py). The prototype "
        "uses the config-declared confounders directly; a production system must "
        "require human sign-off on the causal structure. See ROADMAP.md."
    )

    def submit(self, dag: Any, sealed_protocol: Any) -> str:
        raise NotImplementedError(self._MSG)

    def is_approved(self, request_id: str) -> bool:
        raise NotImplementedError(self._MSG)

    def approval_record(self, request_id: str) -> dict[str, Any]:
        raise NotImplementedError(self._MSG)
