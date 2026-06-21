"""Render the Phase 0 audit as a human-readable markdown report.

All prose passes through the controlled-vocabulary guard before it is written,
so the audit cannot accidentally state a clinical claim.
"""

from __future__ import annotations

from .phase0 import Phase0Result
from ..honesty.vocabulary_guard import guard_text


def _table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def render(result: Phase0Result) -> str:
    r = result
    lines: list[str] = []
    lines.append("# Phase 0 — Data-Generating-Process Audit")
    lines.append("")
    lines.append(
        "> This audit characterizes the dataset as a **biased artifact** before "
        "any inference is permitted. Its findings are carried forward as caveats "
        "on every downstream result."
    )
    lines.append("")
    lines.append(f"- **Data version:** `{r.data_version}`")
    lines.append(f"- **Synthetic surrogate:** {'YES' if r.is_synthetic else 'no'}")
    lines.append(f"- **Patients (rows):** {r.n_patients}")
    lines.append("")

    if r.is_synthetic:
        lines.append(
            "> ⚠️ **These are SYNTHETIC data.** The numbers below illustrate the "
            "audit machinery on planted biases; they are not real measurements "
            "and have no clinical meaning."
        )
        lines.append("")

    # --- 1. Representation -------------------------------------------------
    lines.append("## 1. Cohort representation")
    lines.append("")
    lines.append(
        "Single-center ICU data is **not representative**. Counts below describe "
        "this cohort only."
    )
    for stratum, levels in r.representation.items():
        lines.append("")
        lines.append(f"### By `{stratum}`")
        rows = [
            [str(k), str(v["count"]), f"{v['proportion']:.1%}"]
            for k, v in levels.items()
        ]
        lines.append(_table(["level", "count", "proportion"], rows))

    # --- 2. Pulse-oximetry probe -----------------------------------------
    lines.append("")
    lines.append("## 2. Flagship measurement-bias probe — pulse oximetry")
    lines.append("")
    po = r.pulse_oximetry
    if not po.get("available"):
        lines.append(f"_Probe unavailable: {po.get('reason', 'unknown')}._")
    else:
        d = po["definition"]
        lines.append(
            f"**Occult hypoxemia** := arterial SaO2 < {d['sao2_below']}% while the "
            f"pulse oximeter (SpO2) reads a reassuring "
            f"{d['spo2_reassuring_band'][0]}–{d['spo2_reassuring_band'][1]}%. "
            "A recorded SpO2 that misses actual arterial hypoxemia is a biased "
            "measurement."
        )
        lines.append("")
        rows = []
        for race, v in po["by_race"].items():
            rate = (
                f"{v['occult_hypoxemia_rate']:.1%}"
                if v["occult_hypoxemia_rate"] is not None
                else "n/a"
            )
            rows.append(
                [
                    race,
                    str(v["n_paired_readings"]),
                    str(v["n_reassuring_spo2"]),
                    str(v["n_occult_hypoxemia"]),
                    rate,
                    f"{v['mean_spo2_minus_sao2']:+.2f}",
                ]
            )
        lines.append(
            _table(
                [
                    "recorded race",
                    "paired readings",
                    "reassuring SpO2",
                    "occult hypoxemia",
                    "occult rate",
                    "mean SpO2−SaO2",
                ],
                rows,
            )
        )
        lines.append("")
        lines.append(
            f"Overall mean SpO2−SaO2 over-read: "
            f"**{po['overall_mean_spo2_minus_sao2']:+.2f}** percentage points. "
            "A positive value means the pulse oximeter reads higher than the "
            "arterial reference."
        )

    # --- 3. Differential testing -----------------------------------------
    lines.append("")
    lines.append("## 3. Differential testing")
    lines.append("")
    dt = r.differential_testing
    if not dt.get("available"):
        lines.append("_Differential-testing probe unavailable for this source._")
    else:
        lines.append(dt["note"])
        lines.append("")
        rows = [
            [race, str(v["n"]), f"{v['lactate_ordered_rate']:.1%}"]
            for race, v in dt["by_race"].items()
        ]
        lines.append(_table(["recorded race", "n", "lactate ordered rate"], rows))

    # --- 4. Missingness ---------------------------------------------------
    lines.append("")
    lines.append("## 4. Missingness (MNAR)")
    lines.append("")
    miss = r.missingness
    if miss["columns_with_missing"]:
        rows = [
            [c, str(v["n_missing"]), f"{v['fraction_missing']:.1%}"]
            for c, v in miss["columns_with_missing"].items()
        ]
        lines.append(_table(["column", "n missing", "fraction"], rows))
    else:
        lines.append("_No missing values detected in the analytic columns._")
    if miss.get("mnar_signal", {}).get("lactate_vs_severity"):
        s = miss["mnar_signal"]["lactate_vs_severity"]
        lines.append("")
        lines.append(
            f"**MNAR signal:** mean severity when lactate observed = "
            f"{s['mean_sofa_when_observed']} vs when missing = "
            f"{s['mean_sofa_when_missing']}. Missingness tracks severity, so it is "
            "not missing-at-random."
        )
    lines.append("")
    lines.append(
        f"Silent imputation is **forbidden** for: "
        f"`{', '.join(miss['silent_imputation_forbidden_for'])}`. "
        "Missingness is carried as explicit indicator variables."
    )

    # --- Caveats carried forward -----------------------------------------
    lines.append("")
    lines.append("## Caveats carried forward to every downstream result")
    lines.append("")
    for c in r.caveats:
        lines.append(f"- {c}")
    lines.append("")

    text = "\n".join(lines)
    return guard_text(text, where="phase0_audit_report")
