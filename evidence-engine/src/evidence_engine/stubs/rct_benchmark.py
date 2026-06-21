"""STUB — RCT-benchmark harness (calibrate the whole method against ground truth).

The only way to know whether the engine's observational estimates track reality is
to replay questions where a randomized trial already gave the answer, and measure
how often the engine's hypothesis tier agrees in sign and magnitude. This is the
OHDSI "LEGEND"/benchmark idea and the RCT-DUPLICATE programme in spirit.

Intended contract:
  * A registry of (observational question, published RCT result) pairs.
  * Run the full pipeline on each, compare the calibrated estimate to the RCT
    effect, and produce coverage / sign-concordance / calibration plots.
  * Emit a *method-level* reliability statement that bounds how much trust any
    single finding deserves — itself an input to the evidence tier.

ROADMAP: Phase 3. Not yet implemented.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RctBenchmark(Protocol):
    def evaluate(self, pipeline: Any, registry: Any) -> dict[str, Any]:
        """Replay benchmarked questions; return method-level reliability metrics."""
        ...


class NotImplementedRctBenchmark:
    _MSG = (
        "RCT-benchmark harness is a Phase-3 stub (stubs/rct_benchmark.py). The "
        "prototype cannot yet state method-level reliability. See ROADMAP.md."
    )

    def evaluate(self, pipeline: Any, registry: Any) -> dict[str, Any]:
        raise NotImplementedError(self._MSG)
