# Build Task List

Living checklist for completing the Phase-2/Phase-3 roadmap. Updated as work lands.
Order is by value and dependency: the DAG gate first (closes the trust boundary),
then the estimator panel, then the two validation harnesses, then real-data ETL.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done

## 1. DAG-approval gate  (Harm c) — `protocol/dag_gate.py`, `protocol/causal_dag.py`  ✅ DONE
- [x] `CausalDAG`: frozen, hashable; nodes + directed edges + declared adjustment set
- [x] Acyclicity check (pure-Python Kahn topo-sort, no networkx coupling)
- [x] Structural validation vs sealed protocol (backdoor confounders; no mediator/collider adjustment)
- [x] `Reviewer` + `Signature` over the DAG hash
- [x] `DagApprovalCertificate` — unforgeable capability; quorum + role rules enforced
- [x] Pipeline: build DAG from config, require certificate before cohort/estimation, ledger it
- [x] Config: `dag:` block (extra_edges + reviewers)
- [x] Tests: 11 cases (acyclicity, backdoor, mediator/collider, quorum/role, unforgeable cert, e2e)
- [x] Docs: README, DESIGN_CRITIQUE, ARCHITECTURE, ROADMAP, diagram un-stubbed

## 2. Full estimator panel  (Harm a) — `estimator/{matching,gcomputation,tmle}.py`  ✅ DONE
- [x] Propensity-matching estimator (1:1 nearest-neighbour on logit PS, caliper)
- [x] G-computation / standardization (outcome model, marginal effect, bootstrap SE)
- [x] TMLE (targeted maximum likelihood; doubly robust + EIF inference)
- [x] Extend `concurrence.compare` to N estimators (common-interval overlap, max gap)
- [x] Wire panel into pipeline; concurrence gate over the full panel
- [x] Tests: each estimator recovers planted effect; 5-estimator panel concurrence
- [x] Docs + diagram update; multi_estimator stub removed

## 3. Validation harness (does the pipeline work?) — `validation/`  ✅ DONE
- [x] `dgp.py`: data-generating process with a KNOWN marginal causal effect (MC-integrated truth)
- [x] `simulation.py`: recovery study (bias, RMSE, coverage, Type I error, power, concordance)
- [x] Crude vs IPTW vs AIPW comparison — proves confounding is actually removed
- [x] Calibration study: unmeasured confounder → leave-one-out empirical-null coverage repair
- [x] `report.py`: markdown report + 4-panel operating-characteristics figure
- [x] CLI `python -m evidence_engine.validation` (non-zero exit on failure) + `make validate`
- [x] Tests (recovery, calibration, full verdict) + README "Does it actually work?" section
- [ ] FOLLOW-UP: replay specific published RCT results (RCT-DUPLICATE-style external validity)

## 4. Cross-dataset replication  (Harm b) — `validation/replication.py`
- [ ] Run identical sealed protocol against ≥2 independent synthetic sources (each guarded)
- [ ] Random-effects meta-analysis of CALIBRATED estimates with I²/τ² heterogeneity
- [ ] Downgrade gate on heterogeneity/disagreement; never pool heterogeneity silently
- [ ] Tests + docs

## 5. Real-data ETL (OMOP/MIMIC) — `data/omop.py`
- [ ] OMOP-CDM-style mapping from MIMIC-IV demo tables to the engine's cohort schema
- [ ] Keep the restricted-data guard; demo-only by default
- [ ] Tests on the synthetic/demo surrogate
- [ ] Docs

## Cross-cutting
- [ ] Keep mypy clean, 100% of tests green, output byte-reproducible after every change
- [ ] Update `docs/dataflow.mmd` + regenerate `docs/dataflow.png` as gates are added
