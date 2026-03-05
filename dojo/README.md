# Dojo: Evaluation + Coaching for Health AI

A platform where health AI models are evaluated across multiple dimensions and then coached to improve — not just scored and abandoned.

## The Problem

Health AI evaluation today is one-shot (submit, score, leave), decontextualized (tested in isolation from deployment), and demographically naive (auditing by race/sex gives false confidence about fairness). When failures are found, the path to fixing them is unclear.

## What Dojo Does Differently

**1. Care phenotypes instead of demographics.** We generate patient subgroups based on treatment patterns (monitoring frequency, intervention timing) adjusted for illness severity. Our preliminary work shows these reveal model performance disparities invisible to standard race/sex auditing.

**2. Coaching, not just scoring.** Every evaluation finding comes with an automated remediation plan, curated resources from a community library, and a structured expert match. The success metric is model improvement on re-evaluation, not the initial score.

## Phase 1 Agents

- **Shortcut Detective** — Identifies spurious correlations in medical imaging models (e.g., chest tube → pneumonia) using feature attribution, subgroup ablation, and counterfactual generation.
- **Care Phenotype Agent** — Generates treatment-pattern-based patient subgroups for fairness auditing as an alternative to demographic labels.

## Status

Phase 0: Grant writing and validation of existing tools. Target NIH submission: end of May 2026.

## Documentation

- [Project Plan](./docs/project-plan.md) — Full technical plan, architecture, timeline, risks
- [Grant Specific Aims](./docs/grant-specific-aims.md) — NIH proposal draft (v4)
- [Use Cases](./docs/use-cases.md) — Three scenarios including failure modes
- [Values Charter](./docs/values-charter.md) — Community values and governance principles

## Team

Distributed across MIT, Google, University of Pittsburgh, Vanderbilt, University of Geneva, Johns Hopkins, University Health Network (Canada), and collaborators in South Korea, Japan, Germany, France, and Colombia.

## Key Frameworks

- **LTARC**: Local, Task-specific, Agile, Reflexive, Community-powered evaluation
- **Value Sensitive Design**: Centering stakeholder values from the design phase
- **AI Plasticity**: Hypothesis that structured community engagement with AI failures leads to measurable shifts in participant practices (research question, not assumption)
