"""Glue: build the protocol DAG and obtain its approval certificate from config.

In a production system the signatures would arrive out-of-band from a signing
service. Here the `dag:` config block records the reviewers who attested to the
DAG, and this module replays those attestations through the real gate so the
structural checks and quorum rules are genuinely enforced (config cannot bypass
them — a missing role or a mediator in the adjustment set still raises).
"""

from __future__ import annotations

from typing import Any

from .causal_dag import CausalDAG, dag_from_protocol
from .dag_gate import DagApprovalCertificate, DagApprovalGate, Reviewer
from .schema import SealedProtocol


def build_and_approve_dag(
    sealed: SealedProtocol, dag_cfg: dict[str, Any]
) -> tuple[CausalDAG, DagApprovalCertificate]:
    proto = sealed.protocol
    confounders = sealed.confounder_names()
    extra = [tuple(e) for e in dag_cfg.get("extra_edges", [])]
    dag = dag_from_protocol(proto.exposure, proto.outcome, confounders, extra_edges=extra)  # type: ignore[arg-type]

    gate = DagApprovalGate(
        exposure=proto.exposure,
        outcome=proto.outcome,
        confounders=confounders,
        protocol_hash=sealed.protocol_hash,
    )
    for r in dag_cfg.get("reviewers", []):
        gate.sign(dag, Reviewer(name=r["name"], role=r["role"], affiliation=r.get("affiliation", "")))

    # issue() raises DagApprovalError if structure is invalid or quorum is unmet.
    cert = gate.issue(dag)
    return dag, cert
