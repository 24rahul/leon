# Pipeline validation report

**Overall verdict: ✅ PASS** — Monte Carlo study, n=3000 patients/replication, 300 replications/scenario. Estimators driven are the engine's own `fit_propensity` + `estimate_outcome` (IPTW), `estimate_aipw` (AIPW), and the empirical-null calibration — compared against a crude unadjusted estimator and the data-generating process's known marginal causal effect.

## 1. Recovery of known truth, by scenario

For each true risk ratio we report bias (log scale; 0 = unbiased), 95% CI coverage (should be ≈0.95), and the rejection rate (= **Type I error** when true RR=1, = **power** otherwise).

### True RR = 1.000  (log = +0.000)

| estimator | bias(log) | RMSE | coverage | reject rate | mean CI width | n |
|---|---:|---:|---:|---:|---:|---:|
| crude | +0.405 | 0.410 | 0.000 | 1.000 | 0.261 | 300 |
| iptw | +0.003 | 0.077 | 0.957 | 0.043 | 0.318 | 300 |
| aipw | +0.002 | 0.075 | 0.930 | 0.070 | 0.286 | 300 |

IPTW/AIPW sign concordance: **0.920**.

### True RR = 1.249  (log = +0.223)

| estimator | bias(log) | RMSE | coverage | reject rate | mean CI width | n |
|---|---:|---:|---:|---:|---:|---:|
| crude | +0.399 | 0.405 | 0.000 | 1.000 | 0.244 | 300 |
| iptw | -0.001 | 0.073 | 0.953 | 0.840 | 0.292 | 300 |
| aipw | -0.002 | 0.071 | 0.930 | 0.897 | 0.265 | 300 |

IPTW/AIPW sign concordance: **1.000**.

### True RR = 1.585  (log = +0.461)

| estimator | bias(log) | RMSE | coverage | reject rate | mean CI width | n |
|---|---:|---:|---:|---:|---:|---:|
| crude | +0.401 | 0.405 | 0.000 | 1.000 | 0.231 | 300 |
| iptw | +0.003 | 0.061 | 0.970 | 1.000 | 0.269 | 300 |
| aipw | +0.001 | 0.057 | 0.967 | 1.000 | 0.248 | 300 |

IPTW/AIPW sign concordance: **1.000**.

### True RR = 1.929  (log = +0.657)

| estimator | bias(log) | RMSE | coverage | reject rate | mean CI width | n |
|---|---:|---:|---:|---:|---:|---:|
| crude | +0.389 | 0.393 | 0.000 | 1.000 | 0.222 | 300 |
| iptw | -0.003 | 0.063 | 0.950 | 1.000 | 0.254 | 300 |
| aipw | -0.005 | 0.060 | 0.943 | 1.000 | 0.237 | 300 |

IPTW/AIPW sign concordance: **1.000**.

## 2. Empirical-null calibration under residual confounding

Negative-control outcomes have a TRUE null effect (RR=1) but share an *unmeasured* confounder the estimator never sees. Raw intervals therefore under-cover the null; calibration should restore it.

| metric | value |
|---|---:|
| negative-control estimates | 500 |
| raw 95% CI coverage of RR=1 | 0.422 |
| **calibrated** 95% CI coverage of RR=1 | **0.960** |
| estimated systematic bias μ (log) | +0.166 |

## 3. Pass/fail checks

| check | result | detail |
|---|:--:|---|
| iptw unbiased @RR=1.00 | ✅ | bias(log)=+0.003 (≤0.07) |
| iptw coverage @RR=1.00 | ✅ | coverage=0.957 in [0.9,0.98] |
| aipw unbiased @RR=1.00 | ✅ | bias(log)=+0.002 (≤0.07) |
| aipw coverage @RR=1.00 | ✅ | coverage=0.930 in [0.9,0.98] |
| iptw unbiased @RR=1.25 | ✅ | bias(log)=-0.001 (≤0.07) |
| iptw coverage @RR=1.25 | ✅ | coverage=0.953 in [0.9,0.98] |
| aipw unbiased @RR=1.25 | ✅ | bias(log)=-0.002 (≤0.07) |
| aipw coverage @RR=1.25 | ✅ | coverage=0.930 in [0.9,0.98] |
| iptw unbiased @RR=1.59 | ✅ | bias(log)=+0.003 (≤0.07) |
| iptw coverage @RR=1.59 | ✅ | coverage=0.970 in [0.9,0.98] |
| aipw unbiased @RR=1.59 | ✅ | bias(log)=+0.001 (≤0.07) |
| aipw coverage @RR=1.59 | ✅ | coverage=0.967 in [0.9,0.98] |
| iptw unbiased @RR=1.93 | ✅ | bias(log)=-0.003 (≤0.07) |
| iptw coverage @RR=1.93 | ✅ | coverage=0.950 in [0.9,0.98] |
| aipw unbiased @RR=1.93 | ✅ | bias(log)=-0.005 (≤0.07) |
| aipw coverage @RR=1.93 | ✅ | coverage=0.943 in [0.9,0.98] |
| iptw Type I error | ✅ | α̂=0.043 (≤0.1) |
| aipw Type I error | ✅ | α̂=0.070 (≤0.1) |
| iptw power @RR=1.93 | ✅ | power=1.000 (≥0.7) |
| aipw power @RR=1.93 | ✅ | power=1.000 (≥0.7) |
| confounding actually removed (crude vs IPTW) | ✅ | |crude bias|=0.405 vs |IPTW bias|=0.003 (gap≥0.07) |
| calibration restores coverage under residual confounding | ✅ | raw=0.422 → calibrated=0.960 |

## How to read this

- The **crude** rows are the control group: a naive analyst. Their large bias and 0% coverage are the confounding the pipeline must remove.
- IPTW and AIPW bias near 0 with ≈95% coverage means the engine recovers the true causal effect and its uncertainty is honest.
- Type I error ≈0.05 at the null means it does not manufacture findings; high power at real effects means it can still find them.
- Calibration lifting negative-control coverage back toward 0.95 shows the empirical-null machinery corrects residual (unmeasured) confounding.
