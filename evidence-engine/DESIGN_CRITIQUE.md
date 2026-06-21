# Design Critique & First Principles

A genuinely critical evaluation of the evidence-engine specification, and the
reasoning behind the architecture that implements it. This document is adversarial
toward the spec on purpose: a system whose entire premise is *epistemic humility*
must be the harshest critic of its own design.

---

## 0. The thesis, stated precisely

The system makes one kind of statement and no other:

> Within a single, pre-registered research context *C*, the observational data
> *D* are **consistent with** an association between exposure *X* and outcome *Y*
> of magnitude *θ̂* (with uncertainty *U*), *after* the enumerated identifying
> assumptions *A* are granted — assumptions that *D* cannot itself verify. This
> is **hypothesis-generating** and **requires a confirmatory trial**.

Everything in the codebase exists to make any *stronger* statement than this
**unrepresentable**, not merely discouraged. That distinction — unrepresentable
vs. discouraged — is the spine of the design and the bar against which every
module is judged below.

---

## 1. Where a naive reading of the spec goes wrong

The spec is good, but four of its instructions, taken literally, produce a
**weaker** system than intended. A careful implementation must improve on them.

### 1.1 "Write a guard that scans output strings for forbidden words."

A blacklist is the *weakest* possible enforcement of a safety property. It is:

- **Evadable.** "not ineffective", "the data prove… nothing", "this is a safe bet"
  vs. clinical "safe" — string matching cannot distinguish sense from mention.
- **Brittle.** It produces false positives ("the assay is *effective* at 37°C")
  and false negatives in equal measure.
- **Misplaced in the pipeline.** It runs at *serialization* — the last possible
  moment — which means an unsafe claim can be *constructed, reasoned about, and
  passed around* internally and is caught only on the way out the door.

**The correct primary mechanism is constructive, not filtrative.** Outputs are
not free text that we later police; they are *rendered from a closed algebra of
sanctioned claim types* (`honesty/claims.py`). A `Claim` carries a `Stance` drawn
from a four-element enum and a set of *structured* referents; its natural-language
form is a **pure function** of those fields. There is no code path that
interpolates analyst-supplied prose into a claim. A forbidden assertion is not
"rejected" — it has no constructor.

The word-blacklist still exists (`honesty/vocabulary_guard.py`) but is demoted to
its proper role: a **defense-in-depth tripwire** over the *already-constructed*
output, catching the one residual risk the algebra cannot (a developer
hand-writing prose into a free-text caveat field). Belt, *and* suspenders, with
the suspenders load-bearing.

### 1.2 "Pre-register the protocol before outcomes are examined."

Stated as a *procedure*, this is unenforceable — nothing stops a developer from
peeking at `Y`, then writing the protocol to fit. A procedure that depends on
discipline is a procedure that fails under deadline pressure.

**The fix is to make peeking require a capability you can only obtain by
committing.** `Protocol.seal()` returns a `SealedProtocol` whose construction
*computes and freezes the protocol hash*, and only a `SealedProtocol` can mint the
`OutcomeAccessToken` that outcome-reading functions demand
(`cohort/builder.py`, `estimator/`). You cannot touch `Y` without first having
produced an immutable, hashed pre-registration of the analysis. The temporal
ordering — register, *then* look — is enforced by the dataflow, not by a comment.
This is the same trick capability-based security uses: unforgeable tokens replace
honor-system rules.

### 1.3 "Use dowhy refuters as the empirical-calibration analog."

Refutation tests (placebo treatment, random common cause, subset) are valuable
*falsification* probes, but they are **not** empirical calibration. Calibration —
the OHDSI/Schuemie contribution that is the actual state of the art — does
something the spec conflates away: it uses a *panel of negative controls whose
true effect is known to be null* to **estimate the distribution of the method's
systematic error**, then **recalibrates the p-value and confidence interval of
the real estimate** against that empirical null. A method that is biased by
1.3-fold on things that cannot be caused gets its real findings discounted by
that same systematic error.

This system implements **both**: dowhy refuters as falsification
(`estimator/refutation.py`) *and* a genuine empirical-null calibration from the
negative-control panel (`estimator/calibration.py`), following Schuemie et al.
(2014, *Stat. Med.*). Reporting a refuter's pass/fail without calibrating against
the empirical null would be the kind of "biased-but-plausible" answer that is
*Harm (b)* in the three-harm model. The spec's own threat model demands the
stronger machinery.

### 1.4 "Compute and attach an E-value."

Necessary, not sufficient, and easy to misuse. The E-value answers *one* narrow
question — how strong an unmeasured confounder would have to be to explain away
the point estimate (and, separately, the CI bound). It says nothing about
selection bias, measurement bias (the pulse-ox probe!), or model
misspecification. Implemented carelessly it becomes a single reassuring number
that *launders* a fragile estimate.

So the E-value here is (a) computed by the exact VanderWeele–Ding closed form for
both the estimate **and** the limit of the CI nearest the null — the CI E-value is
the one that actually matters — and (b) **never reported alone**: it is one field
in an evidence object that *also* carries the calibration result, the balance
diagnostics, the audit caveats, and the equity breakdown. The honesty object is
designed so that no single number can stand in for the whole.

---

## 2. The three-harm model, mapped to mechanisms

The spec names three harms. A design is only serious if every harm maps to a
*specific, testable* mechanism — otherwise the model is decoration.

| Harm | Mechanism in this codebase | Failure mode it prevents |
|---|---|---|
| **(a) A wrong answer reaches a patient** | Closed claim algebra + `Stance.INSUFFICIENT_EVIDENCE` as the *default*; fail-loud on assumption violation; no API surface that returns an "action". | A plausible-looking estimate being read as a treatment decision. |
| **(b) A biased-but-plausible answer entrenches inequity** | Phase-0 audit as a *precondition* (inference cannot run first); measurement-bias probe surfaced as a caveat on every result; empirical-null calibration; mandatory equity stratification that reports *where evidence is absent*, never extrapolating a population-average effect to an under-represented group. | A confidently-stated effect that only holds for the majority group, silently generalized. |
| **(c) Concentrating the power to declare truth** | The system *cannot* declare truth (claim algebra); the **human DAG-approval gate** (`protocol/dag_gate.py`) keeps causal-structure authority with domain experts — estimation is refused without a `DagApprovalCertificate` minted only when the graph passes structural checks AND a clinician + affected-population quorum signs it; provenance is a content-addressed chain (`provenance.py`) so any party can independently *verify* a finding rather than *trust* its author. | One actor's model becoming an unauditable oracle. |

The mapping is the design review: if a module cannot be placed in this table, it
does not belong in the system.

---

## 3. Language choice — and why *not* polyglot

The invitation to "deviate to any language" is itself a design question, and the
disciplined answer is **mostly no**, for reasons that are themselves the point.

- The epistemic core (claim algebra, the seal/token state machine, the
  content-addressed ledger) is exactly the kind of "make illegal states
  unrepresentable" problem where a language with sum types and a borrow checker —
  Rust, or an ML — would be *ideal*. I considered it seriously.
- But the *statistical* substrate that gives the system any value — `dowhy` for
  the causal graph and refuters, `lifelines` for time-to-event, `statsmodels`,
  the OHDSI empirical-calibration lineage — lives in Python and R. A second
  language at the core would buy stronger compile-time guarantees at the cost of
  an FFI seam running through the most safety-critical path. **A seam is a place
  bias hides.** For a system whose entire job is auditability, *fewer moving
  parts that a reviewer can hold in their head* beats *stronger types behind a
  boundary they cannot see across.*
- So the choice is Python, but operated as if it were a typed language:
  `from __future__ import annotations` everywhere, `Final`/`Literal`/`NewType`,
  exhaustively-matched `Enum`s, frozen dataclasses for every value object,
  capability tokens instead of honor-system ordering, `mypy --strict` clean, and
  **property-based tests** (`hypothesis`) that assert invariants over *generated*
  inputs rather than hand-picked examples. The genius move is not adopting a
  fashionable language; it is recognizing that *the reliability argument is made
  by the absence of seams*, and then enforcing rigor within that constraint.

The architecture is nonetheless kept **portable to the OHDSI/R stack**: the
analytic schema mirrors OMOP CDM concepts and the calibration step mirrors the
`EmpiricalCalibration` package, so the Python core is a faithful prototype of a
system that could later be backed by HADES without redesign.

---

## 4. Modularity & interoperability — the boundaries that matter

A module boundary is well-placed iff the two sides can be *reasoned about
independently* and *replaced independently*. The seams here are chosen so each
stub can be filled in later **without touching the core**:

```
config ─► data.loader ─►  Phase0 audit  ─► (caveats) ─┐
                              │                        ▼
        protocol.seal() ─► dag_gate ─► cohort.builder ─► estimator ─► honesty.EvidenceObject ─► guard ─► serialize
              │  (token)     (cert)       ▲   ▲            │  ▲           ▲
              ▼              required      │   │            │  │           │
        OutcomeAccessToken   to estimate ─┘   │   IPTW+AIPW concurrence   │
                                              │   [stub] full panel       │
              [stub] rct_benchmark ───────────┴── [stub] replication ─────┘
```

- Every arrow is a **value object** (frozen dataclass), never a mutable shared
  blob, so a stage's output is a hashable, content-addressable artifact.
- Each stub is defined by a `typing.Protocol` (structural interface) the core
  already calls; the stub raises `NotImplementedError` with a roadmap pointer.
  Filling it in is *implementing an interface that already has callers and
  tests*, the opposite of a refactor.
- The data loader is the only impurity (I/O, randomness); it is funnelled through
  one seam with a hard restricted-data guard, so the rest of the system is a pure
  function of `(SealedProtocol, tables, seed)`. Purity is what makes the
  byte-reproducibility guarantee *true by construction* rather than *tested and
  hoped for*.

---

## 5. Honest catalogue of what remains weak

A critique that finds no faults is flattery. The real limitations, ranked:

1. **The bias lives upstream of the code, and the code cannot reach it.** The
   pulse-ox probe can *detect* that SpO2 mis-measures saturation by race; it
   cannot *correct* the thousands of downstream variables silently conditioned on
   biased measurement and differential testing. The audit produces caveats, not
   repairs. The honest next step is not more code — it is taking these findings to
   clinicians and to people from the affected populations. The system is designed
   to make that conversation *legible*, not to substitute for it.
2. **Identification is assumed, never proven.** No-unmeasured-confounding,
   positivity, consistency, correct DAG — the data are mute on all of them. The
   E-value and calibration bound *some* violations; they cannot bound selection
   bias or a missing confounder nobody named. The **human DAG-approval gate** is
   the intended check and is now built: estimation is refused unless the causal
   graph is structurally valid AND a clinician + affected-population quorum has
   signed it. What code still cannot do is guarantee the *signed graph is correct* —
   that remains an irreducibly human judgement the gate makes explicit and
   auditable rather than silent.
3. **A five-estimator panel now triangulates.** IPTW (propensity-only), AIPW and
   TMLE (doubly robust), propensity matching, and g-computation (outcome-model
   only) are estimated under the same sealed protocol and DAG, and their
   concurrence is a live downgrade gate — an effect that survives all five methods
   is far harder to dismiss than one from any single one. The remaining refinement
   is to run concurrence on the *calibrated* intervals rather than the raw ones.
4. **The demo runs on a synthetic surrogate** when the open MIMIC-IV demo is
   absent (e.g. offline). The surrogate has *planted, known* biases so the
   machinery is demonstrable and reproducible — but a planted bias the author
   already understands is the easiest possible test. Real data will be messier in
   ways the author did not anticipate; that is the point of point 1.

If you remember one thing: **this engine's output is an input to a human
argument, never the end of one.** Its highest aspiration is to be wrong *legibly*
— to fail loud, show its assumptions, and make disagreement cheap.
