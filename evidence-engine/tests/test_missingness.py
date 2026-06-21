"""Missingness is explicit (indicator method) and never silent for equity vars."""

import numpy as np
import pandas as pd
import pytest

from evidence_engine.audit.phase0 import add_missingness_indicators
from evidence_engine.estimator.iptw import build_design_matrix


def test_missing_indicator_method_for_allowed_confounder():
    df = pd.DataFrame({"lactate": [1.0, np.nan, 3.0, np.nan]})
    X, notes = build_design_matrix(df, ["lactate"], no_impute=[])
    assert "lactate_missing" in X.columns
    assert X["lactate_missing"].tolist() == [0.0, 1.0, 0.0, 1.0]
    assert "lactate" in notes  # the action was logged


def test_no_impute_variable_fails_loud():
    df = pd.DataFrame({"sex_num": [1.0, np.nan]})
    with pytest.raises(ValueError):
        build_design_matrix(df, ["sex_num"], no_impute=["sex_num"])


def test_add_missingness_indicators_promotes_first_class():
    df = pd.DataFrame(
        {"subject_id": [1, 2, 3], "lactate": [1.0, np.nan, 3.0], "age": [40, 50, 60]}
    )
    out = add_missingness_indicators(df)
    assert "lactate_missing" in out.columns
    assert "age_missing" not in out.columns  # no missing -> no indicator
    assert out["lactate_missing"].tolist() == [0, 1, 0]
