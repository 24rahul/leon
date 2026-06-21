"""The controlled-vocabulary guard is the safety net behind the claim algebra."""

import pytest
from hypothesis import given, strategies as st

from evidence_engine.honesty.claims import Claim, Stance
from evidence_engine.honesty.vocabulary_guard import (
    ControlledVocabularyError,
    find_violations,
    guard_object,
    guard_text,
)

FORBIDDEN_EXAMPLES = [
    "this is true",
    "the drug is effective",
    "it is safe",
    "the effect is proven",
    "we recommend this",
    "clinicians should act",
    "the exposure causes death",
    "it caused harm",
    "this proves the point",
    "highly effective treatment",
]


@pytest.mark.parametrize("text", FORBIDDEN_EXAMPLES)
def test_forbidden_words_raise(text):
    with pytest.raises(ControlledVocabularyError):
        guard_text(text)


def test_allowed_framing_passes():
    ok = (
        "These data are consistent with an association; the result is "
        "hypothesis-generating and requires confirmatory trial."
    )
    assert guard_text(ok) == ok


def test_nested_object_is_scanned():
    bad = {"a": {"b": ["fine", "this is proven"]}}
    with pytest.raises(ControlledVocabularyError):
        guard_object(bad)


def test_dict_keys_are_scanned():
    with pytest.raises(ControlledVocabularyError):
        guard_object({"recommend": "value"})


@given(
    prefix=st.text(alphabet=st.characters(whitelist_categories=("L", "Zs")), max_size=20),
    suffix=st.text(alphabet=st.characters(whitelist_categories=("L", "Zs")), max_size=20),
    word=st.sampled_from(["true", "effective", "safe", "proven", "recommend", "should", "causes"]),
)
def test_property_any_forbidden_stem_raises(prefix, suffix, word):
    text = f"{prefix} {word} {suffix}"
    assert find_violations(text)  # non-empty
    with pytest.raises(ControlledVocabularyError):
        guard_text(text)


def test_every_stance_renders_clean():
    # The claim algebra must never produce a string the guard would reject.
    for stance in Stance:
        c = Claim(stance=stance, exposure="X", outcome="Y", scope="research context C")
        guard_text(c.render())  # must not raise
