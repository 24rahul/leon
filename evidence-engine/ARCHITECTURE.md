# Architecture — module map

A one-line responsibility per module. The design rationale (why the seams are
here, why Python, why a claim algebra) lives in [`DESIGN_CRITIQUE.md`](DESIGN_CRITIQUE.md).

```
src/evidence_engine/
├── config.py                  Load config.yaml; content-hash it for provenance.
├── logging_setup.py           Structured JSON-line logging.
├── provenance.py              Static fingerprint + content-addressed artifact ledger (Merkle root).
├── pipeline.py                Orchestrates every stage; the only place I/O + stages compose.
├── __main__.py                `python -m evidence_engine [config.yaml]`.
│
├── data/
│   ├── loader.py              Restricted-data guard; demo-or-surrogate; real MIMIC mapping.
│   └── synth.py               Deterministic surrogate with PLANTED, known biases.
│
├── audit/                     Phase 0 — runs first, unconditionally.
│   ├── phase0.py              Representation, pulse-ox probe, differential testing, MNAR.
│   └── report.py              Markdown audit report (passes the vocabulary guard).
│
├── protocol/
│   ├── schema.py              Frozen protocol; seal() → hash; OutcomeAccessToken capability.
│   ├── causal_dag.py          Explicit DAG; acyclicity + backdoor/mediator/collider checks.
│   ├── dag_gate.py            Human DAG-approval gate; unforgeable DagApprovalCertificate.
│   └── dag_approval.py        Config glue: build DAG, replay reviewer signatures, issue cert.
│
├── cohort/
│   └── builder.py             Eligibility + time-zero enforcement; token-gated outcome access.
│
├── estimator/
│   ├── iptw.py                Stabilized IPTW; balance (SMD); explicit missingness; bootstrap CI.
│   ├── aipw.py                Doubly-robust AIPW with efficient-influence-function SE.
│   ├── concurrence.py         IPTW-vs-AIPW agreement (sign + interval overlap) → downgrade gate.
│   ├── calibration.py         Empirical-null calibration from the negative-control panel (Schuemie).
│   ├── refutation.py          dowhy falsification probes (placebo / random cause / subset).
│   ├── evalue.py              E-value (VanderWeele & Ding), exact, point + CI limit.
│   └── units.py               Scale-safe NewTypes (RiskRatio vs LogRiskRatio), mypy-enforced.
│
├── equity/
│   └── stratify.py            Per-group estimation → PRESENT / SILENT / ABSENT classification.
│
├── honesty/
│   ├── claims.py              The closed claim algebra (Stance enum + pure rendering).
│   ├── vocabulary_guard.py    Defense-in-depth blacklist over every serialized string.
│   └── evidence_object.py     Pessimistic-gate tier decision; the one emitted result.
│
├── validation/                Data-driven proof the pipeline recovers known truth.
│   ├── dgp.py                 Data-generating process with a KNOWN marginal causal effect.
│   ├── simulation.py          Monte Carlo operating characteristics + pass/fail verdict.
│   └── report.py              Markdown report + operating-characteristics figure.
│
└── stubs/                     Typed interfaces + NotImplementedError (see ROADMAP.md).
    ├── multi_estimator.py     Multi-estimator concurrence       (Phase 2, Harm a — partial).
    ├── rct_benchmark.py       RCT-benchmark harness             (Phase 3).
    └── replication.py         Cross-dataset replication         (Phase 3, Harm b).
```

## Dataflow invariants (enforced, not conventional)

1. **Phase 0 before inference.** `pipeline.run` calls the audit before the cohort
   is built; its caveats are threaded into the final object.
2. **Seal before you see Y.** `cohort.outcome(...)` and every outcome read require
   an `OutcomeAccessToken`, mintable only from a `SealedProtocol`.
2b. **Approve the DAG before you estimate.** `require_certificate(...)` guards the
   cohort/estimation path; the `DagApprovalCertificate` is mintable only after the
   DAG passes structural checks and the human quorum signs (Harm c).
3. **Propensity fitted once.** Weights are reused for the primary outcome and every
   negative control, so calibration sees exactly the method it calibrates.
4. **Weakest-link tiering.** The evidence tier is `min` over independent gates;
   the floor is `INSUFFICIENT_EVIDENCE`.
5. **Everything is content-addressed.** The final `artifact_root` is a hash that
   transitively commits to data, audit, protocol, cohort, estimate, calibration,
   E-value, refutation, equity, and the object itself.

## Test coverage map

| Invariant | Test |
|---|---|
| Controlled vocabulary (incl. property test) | `tests/test_vocabulary_guard.py` |
| Frozen-protocol hash + capability token | `tests/test_protocol.py` |
| Time-zero enforcement + token-gated outcomes | `tests/test_cohort_timezero.py` |
| Explicit (never silent) missingness | `tests/test_missingness.py` |
| E-value closed form | `tests/test_evalue.py` |
| Empirical-null calibration + fail-loud | `tests/test_calibration.py` |
| AIPW recovery, concurrence, deterministic bootstrap | `tests/test_estimators.py` |
| DAG structural checks + unforgeable approval certificate | `tests/test_dag_gate.py` |
| Recovery of known truth, confounding removal, calibration repair | `tests/test_validation.py` |
| Provenance ledger chaining + tamper detection | `tests/test_provenance.py` |
| Restricted-data guard, end-to-end, byte-reproducibility | `tests/test_pipeline.py` |
```
