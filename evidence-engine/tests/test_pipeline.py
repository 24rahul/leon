"""End-to-end pipeline: restricted-data guard, full run, and reproducibility."""

import json
from pathlib import Path

import pytest
import yaml

from evidence_engine.config import load_config
from evidence_engine.data import loader
from evidence_engine.pipeline import run


def _fast_config(tmp_path: Path) -> Path:
    base = yaml.safe_load(Path("config.yaml").read_text())
    base["data"]["demo_path"] = str(tmp_path / "no_such_demo")  # force synthetic
    base["data"]["synthetic_n_patients"] = 1200
    base["estimator"]["negative_control_panel_size"] = 15
    base["estimator"]["bootstrap_iterations"] = 50
    base["estimator"]["gcomp_bootstrap_iterations"] = 40
    base["estimator"]["refuter_simulations"] = 8
    base["run"]["output_dir"] = str(tmp_path / "out")
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(base))
    return p


def test_restricted_data_guard():
    cfg = load_config("config.yaml")
    raw = dict(cfg.raw)
    raw["data"] = {**raw["data"], "full_data_path": "/restricted/mimic", "forbid_restricted": True}
    from evidence_engine.config import Config
    spoofed = Config(raw=raw, path=cfg.path, config_hash="x")
    with pytest.raises(loader.RestrictedDataError):
        loader.load(spoofed)


@pytest.mark.slow
def test_end_to_end_produces_guarded_object(tmp_path):
    cfg_path = _fast_config(tmp_path)
    result = run(cfg_path)
    # Required structure.
    for key in ("claim", "evidence_tier", "estimate", "empirical_calibration",
                "e_value", "equity", "audit_caveats", "assumptions", "provenance"):
        assert key in result
    # The audit report and evidence object were written.
    out = tmp_path / "out"
    assert (out / "phase0_audit_report.md").exists()
    assert (out / "evidence_object.json").exists()
    # Synthetic data is flagged honestly.
    assert result["data_is_synthetic"] is True
    # The provenance carries the full content-addressed chain.
    assert result["provenance"]["artifact_ledger"]["root"] == result["artifact_root"]


@pytest.mark.slow
def test_byte_identical_reproducibility(tmp_path):
    cfg_path = _fast_config(tmp_path)
    r1 = run(cfg_path)
    snap1 = json.dumps(r1, sort_keys=True)
    r2 = run(cfg_path)
    snap2 = json.dumps(r2, sort_keys=True)
    assert snap1 == snap2
