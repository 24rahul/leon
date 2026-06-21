"""Human DAG-approval gate: structural checks + unforgeable capability."""

import pytest

from evidence_engine.protocol.causal_dag import CausalDAG, dag_from_protocol
from evidence_engine.protocol.dag_gate import (
    DagApprovalCertificate,
    DagApprovalError,
    DagApprovalGate,
    Reviewer,
    require_certificate,
)


def _good_dag():
    # c is a common cause of x and y; x -> y. Adjust for c only.
    return CausalDAG(
        nodes=("c", "x", "y"),
        edges=(("c", "x"), ("c", "y"), ("x", "y")),
        adjustment_set=("c",),
    )


def _reviewers(gate, dag):
    gate.sign(dag, Reviewer("Dr. Who", "clinician", "Hosp"))
    gate.sign(dag, Reviewer("A. Advocate", "affected_population", "Council"))


# --- structural validation -------------------------------------------------
def test_dag_from_protocol_is_canonical_and_valid():
    dag = dag_from_protocol("x", "y", ["c1", "c2"])
    v = dag.validate("x", "y", ["c1", "c2"])
    assert v.ok and v.is_acyclic
    assert all(v.confounders_are_backdoor.values())


def test_cycle_is_rejected():
    dag = CausalDAG(("a", "b"), (("a", "b"), ("b", "a")), ())
    assert dag.is_acyclic() is False
    assert dag.validate("a", "b", []).ok is False


def test_non_backdoor_confounder_is_rejected():
    # z only causes y, not x -> not a confounder of x->y.
    dag = CausalDAG(("x", "y", "z"), (("x", "y"), ("z", "y")), ("z",))
    v = dag.validate("x", "y", ["z"])
    assert v.confounders_are_backdoor["z"] is False
    assert v.ok is False


def test_mediator_in_adjustment_set_is_rejected():
    # m is a descendant of x (a mediator); conditioning on it is forbidden.
    dag = CausalDAG(
        ("c", "x", "m", "y"),
        (("c", "x"), ("c", "y"), ("x", "m"), ("m", "y")),
        ("c", "m"),
    )
    v = dag.validate("x", "y", ["c"])
    assert "m" in v.bad_adjustments
    assert v.ok is False


# --- quorum + roles --------------------------------------------------------
def test_issue_requires_two_reviewers():
    dag = _good_dag()
    gate = DagApprovalGate("x", "y", ["c"], "proto-hash")
    gate.sign(dag, Reviewer("Solo", "clinician", "Hosp"))
    with pytest.raises(DagApprovalError, match="2 signatures"):
        gate.issue(dag)


def test_issue_requires_affected_population_role():
    dag = _good_dag()
    gate = DagApprovalGate("x", "y", ["c"], "proto-hash")
    gate.sign(dag, Reviewer("Doc A", "clinician", "Hosp"))
    gate.sign(dag, Reviewer("Doc B", "clinician", "Hosp"))
    with pytest.raises(DagApprovalError, match="affected_population"):
        gate.issue(dag)


def test_signature_must_match_current_dag_hash():
    dag = _good_dag()
    gate = DagApprovalGate("x", "y", ["c"], "proto-hash")
    _reviewers(gate, dag)
    # Mutate the DAG after signing: the old signatures no longer count.
    mutated = CausalDAG(dag.nodes, dag.edges + (("y", "c"),), dag.adjustment_set)
    with pytest.raises(DagApprovalError):
        gate.issue(mutated)


def test_happy_path_issues_and_validates():
    dag = _good_dag()
    gate = DagApprovalGate("x", "y", ["c"], "proto-hash")
    _reviewers(gate, dag)
    cert = gate.issue(dag)
    assert isinstance(cert, DagApprovalCertificate)
    assert len(cert.signatures) == 2
    require_certificate(cert, dag, "proto-hash")  # does not raise


# --- unforgeable capability ------------------------------------------------
def test_certificate_cannot_be_constructed_directly():
    dag = _good_dag()
    v = dag.validate("x", "y", ["c"])
    with pytest.raises(DagApprovalError, match="cannot be constructed directly"):
        DagApprovalCertificate("h", "p", (), v, _key=object())


def test_require_certificate_rejects_mismatched_protocol():
    dag = _good_dag()
    gate = DagApprovalGate("x", "y", ["c"], "proto-hash")
    _reviewers(gate, dag)
    cert = gate.issue(dag)
    with pytest.raises(DagApprovalError, match="different protocol"):
        require_certificate(cert, dag, "WRONG-hash")


def test_require_certificate_rejects_mismatched_dag():
    dag = _good_dag()
    gate = DagApprovalGate("x", "y", ["c"], "proto-hash")
    _reviewers(gate, dag)
    cert = gate.issue(dag)
    other = dag_from_protocol("x", "y", ["c", "extra"])
    with pytest.raises(DagApprovalError, match="does not match"):
        require_certificate(cert, other, "proto-hash")
