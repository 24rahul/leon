"""End-to-end pipeline: Phase-0 audit → sealed protocol → cohort → IPTW →
negative-control calibration → refutation → E-value → equity → evidence object.

Order is not cosmetic. The Phase-0 audit runs FIRST and unconditionally; its
caveats are threaded into the final object. The protocol is SEALED before any
outcome is read; outcome access is mediated by the capability token throughout.
Every stage appends a content-addressed artifact to the ledger, so the final
`artifact_root` transitively commits to the entire computation.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from .audit import phase0, report as audit_report
from .cohort.builder import build_cohort
from .config import Config, load_config
from .data import loader
from .estimator import calibration as calib
from .estimator import concurrence as conc
from .estimator import refutation
from .estimator.aipw import estimate_aipw
from .estimator.evalue import evalue_for_rr
from .estimator.gcomputation import estimate_gcomputation
from .estimator.iptw import bootstrap_rr_ci, estimate_outcome, fit_propensity
from .estimator.matching import estimate_matching
from .estimator.tmle import estimate_tmle
from .estimator.units import LogRiskRatio, RiskRatio
from .equity.stratify import stratified_estimates
from .honesty.evidence_object import build_evidence_object
from .logging_setup import get_logger
from .protocol.dag_approval import build_and_approve_dag
from .protocol.dag_gate import require_certificate
from .protocol.schema import protocol_from_config
from .provenance import ArtifactLedger, build_provenance


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(config_path: str | Path = "config.yaml") -> dict[str, Any]:
    cfg: Config = load_config(config_path)
    seed = int(cfg["run"]["seed"])
    np.random.seed(seed)
    log = get_logger("evidence_engine", cfg["run"].get("log_level", "INFO"))
    out_dir = Path(cfg["run"]["output_dir"])
    ledger = ArtifactLedger()

    # --- data --------------------------------------------------------------
    tables, data_version = loader.load(cfg)
    a_data = ledger.add("data", {"data_version": data_version})
    log.info("data loaded", extra={"context": {"data_version": data_version}})

    # --- Phase 0 audit (runs first, unconditionally) -----------------------
    p0 = phase0.run_phase0(tables, data_version, audit_cfg=cfg["audit"])
    tables["patients"] = phase0.add_missingness_indicators(tables["patients"])
    md = audit_report.render(p0)
    _write(out_dir / "phase0_audit_report.md", md)
    a_audit = ledger.add("phase0_audit", p0.to_dict(), (a_data,))
    log.info("phase0 audit complete", extra={"context": {"n": p0.n_patients}})

    # --- sealed protocol + capability token --------------------------------
    protocol = protocol_from_config(cfg["protocol"])
    sealed = protocol.seal()
    token = sealed.outcome_token()  # minting REQUIRES the seal
    a_proto = ledger.add("protocol", sealed.to_dict(), (a_audit,))

    # --- human DAG-approval gate (Harm c) ----------------------------------
    # Refuses to proceed unless the causal graph passes structural checks AND the
    # required human quorum has signed it. The certificate gates estimation below.
    dag, dag_cert = build_and_approve_dag(sealed, cfg.get("dag", {}))
    a_dag = ledger.add("dag_approval", dag_cert.to_dict(), (a_proto,))
    log.info(
        "DAG approved",
        extra={"context": {"dag": dag.dag_hash()[:12], "signers": len(dag_cert.signatures)}},
    )

    # --- cohort (time-zero enforced) ---------------------------------------
    # The estimation path is structurally gated: no certificate, no cohort.
    require_certificate(dag_cert, dag, sealed.protocol_hash)
    cohort = build_cohort(sealed, tables["patients"])
    a_cohort = ledger.add("cohort", cohort.summary(), (a_dag,))
    log.info("cohort built", extra={"context": cohort.summary()})

    confounders = sealed.confounder_names()
    no_impute = cfg["audit"]["no_impute_variables"]
    trim = tuple(cfg["estimator"]["trim_propensity"])

    # --- propensity fitted ONCE; weights reused for every outcome ----------
    fit = fit_propensity(
        cohort.frame, protocol.exposure, confounders,
        no_impute=no_impute, trim=trim, seed=seed,
    )
    keep = fit.keep_mask
    a_vec = cohort.exposure()[keep]
    a_ps = ledger.add("propensity", fit.diagnostics_dict(), (a_cohort,))

    # --- primary outcome (token-gated) -------------------------------------
    y_primary_full = cohort.outcome(protocol.outcome, token)
    y_primary = y_primary_full[keep]
    primary = estimate_outcome(y_primary, a_vec, fit.weights)
    a_est = ledger.add("primary_estimate", primary.to_dict(), (a_ps,))

    # --- estimator panel (triangulation across distinct failure modes) -----
    # IPTW (propensity-only), AIPW + TMLE (doubly robust), matching (discards
    # unmatched), g-computation (outcome-model only). Agreement across these is far
    # stronger than any single method. Each is fitted on the same kept cohort/PS.
    kept_frame = cohort.frame.loc[keep]
    panel = {
        "iptw": primary,
        "aipw": estimate_aipw(
            kept_frame, protocol.exposure, confounders, y_primary, fit.propensity,
            no_impute=no_impute, seed=seed,
        ),
        "matching": estimate_matching(
            kept_frame, protocol.exposure, y_primary, fit.propensity,
        ),
        "gcomputation": estimate_gcomputation(
            kept_frame, protocol.exposure, confounders, y_primary,
            no_impute=no_impute, seed=seed,
            n_boot=int(cfg["estimator"].get("gcomp_bootstrap_iterations", 200)),
        ),
        "tmle": estimate_tmle(
            kept_frame, protocol.exposure, confounders, y_primary, fit.propensity,
            no_impute=no_impute, seed=seed,
        ),
    }
    concurrence = conc.compare(panel).to_dict()
    a_aipw = ledger.add(
        "estimator_panel",
        {"panel": {k: v.to_dict() for k, v in panel.items()}, "concurrence": concurrence},
        (a_est,),
    )

    # --- bootstrap CI (captures propensity-estimation uncertainty) ---------
    bootstrap = bootstrap_rr_ci(
        cohort.frame, protocol.exposure, y_primary_full, confounders,
        no_impute=no_impute, trim=trim, seed=seed,
        n_boot=int(cfg["estimator"].get("bootstrap_iterations", 500)),
    )
    a_boot = ledger.add("bootstrap", bootstrap, (a_aipw,))

    # --- negative-control panel + empirical calibration --------------------
    nc_cols = sorted(c for c in cohort.frame.columns if c.startswith("nc_"))
    nc_log_rr: list[float] = []
    nc_se: list[float] = []
    nc_named: dict[str, Any] = {}
    for nc in nc_cols:
        y_nc = cohort.outcome(nc, token)[keep]
        est_nc = estimate_outcome(y_nc, a_vec, fit.weights)
        if est_nc.status == "ok" and est_nc.log_rr is not None:
            nc_log_rr.append(est_nc.log_rr)
            nc_se.append(est_nc.se_log_rr)  # type: ignore[arg-type]
        if not nc.startswith("nc_0"):  # the human-readable named controls
            nc_named[nc] = est_nc.to_dict()

    null = calib.fit_empirical_null(
        np.array(nc_log_rr), np.array(nc_se),
        min_controls=int(cfg["estimator"]["min_negative_controls"]),
    )
    if primary.status == "ok" and primary.log_rr is not None and primary.se_log_rr is not None:
        calibrated = calib.calibrate(LogRiskRatio(primary.log_rr), primary.se_log_rr, null)
    else:
        calibrated = calib.calibrate(LogRiskRatio(0.0), 1.0, null)
    a_calib = ledger.add(
        "calibration",
        {"empirical_null": null.to_dict(), "calibrated": calibrated.to_dict()},
        (a_boot,),
    )

    # --- E-value (computed on the CALIBRATED estimate when available) ------
    # The NewType wraps make the risk-ratio scale explicit and mypy-checked.
    if calibrated.calibrated_log_rr is not None and calibrated.calibrated_ci95 is not None:
        ev = evalue_for_rr(
            RiskRatio(math.exp(calibrated.calibrated_log_rr)),
            RiskRatio(calibrated.calibrated_ci95[0]),
            RiskRatio(calibrated.calibrated_ci95[1]),
        )
    elif primary.risk_ratio is not None and primary.ci95_rr is not None:
        ev = evalue_for_rr(
            RiskRatio(primary.risk_ratio),
            RiskRatio(primary.ci95_rr[0]),
            RiskRatio(primary.ci95_rr[1]),
        )
    else:
        ev = evalue_for_rr(RiskRatio(1.0), RiskRatio(1.0), RiskRatio(1.0))
    a_ev = ledger.add("evalue", ev.to_dict(), (a_calib,))

    # --- refutation (falsification probes) ---------------------------------
    refs = refutation.run_refutations(
        cohort.frame.assign(**{protocol.outcome: cohort.outcome(protocol.outcome, token)}),
        protocol.exposure, protocol.outcome, confounders, seed=seed,
        num_simulations=int(cfg["estimator"].get("refuter_simulations", 20)),
    )
    placebo_alarmed = refutation.placebo_alarm(refs)
    a_ref = ledger.add("refutation", [r.to_dict() for r in refs], (a_ev,))

    # --- equity-stratified estimation --------------------------------------
    equity = stratified_estimates(
        cohort, protocol.outcome, token, confounders,
        stratifier="race", no_impute=no_impute, trim=trim, seed=seed,
        min_stratum_n=int(cfg["reporting"]["min_stratum_n"]),
    ).to_dict()
    a_eq = ledger.add("equity", equity, (a_ref,))

    # --- provenance + evidence object --------------------------------------
    prov = build_provenance(
        config_hash=cfg.config_hash,
        protocol_hash=sealed.protocol_hash,
        data_version=data_version,
        seed=seed,
    ).to_dict()

    scope = (
        f"the pre-registered research context "
        f"'{protocol.name}' on data '{data_version}'"
    )
    negative_controls = {
        "panel_size_estimable": len(nc_log_rr),
        "named_controls": nc_named,
        "empirical_null": null.to_dict(),
    }
    evidence = build_evidence_object(
        exposure=protocol.exposure,
        outcome=protocol.outcome,
        scope=scope,
        estimate=primary,
        propensity=fit,
        calibration=calibrated,
        evalue=ev,
        refutations=[r.to_dict() for r in refs],
        placebo_alarmed=placebo_alarmed,
        audit_caveats=p0.caveats,
        equity=equity,
        provenance=prov,
        artifact_root="",  # filled after the ledger closes below
        is_synthetic=p0.is_synthetic,
        negative_controls=negative_controls,
        concurrence=concurrence,
        bootstrap=bootstrap,
        causal_dag=dag_cert.to_dict(),
    )

    a_evidence = ledger.add("evidence_object", evidence.to_dict(), (a_eq,))
    evidence.artifact_root = a_evidence  # the Merkle root commits to everything

    serialized = evidence.serialize()  # passes the controlled-vocabulary guard
    serialized["provenance"]["artifact_ledger"] = ledger.to_dict()

    _write(
        out_dir / "evidence_object.json",
        json.dumps(serialized, indent=2, sort_keys=True),
    )
    log.info(
        "pipeline complete",
        extra={"context": {"tier": evidence.evidence_tier, "root": a_evidence[:12]}},
    )
    return serialized


if __name__ == "__main__":  # pragma: no cover
    run()
