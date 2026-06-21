"""Content-addressed provenance ledger: chaining and tamper detection."""

import dataclasses

from evidence_engine.provenance import Artifact, ArtifactLedger, canonical_hash


def test_canonical_hash_is_order_independent():
    assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})


def test_ledger_chains_and_verifies():
    led = ArtifactLedger()
    a = led.add("data", {"v": 1})
    b = led.add("audit", {"n": 10}, (a,))
    c = led.add("evidence", {"tier": "X"}, (b,))
    assert led.root == c
    assert led.verify() is True
    # Each child commits to its parent: changing a parent changes the root.
    assert b != a and c != b


def test_ledger_detects_tampering():
    led = ArtifactLedger()
    a = led.add("data", {"v": 1})
    led.add("audit", {"n": 10}, (a,))
    assert led.verify() is True
    # Tamper with a stored payload digest without recomputing the id.
    bad = dataclasses.replace(led.artifacts[1], payload_digest="deadbeef")
    led.artifacts[1] = bad
    assert led.verify() is False


def test_root_of_empty_ledger_raises():
    led = ArtifactLedger()
    try:
        _ = led.root
        assert False, "expected ValueError"
    except ValueError:
        pass
