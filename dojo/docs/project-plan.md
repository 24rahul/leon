# Dojo Project Plan

## 1. What We're Building

Dojo is a **community gym for health AI** — a platform where AI models, agents, and humans red-team, stress-test, and train each other. It goes beyond evaluation: after identifying weaknesses, Dojo provides the tools, data, and community support to actually improve.

The metaphor is literal: a gym has machines (evaluation tools), weights (training resources), coaches (agents + humans), and members (the community). Everyone who enters gets stronger.

---

## 2. Problem Statement

Current AI evaluation is:
- **One-shot**: You submit, you get a score, you leave
- **Decontextualized**: Models are tested in isolation from their deployment context
- **Demographically naive**: Uses race/ethnicity labels that are social constructs and imperfectly collected, giving false confidence about fairness
- **Siloed**: Evaluation tools don't talk to each other
- **Gatekept**: Only elite institutions have the expertise to build and evaluate well
- **Environmentally blind**: No systematic accounting of computational and environmental costs

---

## 3. Core Design Principles

### 3.1 LTARC Framework
- **L**ocal: Evaluations are contextualized to deployment settings
- **T**ask-specific: No one-size-fits-all benchmarks
- **A**gile: Adapts as models and contexts evolve
- **R**eflexive: The evaluation system evaluates itself
- **C**ommunity-powered: Governed by and for the community

### 3.2 Value Sensitive Design
Embed stakeholder values (patients, clinicians, communities, researchers) from the design phase — not as an afterthought. Concretely:
- Identify direct, indirect, and excluded stakeholders
- Surface value tensions explicitly (e.g., accuracy vs. equity vs. sustainability)
- Make value trade-offs transparent and community-governed

### 3.3 AI Plasticity
The community grows through collectively experiencing and learning from AI failures. The process itself is the product — not just the output.

---

## 4. Agent Ecosystem

Each agent is a "machine" or "weight" in the dojo gym. They are modular, composable, and independently validatable.

### 4.1 Flagship Agents (Phase 1)

#### Shortcut Detective Agent
- **Purpose**: Identify whether medical computer vision models use features unrelated to disease (e.g., race markers, imaging artifacts) for classification
- **Input**: Model + dataset + task description
- **Output**: Shortcut report with identified spurious correlations, affected subgroups, and remediation suggestions
- **Status**: Existing tool — needs agent wrapper and API

#### Care Phenotype Agent
- **Purpose**: Generate care phenotypes — subgroups defined by treatment patterns rather than demographic labels — as alternative fairness audit categories
- **Input**: Clinical dataset with treatment variables + illness severity measures
- **Output**: Care phenotype clusters, fairness audit using phenotypes vs. demographics, comparison of bias visibility
- **Insight**: Demographic labels can mask algorithmic bias; care phenotypes (e.g., frequency of turning/monitoring adjusted for severity) reveal hidden disparities
- **Status**: Paper in review — needs productionization

#### Environmental Impact Agent
- **Purpose**: Calculate and report the full environmental footprint of an AI model's lifecycle
- **Scope**: Not just carbon/compute — includes hardware sourcing, water usage, energy sources, e-waste, supply chain ethics
- **Input**: Model architecture, training logs, infrastructure specs
- **Output**: Environmental report card with actionable reduction recommendations
- **Status**: New development — Rawan's domain

#### Value Reflection Agent
- **Purpose**: Guide teams through structured value reflection before, during, and after model development
- **Input**: Project description, team composition, deployment context
- **Output**: Values audit report, tension map, recommended governance structures
- **Approach**: Non-technical agent — focuses on process, not code
- **Status**: New development — draws on Value Sensitive Design literature

### 4.2 Phase 2 Agents

#### AI Report Card Generator
- **Purpose**: Comprehensive societal impact assessment
- **Dimensions**: Environmental impact, job displacement, entry-level opportunity erosion, healthcare access effects, economic concentration
- **Uses the Six Tools framework**:
  - Mirror: What does this model reflect about us?
  - Flashlight: What does it illuminate that we couldn't see?
  - Microscope: What details does it reveal under scrutiny?
  - Paintbrush: What narrative does it paint?
  - Podium: Whose voice does it amplify?
  - Slingshot: What power dynamics does it disrupt?

#### Contextual Modeling Agent
- **Purpose**: Assess context rot — how well a model adapts to contextual variation in real-world deployment
- **Key insight**: Models cannot simulate all deployment contexts (unlike board games). Beyond a threshold, contextual modeling requires human input — but from "evolved" humans with new AI-era agency
- **Input**: Model + deployment scenario descriptions
- **Output**: Context sensitivity analysis, failure mode catalog, human oversight recommendations

#### Persuasion Analysis Agent
- **Purpose**: Evaluate the believability and persuasive capacity of model outputs — and identify who is most susceptible
- **Motivation**: The Mt. Sinai/Nature study showed ChatGPT triaging is poor, but accuracy alone misses the dimension of how convincingly wrong answers are presented
- **Input**: Model outputs + task context
- **Output**: Persuasion risk assessment, vulnerable population analysis

#### Provenance Tracker Agent
- **Purpose**: Track the full research provenance trail from data collection through model deployment
- **Design for agentic research workflows**: Integrates at the beginning of research, not just at final model submission
- **Input**: Research workflow logs, agent interaction traces
- **Output**: Complete provenance graph, decision audit trail

---

## 5. Platform Architecture

### 5.1 Technical Stack (Proposed)

```
Frontend:        Web dashboard for submission, results, community
Backend API:     FastAPI (Python) — orchestrates agent execution
Agent Runtime:   LangGraph or similar agent orchestration framework
Data Layer:      PostgreSQL + object storage for models/datasets
Auth:            OAuth2 with institutional and individual accounts
Deployment:      Containerized (Docker/K8s), cloud-agnostic
```

### 5.2 Submission Flow

```
1. User submits model/agent/dataset via portal
   ├── Metadata: task, deployment context, target population
   ├── Model artifacts or API endpoint
   └── Opt-in: which evaluations to run

2. Evaluation Arena runs selected agents
   ├── Shortcut Detective → shortcut report
   ├── Care Phenotype Agent → fairness audit
   ├── Environmental Impact → footprint report
   ├── Persuasion Analysis → risk assessment
   └── ... (composable, user-selected)

3. Results aggregated into Dojo Report Card
   ├── Strengths identified
   ├── Weaknesses identified
   └── Actionable improvement paths

4. Training Gymnasium activated
   ├── Recommended fine-tuning strategies
   ├── Debiased training data offered
   ├── Community mentorship matched
   └── Tool access granted (compute, weights, frameworks)

5. Re-evaluation cycle
   └── Improved model re-enters the arena
```

### 5.3 Agent Validation

Every agent in the gym must itself be validated. Mechanisms:
- **Cross-validation**: Agents evaluate each other
- **Community review**: Humans audit agent outputs
- **Adversarial testing**: Deliberately adversarial submissions to test agent robustness
- **Version tracking**: All agent versions and outputs are logged
- **Reflexive reporting**: Each agent reports its own confidence and limitations

---

## 6. Community Governance

### 6.1 Guiding Principles (Draft — Open to Disruption)

1. **No single institution owns Dojo** — governance belongs to the community
2. **Participants are co-workers, not guests of honor** — patient advocates, community organizations, and Global South researchers have equal standing, not tokenistic representation
3. **The governance itself is a living document** — it evolves as the community evolves
4. **Transparency over polish** — we show the chaos, not just the results
5. **Ideas welcome from everyone** — don't just ask for comments on our ideas; create space for others' ideas
6. **Values before solutions** — reflect on what values drive our work before building

### 6.2 Governance Structure (Initial Proposal)

```
Community Assembly (all participants)
    │
    ├── Values Council
    │   └── Maintains values charter, resolves value tensions
    │
    ├── Technical Steering Committee
    │   └── Agent review, platform architecture, standards
    │
    ├── Community Partnerships
    │   └── Patient advocacy, indigenous communities, Global South orgs
    │
    └── Environmental & Ethics Board
        └── Sustainability oversight, societal impact assessment
```

### 6.3 Stakeholder Inclusion

- **Patient advocacy groups** (Kathy, Hector, others) — as co-designers, not reviewers
- **Community organizations** — for governance co-design
- **Indigenous communities** — pluralism perspectives, tradition preservation
- **Global South researchers** — equal footing in innovation
- **Industry partners** — Google Health (Andrew Seligan / MedGemma), others
- **Hugging Face** — potential integration for model/data sharing infrastructure

---

## 7. Relationship to Existing Work

### 7.1 What We Already Have
- Shortcut detection software (medical computer vision)
- Care phenotypes methodology (paper in review)
- Mortality prediction model with bias analysis across care phenotypes
- LTARC evaluation framework (paper forthcoming)
- AI Report Card framework (six tools)
- AI Plasticity concept (submitted to BMJ)
- Mandate for Healing (Project 2025 for healthcare)

### 7.2 What Hugging Face Has
- Model hub, dataset hub — infrastructure for sharing
- Community around model evaluation
- **Gap**: Not deeply connected as a community; not investing in mutual improvement
- **Dojo adds**: The coaching/training loop, community governance, value-centered evaluation

---

## 8. Grant Strategy

### 8.1 NIH Proposal (Primary — Target: End of May 2026)
- **Framing**: Prototype + evaluate Dojo as community infrastructure for health AI
- **Key sections**:
  - Specific aims: Describe Dojo, prototype 4 flagship agents, validate with diverse community
  - Innovation: Beyond evaluation → coaching; care phenotypes over demographics; community governance
  - Approach: Phase 1 build, Phase 2 pilot at MIT course, Phase 3 scale
  - Governance: Draft community charter (explicitly stating it's open to disruption)
- **Reusable**: Grant designed to be repurposed by any PI for any funder

### 8.2 Industry-Academia Partnership Grant (Secondary)
- Multi-model discordance project with Google Health (Andrew Seligan / MedGemini team)
- To be developed in parallel over next few months

### 8.3 Grant Writing as Masterclass
- Record the grant-writing process as a video series
- Show the chaos, not just the polished output
- Goal: Democratize grant-writing expertise beyond elite universities
- Channel: "Masterclass" (name TBD — dropping "master" per Leo's note)

---

## 9. Roadmap

### Phase 0: Foundation (Now — April 2026)
- [ ] Finalize values charter with community input
- [ ] Draft governance principles document
- [ ] Write specific aims page (version 3 incorporating March 3 meeting ideas)
- [ ] Define 3 concrete use cases (industry, community, health system)
- [ ] Recruit patient advocacy partners as co-designers
- [ ] Begin grant writing work sessions (recorded for video series)
- [ ] Explore Value Sensitive Design framework (Susannah's citations)

### Phase 1: Core Build (May — August 2026)
- [ ] Platform backend: submission portal + evaluation orchestration
- [ ] Shortcut Detective Agent (productionize existing tool)
- [ ] Care Phenotype Agent (productionize from paper)
- [ ] Environmental Impact Agent (new build)
- [ ] Value Reflection Agent (new build)
- [ ] Agent validation framework
- [ ] Community dashboard (results visualization)

### Phase 2: Pilot (September — December 2026)
- [ ] Premiere at MIT fall course
- [ ] Onboard first external community members
- [ ] Run pilot evaluations with 3 use cases
- [ ] Iterate governance based on community feedback
- [ ] Build Phase 2 agents (Report Card, Contextual Modeling, Persuasion, Provenance)
- [ ] Hugging Face integration exploration

### Phase 3: Scale (2027)
- [ ] Open platform to broader community
- [ ] International partnerships (Global South institutions)
- [ ] Agent marketplace — community-contributed agents
- [ ] Continuous governance evolution
- [ ] 2-year scenario planning (what does the landscape look like in 2028?)

---

## 10. Two-Year Scenarios (per Hannes)

### Scenario A: Agentic Research is the Norm
By 2028, autonomous research agents handle most of the clinical AI research lifecycle. Dojo must be designed as an **environment that research agents operate within** — not a tool humans manually invoke. Dojo agents (bias detection, environmental tracking, etc.) run alongside research agents, providing continuous oversight and course correction throughout the research process.

### Scenario B: Regulation Catches Up
Health AI faces significant new regulation. Dojo becomes the **compliance infrastructure** — providing auditable provenance trails, standardized fairness assessments, and environmental impact reports that regulators require.

### Scenario C: Community-Driven Innovation Succeeds
Dojo's model of community governance and democratized expertise takes hold. Institutions beyond elite universities are producing competitive health AI, using Dojo's tools and community for support. The gym metaphor works — everyone who participates gets stronger.

**Strategy**: Build for Scenario A (most technically demanding), design governance for Scenario C (most ambitious), prepare documentation for Scenario B (most likely to attract funding).

---

## 11. Open Questions

1. **Centralized vs. distributed agent architecture?** (Rahul's tension) — Start structured, evolve toward distributed as trust builds
2. **How do we validate the validators?** Agents evaluating agents risks infinite regress (Harry's point) — humans must remain in the loop, but what kind of humans with what capabilities?
3. **Pluralism**: How do indigenous perspectives on pluralism reshape our approach? Western pluralism may not be the only valid frame
4. **Language of the grant**: Avoid "evolved humans" (Harry's advice); frame as "enhanced human-AI collaboration capabilities"
5. **Sustainability of the community**: How do we avoid this becoming another platform that launches with energy and fades?

---

## 12. Action Items from March 3 Meeting

| Action | Owner | Status |
|--------|-------|--------|
| Draft governance principles | Group | Pending |
| Draft values/incentives document | Group (Rawan raised) | Pending |
| Draft practical outcomes / example use cases | Group (Susannah raised) | Pending |
| Send Value Sensitive Design citations | Susannah → Leo | Pending |
| Draft 2-year scenarios + roadmap | Group (Hannes raised) | Done (in this doc) |
| Schedule grant-writing work sessions | Leo | Pending |
| Share meeting recording | Leo | Pending |
| Reach out to Hugging Face | Leo | Pending |
| Connect with patient advocacy groups (Kathy, Hector) | Leo | Ongoing |
| Polished specific aims page (v3) | Leo + Claude | Pending |
