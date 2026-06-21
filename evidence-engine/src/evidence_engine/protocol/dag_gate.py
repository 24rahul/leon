"""Human DAG-approval gate (Harm c: don't concentrate the power to declare
causal structure).

The estimator must refuse to run on a causal graph that no human has approved.
This is enforced the same way outcome access is — with an unforgeable capability:

    CausalDAG ──validate(protocol)──► structural checks must pass
        │
        │  reviewers sign the DAG hash (≥2, incl. clinician + affected-population)
        ▼
    DagApprovalGate.issue() ──mints──► DagApprovalCertificate
        │
        ▼
    required by the estimation stage of the pipeline

A `DagApprovalCertificate` cannot be constructed directly; only `DagApprovalGate`
holds the sentinel its constructor demands. So possessing one *proves* that the
structural checks passed AND the human quorum signed — there is no code path to a
causal estimate that skips either. This is the structural analogue of the
pre-registration token, applied to the causal graph itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from .causal_dag import CausalDAG, DagValidation

# Module-private capability key — only code in this module can mint a certificate.
_MINT: Final = object()

# Roles the quorum must include. "affected_population" encodes the README's
# requirement that someone from an affected population signs off, not only clinicians.
REQUIRED_ROLES: Final = ("clinician", "affected_population")
MIN_REVIEWERS: Final = 2


class DagApprovalError(PermissionError):
    """Raised when estimation is attempted without a valid approval certificate."""


@dataclass(frozen=True)
class Reviewer:
    name: str
    role: str  # e.g. "clinician", "affected_population", "epidemiologist"
    affiliation: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.role.strip():
            raise ValueError("A reviewer needs a name and a role.")


@dataclass(frozen=True)
class Signature:
    """A reviewer's attestation to a specific DAG hash."""

    reviewer: Reviewer
    signed_dag_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.reviewer.name,
            "role": self.reviewer.role,
            "affiliation": self.reviewer.affiliation,
            "signed_dag_hash": self.signed_dag_hash,
        }


class DagApprovalCertificate:
    """Unforgeable proof that a DAG passed validation and human quorum signed it."""

    dag_hash: str
    protocol_hash: str
    signatures: tuple[Signature, ...]
    validation: DagValidation
    __slots__ = ("dag_hash", "protocol_hash", "signatures", "validation")

    def __init__(
        self,
        dag_hash: str,
        protocol_hash: str,
        signatures: tuple[Signature, ...],
        validation: DagValidation,
        _key: object,
    ) -> None:
        if _key is not _MINT:
            raise DagApprovalError(
                "DagApprovalCertificate cannot be constructed directly. Submit a DAG "
                "and the required signatures to DagApprovalGate.issue() — this is the "
                "human-approval guarantee for the causal structure."
            )
        object.__setattr__(self, "dag_hash", dag_hash)
        object.__setattr__(self, "protocol_hash", protocol_hash)
        object.__setattr__(self, "signatures", signatures)
        object.__setattr__(self, "validation", validation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dag_hash": self.dag_hash,
            "protocol_hash": self.protocol_hash,
            "reviewers": [s.to_dict() for s in self.signatures],
            "validation": self.validation.to_dict(),
        }

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"DagApprovalCertificate(dag={self.dag_hash[:12]}…, n_signers={len(self.signatures)})"


@dataclass
class DagApprovalGate:
    """Validates a DAG, collects signatures, and mints a certificate iff both pass."""

    exposure: str
    outcome: str
    confounders: list[str]
    protocol_hash: str
    _signatures: dict[str, Signature] = field(default_factory=dict)

    def sign(self, dag: CausalDAG, reviewer: Reviewer) -> None:
        """Record a reviewer's signature over the current DAG hash."""
        self._signatures[reviewer.name] = Signature(reviewer, dag.dag_hash())

    def _quorum_reasons(self, dag: CausalDAG) -> list[str]:
        reasons: list[str] = []
        valid = [s for s in self._signatures.values() if s.signed_dag_hash == dag.dag_hash()]
        if len(valid) < MIN_REVIEWERS:
            reasons.append(
                f"Need ≥{MIN_REVIEWERS} signatures on this exact DAG; have {len(valid)}."
            )
        roles = {s.reviewer.role for s in valid}
        for required in REQUIRED_ROLES:
            if required not in roles:
                reasons.append(f"Missing a required reviewer role: {required!r}.")
        return reasons

    def issue(self, dag: CausalDAG) -> DagApprovalCertificate:
        """Mint a certificate, or raise with the precise reason it is refused."""
        validation = dag.validate(self.exposure, self.outcome, self.confounders)
        quorum_reasons = self._quorum_reasons(dag)
        if not validation.ok or quorum_reasons:
            raise DagApprovalError(
                "DAG approval refused. "
                + " ".join([*validation.reasons, *quorum_reasons])
            )
        valid_sigs = tuple(
            s for s in self._signatures.values() if s.signed_dag_hash == dag.dag_hash()
        )
        return DagApprovalCertificate(
            dag_hash=dag.dag_hash(),
            protocol_hash=self.protocol_hash,
            signatures=valid_sigs,
            validation=validation,
            _key=_MINT,
        )


def require_certificate(cert: DagApprovalCertificate, dag: CausalDAG, protocol_hash: str) -> None:
    """Guard the estimation entry point: refuse anything but a matching certificate."""
    if not isinstance(cert, DagApprovalCertificate):
        raise DagApprovalError("A valid DagApprovalCertificate is required to estimate.")
    if cert.dag_hash != dag.dag_hash():
        raise DagApprovalError("Certificate does not match the DAG being estimated on.")
    if cert.protocol_hash != protocol_hash:
        raise DagApprovalError("Certificate was issued for a different protocol.")
