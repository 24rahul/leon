# Dojo: Example Use Cases

*Three scenarios showing how Dojo works — including what goes wrong. Scoped to Phase 1 agents (Shortcut Detective + Care Phenotype Agent) with coaching layer.*

---

## Use Case 1: Industry — Hospital Evaluates a Sepsis Prediction Model Before Deployment

### Scenario
A large health system (800-bed hospital, 80-bed ICU) purchases a commercial sepsis prediction model. Before deployment, the chief medical informatics officer submits it to Dojo. The vendor is not involved — this is the hospital's own diligence.

### What the Hospital Submits
- Model as a Docker container with standardized inference API
- 6 months of de-identified ICU data (N=4,200 admissions) under a signed DUA
- Deployment context: ICU, real-time alerts to bedside nurses
- Known limitation (self-reported): "Trained primarily on academic medical center data"

### Evaluation Results

**Shortcut Detective finds:**
- The model uses nursing documentation frequency as a top-5 feature. Documentation frequency correlates with nurse staffing ratios (r=0.71), not sepsis. Night-shift patients (lower staffing) get fewer notes, so the model systematically under-predicts sepsis between 11 PM and 7 AM.
- Confidence: High — confirmed via feature masking (AUC drops 0.04 when documentation frequency is removed, but false-negative rate at night drops by 31%)
- The model also uses "number of blood cultures ordered" — which is both a legitimate clinical signal AND a shortcut (clinicians order more cultures for patients they already suspect have sepsis). Agent flags this as "ambiguous — clinical review recommended."

**Care Phenotype Agent finds:**
- Generates 4 care phenotypes based on monitoring frequency (vitals checks, lab orders, repositioning) adjusted for APACHE-IV:
  - Phenotype A: High-monitoring (matches severity)
  - Phenotype B: High-monitoring (exceeds severity — likely anxiety-driven overmonitoring)
  - Phenotype C: Standard monitoring
  - Phenotype D: Low-monitoring (below what severity warrants)
- Model performance by demographics: AUC 0.84 (White), 0.83 (Black), 0.82 (Hispanic) — looks fair
- Model performance by care phenotype: AUC 0.86 (A), 0.87 (B), 0.83 (C), 0.71 (D) — Phenotype D has a 15-point gap
- Phenotype D is disproportionately patients admitted on weekends and holidays (lower staffing)
- **This disparity is invisible when auditing by race/sex alone**

### Coaching Response

**Automated remediation plan:**
1. Remove documentation frequency from features → provides retraining recipe
2. For "blood cultures ordered" — recommends clinical review panel to decide whether to keep, remove, or transform this feature
3. Recommends temporal validation: test model performance by time-of-day and day-of-week separately

**Resource library surfaces:**
- A published data augmentation strategy for staffing-correlated shortcuts (from a similar model, different hospital)
- A fairness-constrained training recipe that penalizes phenotype-level performance gaps

**Expert match:**
- Connects the CMIO with a researcher at a different health system who solved a similar documentation-frequency shortcut in a readmission model
- Structured consultation template sent; 90-minute session scheduled

### What Goes Wrong

1. **The vendor refuses to help.** The hospital has the model but not the training code. Retraining means building a new model from scratch using the remediation guidance, not patching the existing one. Dojo's coaching helps but can't replace the vendor relationship. **Lesson: Dojo works best when the model developer is the submitter or is engaged.**

2. **The clinical review panel disagrees.** Two intensivists say "blood cultures ordered" is a legitimate feature; one says it's a shortcut. No consensus. Dojo documents the disagreement and recommends a prospective pilot comparing model versions with and without the feature. **Lesson: Not everything resolves cleanly. Documenting disagreement is itself a useful output.**

3. **Re-evaluation shows partial improvement.** After retraining without documentation frequency, the Phenotype D gap narrows from 15 points to 9 points — better, but not eliminated. The remaining gap appears to be driven by factors Dojo hasn't identified yet. **Lesson: Dojo improves models iteratively, not magically. Some problems take multiple cycles.**

---

## Use Case 2: Community — Patient Advocacy Group Audits a Symptom Checker

### Scenario
A patient advocacy group for chronic pain patients suspects that AI symptom checkers systematically downgrade pain severity reports from women. They want evidence, not anecdotes.

### What They Submit
- API endpoint for a popular consumer symptom checker
- 200 clinical vignettes they created: identical symptoms, varied only by gender framing (he/she/they) and presence/absence of "history of anxiety"
- Deployment context: self-service consumer use, no clinician in the loop
- No clinical dataset (they don't have one)

### Evaluation Results

**Shortcut Detective finds:**
- When vignettes include "history of anxiety," triage severity drops by 1.4 levels on average (on a 5-point scale)
- This effect is 2.1x stronger for female-framed vignettes than male-framed
- Confidence: High — consistent across symptom types (chest pain, abdominal pain, headache)
- Agent notes limitation: "This is an API-only submission. Without gradient access, I cannot confirm the causal mechanism — only the behavioral pattern."

**Care Phenotype Agent:**
- **Correctly abstains.** No longitudinal care data available. Agent reports: "Care phenotype analysis requires structured EHR data with treatment process variables. This submission contains vignettes only. I cannot contribute to this evaluation."
- This is important: agents that can't help should say so, not generate spurious findings.

### Coaching Response

**Automated remediation plan:**
- Dojo cannot retrain the symptom checker (it's a third-party API)
- Instead, generates a structured bias report suitable for:
  - Sharing with the symptom checker company
  - Publishing as an independent audit
  - Submitting to regulators
- Report includes methodology, statistical tests, confidence intervals, and limitations

**Expert match:**
- Connects the advocacy group with a health equity researcher who has published on diagnostic bias in AI systems
- Structured consultation: help the group write up findings for peer review

### What Goes Wrong

1. **The vignettes have methodological problems.** An expert reviewer points out that the "history of anxiety" framing varies systematically with other vignette features — it's not a clean experimental design. Some findings may be confounded. Dojo flags this in the report with a confidence downgrade. **Lesson: Dojo can evaluate what's submitted, but can't fix upstream methodology problems. It can flag them.**

2. **The symptom checker company ignores the report.** They have no obligation to engage. The advocacy group publishes the report anyway, which generates media attention, which eventually forces engagement. **Lesson: Dojo provides the evidence. Social and political dynamics determine what happens with it.**

3. **Other advocacy groups start submitting poorly designed audits.** The success of this use case attracts groups that submit biased or leading vignettes designed to confirm their priors, not discover truth. Dojo's agents detect some of this (e.g., Shortcut Detective flags vignettes that differ in more ways than the stated variable), but not all. **Lesson: Dojo needs a submission quality check — not gatekeeping, but flagging methodological concerns before evaluation runs.**

---

## Use Case 3: Academic — Under-Resourced Lab Improves a Chest X-Ray Classifier

### Scenario
A 3-person ML lab at a mid-tier state university builds a pneumonia detection model on CheXpert. They want to deploy it in rural hospitals in their state, but they've never done a fairness audit and don't know how to check for shortcuts. They heard about Dojo from the recorded grant-writing sessions.

### What They Submit
- Model weights + inference script (PyTorch)
- CheXpert as training data (public, no DUA needed)
- A small local dataset (N=800) from a partner rural hospital (de-identified, DUA signed)
- Deployment context: rural community hospitals, read by general practitioners (not radiologists)
- Self-reported limitations: "We know CheXpert has label noise but we're not sure how to address it"

### Evaluation Results

**Shortcut Detective finds:**
- Model strongly associates chest tube presence with positive pneumonia classification (known shortcut, Degrave et al. 2021)
- The lab had no idea this was a documented failure mode
- Confidence: High — counterfactual generation (chest tube removal via inpainting) confirms causal relationship
- Also finds a subtler shortcut: model uses lateral chest X-ray orientation markers that differ between CheXpert (academic) and the rural hospital dataset (different equipment)

**Care Phenotype Agent finds:**
- On the rural hospital dataset (N=800): generates 3 care phenotypes based on follow-up imaging frequency and time-to-radiologist-read
- Phenotype R1: Patients whose X-rays were read by a radiologist within 24 hours
- Phenotype R2: Patients whose X-rays were read by a GP, radiologist review >48 hours later
- Phenotype R3: Patients with no radiologist review (GP read only)
- Model performance: AUC 0.82 (R1), 0.79 (R2), 0.68 (R3)
- **The model performs worst for the exact patients it would serve most in rural deployment** — those without radiologist backup
- Demographics show no significant difference (AUC 0.78-0.80 across race/sex)
- **Again: care phenotypes reveal what demographics hide**

### Coaching Response

**Automated remediation plan:**
1. Chest tube shortcut: apply segmentation mask during training — tool provided from resource library
2. Equipment marker shortcut: apply imaging preprocessing normalization — pipeline provided
3. CheXpert label noise: apply confident learning (Northcutt et al.) — recipe provided with code template
4. Phenotype R3 performance gap: likely driven by distribution shift between CheXpert training data and rural imaging. Recommends fine-tuning on the rural dataset with active learning to prioritize ambiguous cases.

**Resource library surfaces:**
- Chest tube segmentation model (contributed by a previous Dojo user who solved the same problem)
- CheXpert label-cleaning pipeline (with before/after performance metrics)
- A tutorial on domain adaptation for medical imaging (written by a community contributor)

**Expert match:**
- Connects the lab with a senior researcher who has deployed imaging models in resource-limited settings
- Structured consultation: deployment strategy for GP-read-only environments

### What Goes Wrong

1. **The lab doesn't have enough compute to retrain.** Remediation plans are great, but they require GPU access the lab doesn't have. Dojo's resource library includes some shared compute credits (donated by industry partners), but the queue is long. The lab waits 3 weeks. **Lesson: Democratization requires resources, not just knowledge. Dojo needs a compute access strategy — partnerships, cloud credits, efficient training recipes.**

2. **The rural dataset is too small for reliable care phenotype analysis.** N=800 produces phenotype clusters, but the Care Phenotype Agent flags low confidence: "Cluster stability is poor (bootstrap stability <0.6). Findings are suggestive, not conclusive. Recommend larger dataset for definitive analysis." The lab presents the findings as preliminary. **Lesson: Agents must communicate uncertainty honestly. Small-N settings need different statistical approaches.**

3. **After retraining, the chest tube shortcut is reduced but a new shortcut emerges.** The model now relies on image brightness (which correlates with equipment manufacturer). Fixing one shortcut doesn't guarantee others won't appear. The lab submits again, Dojo catches the new shortcut, and the cycle continues. **Lesson: Shortcut detection is adversarial and iterative. Single-pass evaluation is insufficient. This actually validates the re-evaluation loop.**

4. **The GP deployment faces resistance.** Even with improved model, GPs at the rural hospital are uncomfortable using AI for radiology reads. They don't trust the model and don't understand the Dojo Report Card. **Lesson: Dojo addresses technical model quality but cannot solve adoption and trust challenges alone. This needs to be stated as a scope limitation.**

---

## What These Use Cases Demonstrate

### Strengths
1. **Care phenotypes work.** In every applicable case, they reveal disparities invisible to demographic auditing. This is the core scientific contribution.
2. **Coaching closes the loop.** Evaluation without remediation is useless. Automated plans + resource library + expert matching provide concrete next steps.
3. **Honest agents.** Care Phenotype Agent abstains when it can't contribute (Use Case 2). Shortcut Detective reports ambiguity (Use Case 1). Confidence levels are explicit. This is critical for trust.

### Limitations We're Honest About
1. **Dojo can't fix what it doesn't control.** Third-party models, vendor relationships, deployment politics, clinician trust — all outside Dojo's scope.
2. **Methodology in, methodology out.** Bad vignettes produce questionable results. Dojo can flag this but can't fix it automatically.
3. **Small data is hard.** Care phenotype analysis needs sufficient sample size. Rural and under-resourced settings often have small datasets.
4. **One fix can create new problems.** Shortcut removal is iterative. The re-evaluation loop isn't a nice-to-have — it's essential.
5. **Compute access is a bottleneck.** Knowledge democratization without resource democratization is incomplete.
6. **Trust and adoption are human problems.** Dojo makes models better; it doesn't make stakeholders trust them.
