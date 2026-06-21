# Evidence Engine

A **fail-safe target-trial-emulation prototype** that generates *hypotheses* —
never recommendations — from observational health data. It is built around a
single, uncompromising idea:

> The only thing this system is allowed to say is that, within one pre-registered
> research context, the data are **consistent with** an association that is
> **hypothesis-generating** and **requires confirmatory trial** — or that there is
> **insufficient evidence**. Any stronger statement is *unrepresentable*, not
> merely discouraged.

If you read nothing else, read [`DESIGN_CRITIQUE.md`](DESIGN_CRITIQUE.md): it is
the adversarial first-principles evaluation that drove every decision here, and it
is honest about what remains weak.

---

## What this is (and is not)

- It **is** a runnable Phase-0 data-bias audit plus a Phase-1 target-trial
  emulation (cohort → IPTW → negative-control empirical calibration → refutation →
  E-value → equity stratification → a guarded evidence object), wired end-to-end
  with content-addressed provenance and byte-reproducible output.
- It is **not** a clinical decision tool. There is no code path from this engine
  to an action. See the three-harm model below.
- It is **not** production-grade. Production work in this space is the OHDSI/OMOP
  R stack (the HADES packages: `CohortMethod`, `EmpiricalCalibration`). This is a
  faithful Python prototype whose architecture deliberately mirrors the OMOP
  common-data-model concepts and the empirical-calibration idea so it can later be
  backed by that stack without redesign.

---

## Quickstart

```bash
make setup     # create .venv and install pinned dependencies
make run       # run the full pipeline
make test      # run the test suite (pytest)
make typecheck # mypy --strict-ish, clean
make reproduce # run twice; assert byte-identical evidence output
```

`make run` produces, under `outputs/`:

- `phase0_audit_report.md` — the data-generating-process audit (committed example
  in [`examples/`](examples/)).
- `evidence_object.json` — one sample evidence object for the toy
  exposure/outcome question, carrying its estimate, calibration, E-value, audit
  caveats, equity breakdown, assumptions, evidence tier, and the full
  content-addressed provenance ledger.

---

## Data: the open MIMIC-IV demo, or a deterministic surrogate

The engine is designed for the **openly available MIMIC-IV *demo*** dataset (no
credentialing). It will **never** touch credentialed/full MIMIC: `config.data`
exposes a `full_data_path` that defaults to `null` and a `forbid_restricted`
guard that *raises* if you try to use it (`data/loader.py`).

When the demo data is not present on disk (e.g. an offline environment), the
loader generates a **deterministic synthetic surrogate** (`data/synth.py`) with
*known, planted biases* so the safety machinery is demonstrable and the output is
byte-reproducible. **Every output is clearly labelled synthetic in that case.**
Point `config.data.demo_path` at a real demo download to use real data; the
analytic schema is identical so nothing downstream changes.

> The committed example outputs were produced on the synthetic surrogate, because
> the build environment is offline. They are illustrative of the *machinery*, not
> of clinical reality. A planted bias the author already understands is the
> easiest possible test — see `DESIGN_CRITIQUE.md` §5.

---

## The three-harm safety model → concrete mechanisms

Every module exists to defend against one of three harms. If a module cannot be
placed in this table, it does not belong here.

| Harm | Mechanism | File |
|---|---|---|
| (a) A wrong answer reaching a patient | Closed claim algebra; `INSUFFICIENT_EVIDENCE` default; fail-loud on assumption violation; no "action" output exists | `honesty/claims.py`, `honesty/evidence_object.py` |
| (b) A biased-but-plausible answer entrenching inequity | Phase-0 audit as a precondition; pulse-ox measurement-bias probe; empirical-null calibration; mandatory equity stratification that reports where evidence is *absent* | `audit/phase0.py`, `estimator/calibration.py`, `equity/stratify.py` |
| (c) Concentrating the power to declare truth | The engine cannot declare truth; human DAG-approval gate (stub); content-addressed provenance so findings are *verified*, not *trusted* | `stubs/dag_gate.py`, `provenance.py` |

---

## The six hard safety invariants, and how each is enforced

1. **Three-harm model** — the table above; it is the design-review criterion.
2. **Hypothesis-only** — the *only* output type is a `Claim` over a four-element
   `Stance` enum. No constructor accepts an assertive sentence; there is no
   recommendation or action surface anywhere in the code.
3. **Controlled vocabulary, enforced in code** — *primarily* by construction (the
   claim algebra), and *secondarily* by `honesty/vocabulary_guard.py`, which scans
   **every string** in the serialized object and raises on any of
   `true, effective, safe, proven, recommend, should, causes` (with inflections).
   Unit-tested, including a property test that any forbidden stem raises. During
   development this guard repeatedly caught the engine's *own* internal prose —
   that is the tripwire working.
4. **Fail-loud, not fail-silent** — insufficient data / violated assumptions
   produce an explicit insufficient-evidence result. Missing-not-at-random data is
   never silently imputed; missingness becomes first-class indicator variables.
5. **No restricted data** — hard guard in the loader; demo-only by default; no
   network access is ever attempted.
6. **Default to skepticism** — the evidence tier is decided by *pessimistic gates*
   (`honesty/evidence_object.py`): the final stance is the **weakest** across all
   gates, and the floor is `INSUFFICIENT_EVIDENCE`. A finding is promoted only if
   it clears every guardrail.

---

## What is BUILT vs STUBBED (read this before trusting anything)

**Built and tested end-to-end:**

- Phase-0 data audit: cohort representation, the flagship pulse-oximetry
  occult-hypoxemia probe by recorded race, differential-testing rates, MNAR
  characterization with first-class missingness indicators.
- Frozen, hash-committed protocol with a **pre-registration capability**: outcomes
  are unreadable until the protocol is sealed (`protocol/schema.py`).
- Cohort construction with **time-zero enforcement** (immortal-time bias excluded
  by construction).
- One estimator end-to-end: **stabilized IPTW** with covariate-balance (SMD)
  diagnostics and explicit missingness handling.
- **Negative-control empirical-null calibration** (Schuemie et al.) over a control
  panel — not merely a refutation test (see `DESIGN_CRITIQUE.md` §1.3).
- **dowhy refuters** as falsification probes (placebo, random common cause,
  subset).
- **E-value** (VanderWeele & Ding), exact closed form, for the estimate and the
  CI limit.
- **Equity-stratified** estimation classifying each group as evidence
  PRESENT / SILENT / ABSENT.
- A guarded **evidence object**, content-addressed **provenance ledger**, and
  **byte-reproducible** output.

**Stubbed (interfaces defined, `NotImplementedError`, listed in
[`ROADMAP.md`](ROADMAP.md)) — these are NOT complete:**

- Human DAG-approval gate (`stubs/dag_gate.py`)
- Multi-estimator concurrence check (`stubs/multi_estimator.py`)
- RCT-benchmark harness (`stubs/rct_benchmark.py`)
- Cross-dataset replication (`stubs/replication.py`)

---

## Architecture at a glance

```
config ─► data.loader ─►  Phase0 audit  ─► caveats ─┐
                              │                      ▼
        protocol.seal() ─► cohort.builder ─► IPTW ─► calibration ─► E-value
              │ (token)         │  outcomes        (neg-control panel)   │
              ▼                 │  via token                             ▼
        [stub] dag_gate         └────────► refutation, equity ─► EvidenceObject
                                                                  │
                                              vocabulary guard ◄──┘─► serialize
```

Each arrow is an immutable value object; each stage appends a content-addressed
artifact, so the final `artifact_root` transitively commits to the whole run.
See `DESIGN_CRITIQUE.md` §4 for why the seams are placed where they are.

---

## The honest next step

The bias lives **upstream** of this code, where the data were generated, and the
code cannot reach it. The pulse-ox probe can *detect* that SpO2 mis-measures
saturation by race; it cannot *repair* the variables downstream of biased
measurement. The right next move is not more code — it is taking these findings to
clinicians and to people from the populations the data describe, and letting them
say where the audit is wrong or incomplete. This engine is an input to a human
argument, never the end of one. Its highest aspiration is to be wrong *legibly*.
