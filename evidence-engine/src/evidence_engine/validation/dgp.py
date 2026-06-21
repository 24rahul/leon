"""A data-generating process with a KNOWN marginal causal effect.

We simulate potential outcomes directly, so the estimand — the population marginal
risk ratio E[Y(1)] / E[Y(0)] — is known to arbitrary precision (computed by MC
integration over the covariate distribution on a large reference sample).

    X ~ N(0, I_k)                         measured confounders
    U ~ N(0, 1)                           optional UNMEASURED confounder
    P(A=1 | X,U) = expit(a0 + Xβ_a + γ_a U)
    p0(X,U)      = expit(g0 + Xβ_y + γ_y U)        baseline risk = risk under control
    p1(X,U)      = clip(p0 · RR_cond, 0, 1)        risk under treatment
    Y(a) ~ Bernoulli(p_a),   Y = A·Y(1) + (1−A)·Y(0)

Because A depends on the same X (and U) that drive Y, the crude association is
confounded — the naive estimate is biased, and a correct pipeline must remove that
bias. Setting γ_a, γ_y > 0 with U withheld from the estimator creates *residual*
confounding that empirical-null calibration is meant to detect and correct.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


def _expit(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


@dataclass(frozen=True)
class DGP:
    k_confounders: int = 4
    beta_y: tuple[float, ...] = (0.7, 0.5, 0.4, 0.3)   # X -> outcome
    beta_a: tuple[float, ...] = (0.8, 0.6, -0.5, 0.4)  # X -> treatment (confounding)
    g0: float = -1.4                                    # baseline outcome intercept (~20% risk)
    a0: float = -0.2                                    # treatment intercept (~45% treated)
    rr_cond: float = 1.6                                # conditional (= marginal here) risk ratio
    gamma_a_u: float = 0.0                              # unmeasured confounder -> treatment
    gamma_y_u: float = 0.0                              # unmeasured confounder -> outcome

    confounder_names: tuple[str, ...] = field(default_factory=tuple)

    def names(self) -> list[str]:
        return list(self.confounder_names) or [f"x{i}" for i in range(self.k_confounders)]

    # --- ground truth ------------------------------------------------------
    def true_marginal_rr(self, n_ref: int = 400_000, seed: int = 999_983) -> float:
        """Population marginal RR = E[p1] / E[p0], by large-sample MC integration."""
        rng = np.random.default_rng(seed)
        X = rng.normal(size=(n_ref, self.k_confounders))
        u = rng.normal(size=n_ref)
        by = np.array(self.beta_y[: self.k_confounders])
        p0 = _expit(self.g0 + X @ by + self.gamma_y_u * u)
        p1 = np.clip(p0 * self.rr_cond, 0.0, 1.0)
        return float(p1.mean() / p0.mean())

    # --- one simulated dataset --------------------------------------------
    def sample(self, n: int, seed: int, *, n_neg_controls: int = 0) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        k = self.k_confounders
        X = rng.normal(size=(n, k))
        u = rng.normal(size=n)
        by = np.array(self.beta_y[:k])
        ba = np.array(self.beta_a[:k])

        ps = _expit(self.a0 + X @ ba + self.gamma_a_u * u)
        a = (rng.random(n) < ps).astype(int)

        p0 = _expit(self.g0 + X @ by + self.gamma_y_u * u)
        p1 = np.clip(p0 * self.rr_cond, 0.0, 1.0)
        y0 = (rng.random(n) < p0).astype(int)
        y1 = (rng.random(n) < p1).astype(int)
        y = np.where(a == 1, y1, y0)

        data = {name: X[:, i] for i, name in enumerate(self.names())}
        data["treat"] = a
        data["y"] = y
        df = pd.DataFrame(data)

        # Negative-control outcomes: TRUE effect of A is null (RR=1), but they share
        # the same confounding structure (driven by X and U), so a method with
        # residual confounding will show spurious associations the null must absorb.
        for j in range(n_neg_controls):
            bj = rng.normal(0.3, 0.2, size=k)  # each NC has its own X-dependence
            pj = _expit(-1.6 + X @ bj + self.gamma_y_u * u)
            df[f"nc_{j}"] = (rng.random(n) < pj).astype(int)

        return df
