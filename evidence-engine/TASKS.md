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

## 2. Full estimator panel  (Harm a) — `estimator/{matching,gcomputation,tmle}.py`
- [ ] Propensity-matching estimator (1:1 nearest-neighbour on logit PS, caliper)
- [ ] G-computation / standardization (outcome model, marginal effect)
- [ ] TMLE (targeted maximum likelihood; doubly robust + EIF inference)
- [ ] Extend `concurrence.compare` to N estimators (pairwise agreement, max gap)
- [ ] Wire panel into pipeline; concurrence gate over the full panel
- [ ] Tests: each estimator recovers planted effect; panel concurrence agree/disagree
- [ ] Docs + diagram update

## 3. RCT-benchmark harness — `validation/rct_benchmark.py`
- [ ] Define benchmark cases (known RCT direction/effect) over the synthetic surrogate
- [ ] Run the sealed-protocol pipeline per case; measure sign-concordance + interval coverage
- [ ] Produce a method-level reliability statistic that can feed the tier
- [ ] Tests + a `make benchmark` target
- [ ] Docs

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
