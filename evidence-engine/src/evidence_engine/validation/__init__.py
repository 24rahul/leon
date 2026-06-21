"""Data-driven validation: does the pipeline recover known causal truth?

A causal-inference engine cannot be validated by unit tests alone — those check
that components do what their code says. The question that matters is whether the
*whole estimation chain* returns the right answer. We answer it the only rigorous
way available: a Monte Carlo simulation study against a data-generating process
whose true causal effect we know by construction, measuring bias, confidence-
interval coverage, Type I error, power, estimator concordance, and whether the
empirical-null calibration restores nominal coverage under residual confounding.
"""
