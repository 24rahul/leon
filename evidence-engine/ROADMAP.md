# Roadmap

This prototype builds the Phase-0 audit and a runnable Phase-1 emulation. The
phases below are **scaffolded as stubs** — each has a typed interface and a
`NotImplementedError` placeholder the core already calls — but are **not built**.
They are listed here so nothing overstates completeness.

Each stub maps to a specific harm in the three-harm model; filling it in is
*implementing an interface that already has callers and tests*, not a refactor.

## Phase 2 — defensibility of a single finding

### DAG-approval gate — `stubs/dag_gate.py`  (Harm c)
Make the causal graph an explicit, human-approved, hash-chained artifact the
estimator refuses to run without. Require sign-off from ≥2 named reviewers
(clinician + someone from an affected population). Verify acyclicity, that every
declared confounder is a backdoor node, and that no adjustment set conditions on a
collider or mediator. **This is the single largest current gap** — the prototype
trusts the config-declared confounders.

### Multi-estimator concurrence — `stubs/multi_estimator.py`  (Harm a)
Run a panel of estimators with *different* failure modes (IPTW [built], propensity
matching, g-computation/standardization, doubly-robust AIPW/TMLE) under the same
sealed protocol and DAG. Report sign/interval agreement and add a concurrence
downgrade as a new pessimistic gate in `honesty/evidence_object.py`.

## Phase 3 — defensibility of the method and across populations

### RCT-benchmark harness — `stubs/rct_benchmark.py`
Replay questions with known randomized answers (RCT-DUPLICATE / OHDSI LEGEND in
spirit); measure sign-concordance and interval coverage to produce a
*method-level* reliability statement that feeds the evidence tier.

### Cross-dataset replication — `stubs/replication.py`  (Harm b)
Execute the identical sealed protocol against ≥2 independent OMOP sources (each
behind its own restricted-data guard); combine the *calibrated* estimates via
random-effects meta-analysis with heterogeneity (I², τ²) reported; downgrade on
disagreement. Never pool away heterogeneity silently.

## Cross-cutting, later

- Time-to-event estimands via `lifelines` (the dependency is already pinned) for
  outcomes where 28-day mortality is too blunt.
- A real OMOP-CDM ETL for the credentialed path, and a port of the calibration
  step onto OHDSI `EmpiricalCalibration` for parity with the production stack.
- Richer positivity diagnostics (propensity overlap plots, per-stratum ESS).
