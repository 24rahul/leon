"""Frozen-protocol hash and the pre-registration capability."""

import dataclasses

import pytest

from evidence_engine.protocol.schema import (
    Confounder,
    Eligibility,
    OutcomeAccessToken,
    Protocol,
    assert_token,
)


def _proto(**overrides):
    base = dict(
        name="toy",
        eligibility=Eligibility(min_age=18, require_icu_stay=True),
        exposure="x",
        outcome="y",
        time_zero="icu_admission",
        follow_up_days=28,
        estimand="ATE",
        confounders=(Confounder("age", "drives both"),),
        negative_control_outcomes=("nc_a",),
    )
    base.update(overrides)
    return Protocol(**base)


def test_hash_is_stable_and_content_sensitive():
    a = _proto()
    b = _proto()
    assert a.seal().protocol_hash == b.seal().protocol_hash
    c = _proto(follow_up_days=30)
    assert c.seal().protocol_hash != a.seal().protocol_hash


def test_protocol_is_immutable():
    a = _proto()
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.exposure = "z"  # type: ignore[misc]


def test_confounder_requires_justification():
    with pytest.raises(ValueError):
        Confounder("age", "   ")


def test_time_zero_required():
    with pytest.raises(ValueError):
        _proto(time_zero="")


def test_token_cannot_be_forged():
    with pytest.raises(RuntimeError):
        OutcomeAccessToken("deadbeef", object())  # wrong key


def test_seal_mints_matching_token():
    sealed = _proto().seal()
    token = sealed.outcome_token()
    assert token.protocol_hash == sealed.protocol_hash
    assert_token(token, sealed)  # must not raise


def test_token_from_other_protocol_rejected():
    sealed_a = _proto().seal()
    sealed_b = _proto(name="other").seal()
    token_b = sealed_b.outcome_token()
    with pytest.raises(PermissionError):
        assert_token(token_b, sealed_a)
