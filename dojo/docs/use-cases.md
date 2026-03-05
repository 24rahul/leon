# Dojo: Example Use Cases

*Three concrete scenarios showing how Dojo works in practice — from industry, community, and health system perspectives.*

---

## Use Case 1: Industry — Hospital Deploys a Sepsis Prediction Model

### Scenario
A health system purchases a commercial sepsis prediction model. Before deployment, they submit it to Dojo for evaluation and improvement.

### Dojo Flow

**Step 1: Submission**
The hospital submits the model along with:
- A sample of their local patient data (de-identified)
- Deployment context: ICU, used by nurses for early warning
- Target population demographics

**Step 2: Evaluation Arena**

| Agent | Finding |
|-------|---------|
| Shortcut Detective | Model relies heavily on nursing documentation frequency as a predictor. This is a shortcut — documentation frequency correlates with staffing ratios, not sepsis. Night-shift patients get fewer notes → model under-predicts sepsis at night. |
| Care Phenotype Agent | Generates care phenotypes based on monitoring frequency (vitals checks, lab orders) adjusted for illness severity. Reveals that patients in the "low-monitoring" phenotype have 23% higher false-negative rate — invisible when auditing by race/gender alone. |
| Environmental Impact Agent | Model requires real-time inference on all ICU patients. At this hospital's scale: estimated 2.3 tons CO2/year for inference alone. Recommends batch inference with trigger-based real-time fallback. |
| Persuasion Analysis Agent | Model's alert interface uses high-confidence language ("Patient WILL develop sepsis") even at 60% probability. Nurses in pilot reported feeling unable to override alerts — persuasion risk is high. |

**Step 3: Training Gymnasium**
- Dojo recommends retraining with documentation frequency excluded; provides a data augmentation strategy
- Connects hospital team with a community member who solved a similar shortcut problem in a different EHR system
- Suggests alert UI redesign: probabilistic language + nurse override logging

**Step 4: Re-evaluation**
Hospital retrains and resubmits. Shortcut reduced, care phenotype performance gap narrowed from 23% to 7%.

---

## Use Case 2: Community — Patient Advocacy Group Tests a Symptom Checker

### Scenario
A patient advocacy group for chronic pain patients is concerned that AI symptom checkers systematically underweight pain reports from women and people of color. They bring a popular symptom checker API to Dojo.

### Dojo Flow

**Step 1: Submission**
The advocacy group submits:
- API access to the symptom checker
- A curated set of 200 clinical vignettes (identical symptoms, varied demographic framing)
- Their hypothesis: demographic framing changes triage recommendations

**Step 2: Evaluation Arena**

| Agent | Finding |
|-------|---------|
| Care Phenotype Agent | Not applicable (no longitudinal care data) — agent correctly identifies it cannot contribute and abstains |
| Shortcut Detective | Identifies that when vignettes mention "history of anxiety" (more common in female-framed vignettes), triage severity drops by 1.4 levels on average |
| Contextual Modeling Agent | Tests the symptom checker across 5 deployment contexts (ED, primary care, rural clinic, telehealth, self-service). Performance varies dramatically — ED-optimized, fails in primary care context |
| Value Reflection Agent | Facilitates a session with the advocacy group: What values should a symptom checker embody? Group identifies "epistemic justice" — taking patients' reports seriously regardless of demographics — as their primary value |

**Step 3: Training Gymnasium**
- Dojo provides the symptom checker developers with the bias audit results
- Connects them with the advocacy group for direct conversation (co-design, not consultation)
- Offers a debiased vignette dataset for retraining
- Recommends context-specific deployment guidelines

**Step 4: Impact**
The advocacy group publishes the Dojo Report Card publicly. The symptom checker company engages with remediation. Other advocacy groups learn they can bring their concerns to Dojo too.

---

## Use Case 3: Health System — Academic Lab Builds a Chest X-Ray Classifier

### Scenario
A research lab at a mid-tier university (not Harvard, not Stanford) builds a chest X-ray classifier for pneumonia detection. They want it to be competitive with models from elite institutions but don't have the same resources or connections.

### Dojo Flow

**Step 1: Submission**
The lab submits:
- Their model + training details
- Two public datasets they trained on
- Their deployment goal: rural hospitals in their state

**Step 2: Evaluation Arena**

| Agent | Finding |
|-------|---------|
| Shortcut Detective | Model has learned to associate chest tube presence with positive pneumonia — a known shortcut. The lab didn't know this was a documented failure mode. |
| Environmental Impact Agent | Training used 340 GPU-hours. Comparable to top models. No efficiency concern. |
| Provenance Tracker | Identifies that one training dataset has known label quality issues (15% estimated label noise in lateral views). Recommends excluding lateral views or using label-cleaning techniques. |
| AI Report Card Generator | Using the Six Tools — Podium: Whose voice does this model amplify? It amplifies radiologist interpretations from urban academic centers. Rural deployment means it may encounter imaging equipment and patient populations it's never seen. |

**Step 3: Training Gymnasium**
- Dojo provides the lab with a chest tube segmentation mask to remove the shortcut
- Connects them with another lab that solved label noise issues on the same dataset
- Shares a data augmentation pipeline for equipment variation
- A community mentor (experienced researcher) offers to review their revised approach
- Provides access to shared compute for retraining

**Step 4: Outcome**
The lab retrains, removes shortcuts, and achieves performance competitive with top institutions. Their model is actually better suited for rural deployment because of the targeted improvements. Dojo helped level the playing field — not by lowering standards, but by sharing the knowledge that elite institutions hoard.

---

## What These Use Cases Demonstrate

1. **Beyond evaluation**: In every case, Dojo doesn't just identify problems — it provides concrete paths to improvement
2. **Agent composability**: Different use cases activate different agents; agents that can't contribute abstain transparently
3. **Community as infrastructure**: The connections, mentorship, and shared resources are as valuable as the technical tools
4. **Democratization**: Use Case 3 shows how Dojo breaks the expertise monopoly
5. **Stakeholder co-design**: Use Case 2 shows patients as co-designers, not subjects
6. **Context matters**: Models fail differently in different contexts — Dojo surfaces this
