"""Phase 0 — the data-generating-process audit.

This runs FIRST and unconditionally. Inference is not permitted until the
dataset has been characterized as a biased artifact. The audit produces
machine-readable results plus a set of *caveats* that are carried forward and
attached to every downstream evidence object.

Four probes:
  1. Cohort representation by demographics (with the non-representativeness flag).
  2. Pulse-oximetry measurement bias (occult hypoxemia by recorded race).
  3. Differential testing rates by recorded race.
  4. Missing-not-at-random characterization, with missingness indicators promoted
     to first-class variables and silent imputation explicitly forbidden.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class Phase0Result:
    data_version: str
    is_synthetic: bool
    n_patients: int
    representation: dict[str, Any]
    pulse_oximetry: dict[str, Any]
    differential_testing: dict[str, Any]
    missingness: dict[str, Any]
    caveats: list[str] = field(default_factory=list)
    forbid_imputation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _age_group(age: pd.Series) -> pd.Series:
    bins = [0, 40, 55, 70, 85, 200]
    labels = ["18-39", "40-54", "55-69", "70-84", "85+"]
    return pd.cut(age, bins=bins, labels=labels, right=False)


def _representation(patients: pd.DataFrame, strata: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    df = patients.copy()
    if "age" in df:
        df["age_group"] = _age_group(df["age"])
    n = len(df)
    for col in strata:
        if col not in df:
            continue
        counts = df[col].value_counts(dropna=False)
        out[col] = {
            str(k): {"count": int(v), "proportion": round(v / n, 4)}
            for k, v in counts.items()
        }
    return out


def _pulse_oximetry_probe(
    abg: pd.DataFrame,
    patients: pd.DataFrame,
    *,
    sao2_max: float,
    spo2_low: float,
    spo2_high: float,
) -> dict[str, Any]:
    """Occult hypoxemia: SaO2 < sao2_max while SpO2 reads reassuring [low, high].

    Reported per recorded race. This is the canonical demonstration that a
    recorded variable (SpO2) is racially biased before any model runs.
    """
    if abg.empty:
        return {
            "available": False,
            "reason": "no paired SaO2/SpO2 measurements available",
        }

    df = abg.copy()
    # Ensure a race column (real-data ABG lacks it; merge from patients).
    if "race" not in df.columns:
        df = df.merge(patients[["subject_id", "race"]], on="subject_id", how="left")
    df = df.dropna(subset=["sao2", "spo2"])

    df["occult_hypoxemia"] = (
        (df["sao2"] < sao2_max)
        & (df["spo2"] >= spo2_low)
        & (df["spo2"] <= spo2_high)
    )
    # Denominator: paired readings where the pulse-ox looked reassuring.
    df["reassuring_spo2"] = (df["spo2"] >= spo2_low) & (df["spo2"] <= spo2_high)

    by_race: dict[str, Any] = {}
    for race, g in df.groupby("race", dropna=False):
        reassuring = g[g["reassuring_spo2"]]
        denom = len(reassuring)
        occult = int(reassuring["occult_hypoxemia"].sum())
        by_race[str(race)] = {
            "n_paired_readings": int(len(g)),
            "n_reassuring_spo2": int(denom),
            "n_occult_hypoxemia": occult,
            "occult_hypoxemia_rate": round(occult / denom, 4) if denom else None,
            "mean_spo2_minus_sao2": round(float((g["spo2"] - g["sao2"]).mean()), 3),
        }

    return {
        "available": True,
        "definition": {
            "sao2_below": sao2_max,
            "spo2_reassuring_band": [spo2_low, spo2_high],
        },
        "by_race": by_race,
        "overall_mean_spo2_minus_sao2": round(
            float((df["spo2"] - df["sao2"]).mean()), 3
        ),
    }


def _differential_testing(patients: pd.DataFrame) -> dict[str, Any]:
    """Rate at which key measurements were ordered, by recorded race."""
    if "lactate_observed" not in patients or "race" not in patients:
        return {"available": False}
    g = patients.groupby("race")["lactate_observed"]
    rates = {
        str(race): {
            "n": int(cnt),
            "lactate_ordered_rate": round(float(mean), 4),
        }
        for race, mean, cnt in zip(g.mean().index, g.mean().values, g.count().values)
    }
    return {
        "available": True,
        "note": "Ordering is a signal of access/suspicion, not neutral ascertainment.",
        "by_race": rates,
    }


def _missingness(patients: pd.DataFrame, no_impute: list[str]) -> dict[str, Any]:
    """Characterize missingness; produce indicators; forbid silent imputation."""
    cols = [c for c in patients.columns if c not in ("subject_id",)]
    miss: dict[str, Any] = {}
    for c in cols:
        n_missing = int(patients[c].isna().sum())
        if n_missing:
            miss[c] = {
                "n_missing": n_missing,
                "fraction_missing": round(n_missing / len(patients), 4),
            }
    # Is lactate missingness associated with severity / race? (MNAR signal.)
    mnar_signal: dict[str, Any] = {}
    if "lactate" in patients and "sofa_proxy" in patients:
        present = patients["lactate"].notna()
        if present.nunique() > 1 and patients["sofa_proxy"].notna().any():
            mnar_signal["lactate_vs_severity"] = {
                "mean_sofa_when_observed": round(
                    float(patients.loc[present, "sofa_proxy"].mean()), 3
                ),
                "mean_sofa_when_missing": round(
                    float(patients.loc[~present, "sofa_proxy"].mean()), 3
                ),
            }
    return {
        "columns_with_missing": miss,
        "mnar_signal": mnar_signal,
        "indicators_created": [f"{c}_missing" for c in miss],
        "silent_imputation_forbidden_for": list(no_impute),
    }


def add_missingness_indicators(patients: pd.DataFrame) -> pd.DataFrame:
    """Promote missingness to first-class variables (one indicator per col)."""
    df = patients.copy()
    for c in list(df.columns):
        if c == "subject_id":
            continue
        if df[c].isna().any():
            df[f"{c}_missing"] = df[c].isna().astype(int)
    return df


def _build_caveats(result_parts: dict[str, Any], is_synthetic: bool) -> list[str]:
    caveats: list[str] = []
    if is_synthetic:
        caveats.append(
            "Data are a SYNTHETIC surrogate, not real MIMIC-IV; findings are "
            "illustrative of the machinery only and carry no clinical meaning."
        )
    caveats.append(
        "Source is single-center ICU data and is NOT representative of any "
        "general population; effects observed here may not transfer."
    )
    po = result_parts.get("pulse_oximetry", {})
    if po.get("available"):
        rates = {
            k: v["occult_hypoxemia_rate"]
            for k, v in po["by_race"].items()
            if v["occult_hypoxemia_rate"] is not None
        }
        if rates:
            worst = max(rates, key=lambda k: rates[k])
            caveats.append(
                f"Pulse-oximetry probe: occult-hypoxemia rate varies by recorded "
                f"race (highest in {worst!r}); SpO2 is a racially biased measurement "
                "and any analysis using it inherits that bias."
            )
    dt = result_parts.get("differential_testing", {})
    if dt.get("available"):
        caveats.append(
            "Measurement/testing rates differ by recorded race; observed values "
            "are conditioned on differential ascertainment."
        )
    caveats.append(
        "Equity-relevant variables are never silently imputed; missingness is "
        "carried as explicit indicator variables."
    )
    return caveats


def run_phase0(
    tables: dict[str, pd.DataFrame],
    data_version: str,
    *,
    audit_cfg: dict,
) -> Phase0Result:
    patients = tables["patients"]
    abg = tables.get("abg", pd.DataFrame())
    is_synthetic = data_version.startswith("synthetic")

    representation = _representation(patients, audit_cfg["equity_strata"])
    pulse = _pulse_oximetry_probe(
        abg,
        patients,
        sao2_max=float(audit_cfg["occult_hypoxemia_sao2_max"]),
        spo2_low=float(audit_cfg["spo2_reassuring_low"]),
        spo2_high=float(audit_cfg["spo2_reassuring_high"]),
    )
    differential = _differential_testing(patients)
    missingness = _missingness(patients, audit_cfg["no_impute_variables"])

    parts = {
        "pulse_oximetry": pulse,
        "differential_testing": differential,
    }
    caveats = _build_caveats(parts, is_synthetic)

    return Phase0Result(
        data_version=data_version,
        is_synthetic=is_synthetic,
        n_patients=int(len(patients)),
        representation=representation,
        pulse_oximetry=pulse,
        differential_testing=differential,
        missingness=missingness,
        caveats=caveats,
        forbid_imputation=list(audit_cfg["no_impute_variables"]),
    )
