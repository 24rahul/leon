"""Time-zero enforcement and token-gated outcome access in the cohort."""

import numpy as np
import pandas as pd
import pytest

from evidence_engine.cohort.builder import (
    Cohort,
    TimeZeroError,
    assert_time_zero,
    build_cohort,
)
from evidence_engine.protocol.schema import Confounder, Eligibility, Protocol


def _sealed():
    return Protocol(
        name="toy",
        eligibility=Eligibility(min_age=18, require_icu_stay=True),
        exposure="x",
        outcome="y",
        time_zero="icu_admission",
        follow_up_days=28,
        estimand="ATE",
        confounders=(Confounder("age", "drives both"),),
    ).seal()


def _patients():
    return pd.DataFrame(
        {
            "subject_id": [1, 2, 3, 4],
            "age": [17, 40, 55, 70],  # subject 1 ineligible
            "x": [0, 1, 0, 1],
            "y": [0, 1, 0, 1],
            "icu_admission": [True, True, True, True],
        }
    )


def test_assert_time_zero_missing_column():
    with pytest.raises(TimeZeroError):
        assert_time_zero(pd.DataFrame({"a": [1]}), "icu_admission")


def test_assert_time_zero_some_false():
    df = pd.DataFrame({"icu_admission": [True, False, True]})
    with pytest.raises(TimeZeroError):
        assert_time_zero(df, "icu_admission")


def test_build_cohort_excludes_underage_and_aligns_t0():
    cohort = build_cohort(_sealed(), _patients())
    assert cohort.n_included == 3
    assert cohort.exclusions["age_below_min"] == 1


def test_outcome_requires_valid_token():
    sealed = _sealed()
    cohort = build_cohort(sealed, _patients())
    # A bare object is not a token.
    with pytest.raises(PermissionError):
        cohort.outcome("y", object())  # type: ignore[arg-type]
    # The right token works.
    y = cohort.outcome("y", sealed.outcome_token())
    assert set(np.unique(y)).issubset({0.0, 1.0})


def test_all_missing_outcome_fails_loud():
    sealed = _sealed()
    df = _patients()
    df["y"] = np.nan
    cohort = build_cohort(sealed, df)
    with pytest.raises(ValueError):
        cohort.outcome("y", sealed.outcome_token())
