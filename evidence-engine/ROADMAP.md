# Roadmap

This prototype builds the Phase-0 audit and a runnable Phase-1 emulation. The
phases below are **scaffolded as stubs** — each has a typed interface and a
`NotImplementedError` placeholder the core already calls — but are **not built**.
They are listed here so nothing overstates completeness.

Each stub maps to a specific harm in the three-harm model; filling it in is
*implementing an interface that already has callers and tests*, not a refactor.

## Phase 2 — defensibility of a single finding

### DAG-approval gate — ✅ BUILT (`protocol/dag_gate.py`, `protocol/causal_dag.py`)  (Harm c)
The causal graph is now an explicit, human-approved, hash-chained artifact the
estimator refuses to run without. A `DagApprovalCertificate` (an unforgeable
capability, like the outcome token) is minted only when (a) the DAG passes
structural checks — acyclic, every declared confounder a backdoor common-cause,
no adjustment on a mediator/collider — AND (b) ≥2 named reviewers including a
clinician and an affected-population voice sign the exact DAG hash. `require_certificate`
guards the estimation entry point. What remains irreducibly human: ensuring the
*signed graph is correct*.

### Multi-estimator concurrence — ✅ BUILT (`estimator/{iptw,aipw,matching,gcomputation,tmle}.py`)  (Harm a)
A five-estimator panel with *different* failure modes — IPTW (propensity-only),
AIPW and TMLE (doubly robust), propensity matching, and g-computation
(outcome-model only) — runs under the same sealed protocol and DAG.
`estimator/concurrence.py` reports sign/interval agreement across all of them and
feeds a pessimistic downgrade gate in `honesty/evidence_object.py`. Remaining
refinement: concurrence on the *calibrated* intervals rather than the raw ones.

## Phase 3 — defensibility of the method and across populations

### Validation harness — ✅ BUILT (`validation/`)
A Monte Carlo simulation study against a data-generating process with a KNOWN
marginal causal effect. Measures bias, CI coverage, Type I error, power, and
estimator concordance for IPTW and AIPW (vs a crude estimator as the confounded
control), and shows empirical-null calibration restoring negative-control coverage
under unmeasured confounding. `make validate` produces a report, a metrics JSON, an
operating-characteristics figure, and a pass/fail verdict (non-zero exit on fail).

### RCT-benchmark replay (follow-up) — `stubs/rct_benchmark.py`
Extends the validation harness to replay *specific published* randomized answers
(RCT-DUPLICATE / OHDSI LEGEND in spirit) and feed a method-level reliability
statement into the evidence tier. The simulation harness above already provides the
operating-characteristics machinery this would reuse.

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
