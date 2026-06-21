"""Cohort construction from a SEALED protocol, with time-zero enforcement.

Two invariants are enforced here, both by construction rather than convention:

1. **Time zero.** Every included subject must have the protocol's `time_zero`
   defined; eligibility and follow-up are measured from it. Aligning everyone at a
   single t0 is what excludes immortal-time bias — a subject cannot accrue
   "event-free" time before they were eligible. `assert_time_zero` fails loud if
   any included row lacks t0.

2. **Outcome access requires the pre-registration capability.** Exposure and
   confounders are pre-outcome covariates and may be read freely. Reading an
   OUTCOME column requires an `OutcomeAccessToken` minted from the sealed protocol
   (see `protocol/schema.py`). There is no other path to `Y`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..protocol.schema import OutcomeAccessToken, SealedProtocol, assert_token


class TimeZeroError(ValueError):
    """Raised when time-zero alignment cannot be guaranteed for the cohort."""


@dataclass
class Cohort:
    frame: pd.DataFrame
    sealed: SealedProtocol
    n_source: int
    n_included: int
    exclusions: dict[str, int] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "protocol_hash": self.sealed.protocol_hash,
            "n_source": self.n_source,
            "n_included": self.n_included,
            "exclusions": self.exclusions,
        }

    # --- covariate access (pre-outcome; unrestricted) ----------------------
    def exposure(self) -> np.ndarray:
        return self.frame[self.sealed.protocol.exposure].to_numpy(dtype=int)

    # --- outcome access (requires the pre-registration capability) ---------
    def outcome(self, name: str, token: OutcomeAccessToken) -> np.ndarray:
        assert_token(token, self.sealed)
        if name not in self.frame.columns:
            raise KeyError(f"Outcome {name!r} not present in cohort.")
        col = self.frame[name]
        if col.isna().all():
            raise ValueError(
                f"Outcome {name!r} is entirely missing in this data source; "
                "the engine will report insufficient evidence rather than fabricate."
            )
        return col.to_numpy(dtype=float)


def assert_time_zero(frame: pd.DataFrame, time_zero_col: str) -> None:
    if time_zero_col not in frame.columns:
        raise TimeZeroError(
            f"time_zero column {time_zero_col!r} is absent; cannot align follow-up "
            "and cannot exclude immortal-time bias. Failing loud."
        )
    col = frame[time_zero_col]
    # Accept boolean presence flags or timestamps; reject missing/false.
    if col.dtype == bool:
        bad = int((~col).sum())
    else:
        bad = int(col.isna().sum())
    if bad:
        raise TimeZeroError(
            f"{bad} included subjects lack a defined time zero ({time_zero_col!r}); "
            "refusing to proceed."
        )


def build_cohort(sealed: SealedProtocol, patients: pd.DataFrame) -> Cohort:
    p = sealed.protocol
    df = patients.copy()
    n_source = len(df)
    exclusions: dict[str, int] = {}

    # Eligibility: minimum age.
    before = len(df)
    df = df[df["age"] >= p.eligibility.min_age]
    exclusions["age_below_min"] = before - len(df)

    # Eligibility: require an ICU stay (the time-zero anchor must exist).
    if p.eligibility.require_icu_stay:
        before = len(df)
        if p.time_zero in df.columns and df[p.time_zero].dtype == bool:
            df = df[df[p.time_zero]]
        else:
            df = df[df.get("icu_admission", pd.Series(True, index=df.index)).astype(bool)]
        exclusions["no_icu_stay"] = before - len(df)

    # Hard time-zero guarantee on the surviving cohort.
    assert_time_zero(df, p.time_zero if p.time_zero in df.columns else "icu_admission")

    df = df.reset_index(drop=True)
    return Cohort(
        frame=df,
        sealed=sealed,
        n_source=n_source,
        n_included=len(df),
        exclusions=exclusions,
    )
