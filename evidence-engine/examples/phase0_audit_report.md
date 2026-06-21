# Phase 0 — Data-Generating-Process Audit

> This audit characterizes the dataset as a **biased artifact** before any inference is permitted. Its findings are carried forward as caveats on every downstream result.

- **Data version:** `synthetic-surrogate-v1::n=4000::seed=20240617`
- **Synthetic surrogate:** YES
- **Patients (rows):** 4000

> ⚠️ **These are SYNTHETIC data.** The numbers below illustrate the audit machinery on planted biases; they are not real measurements and have no clinical meaning.

## 1. Cohort representation

Single-center ICU data is **not representative**. Counts below describe this cohort only.

### By `race`
| level | count | proportion |
|---|---|---|
| WHITE | 2495 | 62.4% |
| BLACK/AFRICAN AMERICAN | 664 | 16.6% |
| HISPANIC/LATINO | 350 | 8.8% |
| OTHER/UNKNOWN | 248 | 6.2% |
| ASIAN | 243 | 6.1% |

### By `sex`
| level | count | proportion |
|---|---|---|
| M | 2283 | 57.1% |
| F | 1717 | 42.9% |

### By `age_group`
| level | count | proportion |
|---|---|---|
| 55-69 | 1401 | 35.0% |
| 70-84 | 1025 | 25.6% |
| 40-54 | 886 | 22.1% |
| 85+ | 417 | 10.4% |
| 18-39 | 271 | 6.8% |

## 2. Flagship measurement-bias probe — pulse oximetry

**Occult hypoxemia** := arterial SaO2 < 88.0% while the pulse oximeter (SpO2) reads a reassuring 92.0–96.0%. A recorded SpO2 that misses actual arterial hypoxemia is a biased measurement.

| recorded race | paired readings | reassuring SpO2 | occult hypoxemia | occult rate | mean SpO2−SaO2 |
|---|---|---|---|---|---|
| ASIAN | 176 | 60 | 0 | 0.0% | +1.28 |
| BLACK/AFRICAN AMERICAN | 460 | 168 | 16 | 9.5% | +2.71 |
| HISPANIC/LATINO | 236 | 80 | 1 | 1.2% | +1.64 |
| OTHER/UNKNOWN | 157 | 55 | 0 | 0.0% | +1.31 |
| WHITE | 2263 | 652 | 1 | 0.1% | +0.49 |

Overall mean SpO2−SaO2 over-read: **+0.96** percentage points. A positive value means the pulse oximeter reads higher than the arterial reference.

## 3. Differential testing

Ordering is a signal of access/suspicion, not neutral ascertainment.

| recorded race | n | lactate ordered rate |
|---|---|---|
| ASIAN | 243 | 37.5% |
| BLACK/AFRICAN AMERICAN | 664 | 33.6% |
| HISPANIC/LATINO | 350 | 30.0% |
| OTHER/UNKNOWN | 248 | 39.9% |
| WHITE | 2495 | 44.8% |

## 4. Missingness (MNAR)

| column | n missing | fraction |
|---|---|---|
| lactate | 2364 | 59.1% |

**MNAR signal:** mean severity when lactate observed = 5.657 vs when missing = 4.21. Missingness tracks severity, so it is not missing-at-random.

Silent imputation is **forbidden** for: `race, sex, spo2, sao2`. Missingness is carried as explicit indicator variables.

## Caveats carried forward to every downstream result

- Data are a SYNTHETIC surrogate, not real MIMIC-IV; findings are illustrative of the machinery only and carry no clinical meaning.
- Source is single-center ICU data and is NOT representative of any general population; effects observed here may not transfer.
- Pulse-oximetry probe: occult-hypoxemia rate varies by recorded race (highest in 'BLACK/AFRICAN AMERICAN'); SpO2 is a racially biased measurement and any analysis using it inherits that bias.
- Measurement/testing rates differ by recorded race; observed values are conditioned on differential ascertainment.
- Equity-relevant variables are never silently imputed; missingness is carried as explicit indicator variables.
