# Dojo: A Community Gym for Health AI

**A community of agents, models, and humans — stress-testing, red-teaming, and training each other to build better, fairer health AI.**

Dojo is not just an evaluation platform. It's a gym where AI models, autonomous agents, and humans come together to identify weaknesses, share tools, and collectively improve. Think of it as a dojo where every participant — whether a clinical decision support model, a bias detection agent, or a domain expert — gets coached, challenged, and made stronger.

---

## Why Dojo?

The current AI evaluation landscape is fragmented and one-directional: you submit a model, it gets scored, and you're done. Dojo flips this by:

1. **Going beyond evaluation** — We don't just score; we coach. After identifying weaknesses, Dojo provides tools, training data, and community support to improve.
2. **Community governance** — Not dictated by MIT, Google, or any single institution. Designed by the community, for the community.
3. **Centering values** — Using frameworks like Value Sensitive Design and LTARC to ensure the process itself embodies equity, sustainability, and inclusivity.
4. **Addressing the full lifecycle** — From data collection to model deployment to environmental impact to societal consequences.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    DOJO PLATFORM                        │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  SUBMISSION  │  │  EVALUATION  │  │   TRAINING    │  │
│  │   PORTAL     │→│   ARENA      │→│   GYMNASIUM   │  │
│  │             │  │              │  │               │  │
│  │ Models      │  │ Red-teaming  │  │ Coaching      │  │
│  │ Agents      │  │ Stress tests │  │ Fine-tuning   │  │
│  │ Datasets    │  │ Bias audits  │  │ Data sharing  │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              AGENT ECOSYSTEM                      │   │
│  │                                                    │   │
│  │  Shortcut    Care        Environmental   Value     │   │
│  │  Detective   Phenotype   Impact          Reflection│   │
│  │  Agent       Agent       Agent           Agent     │   │
│  │                                                    │   │
│  │  Contextual  Persuasion  Report Card     Provenance│   │
│  │  Modeling    Analysis    Generator       Tracker   │   │
│  │  Agent       Agent       Agent           Agent     │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │           COMMUNITY GOVERNANCE LAYER              │   │
│  │  Values Charter │ LTARC Principles │ Six Tools    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Submission Portal
Where external teams bring their models, agents, and datasets for evaluation and improvement.

### 2. Evaluation Arena
Red-teaming and stress-testing using the agent ecosystem — checking for bias, shortcuts, environmental cost, persuasion risks, and contextual failures.

### 3. Training Gymnasium
The differentiator. After evaluation, Dojo provides actionable coaching: fine-tuning guidance, debiased training data, community mentorship, and tool access.

### 4. Agent Ecosystem
Modular, composable agents that each handle a specific dimension of evaluation and training. See `agents/` for details.

### 5. Community Governance Layer
Principles, values, and processes that guide how Dojo operates — designed to be disrupted and evolved by the community itself.

---

## Quick Start

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to get involved.

See [docs/project-plan.md](./docs/project-plan.md) for the full project plan and roadmap.

---

## Key Frameworks

- **LTARC**: Local, Task-specific, Agile, Reflexive, Community-powered evaluation
- **Value Sensitive Design**: Centering stakeholder values from the beginning
- **Six Tools**: Mirror, Flashlight, Microscope, Paintbrush, Podium, Slingshot
- **AI Plasticity**: Growing through the collective experience of AI failures

---

## Timeline

| Phase | Target | Focus |
|-------|--------|-------|
| Phase 0 | Now - April 2026 | Project planning, grant writing, values charter |
| Phase 1 | May - Aug 2026 | Core platform + 4 flagship agents |
| Phase 2 | Sep - Dec 2026 | MIT fall course premiere, community onboarding |
| Phase 3 | 2027 | Scale, partnerships, Hugging Face integration |

---

## License

TBD — will be determined by community governance process.
