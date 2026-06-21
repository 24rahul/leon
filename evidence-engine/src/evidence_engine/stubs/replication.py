"""STUB — cross-dataset replication (Harm (b): a single-source artifact entrenching
inequity).

A finding from one single-center ICU is a property of that center as much as of
biology. Replication across data sources with *different* populations and
*different* biases is the strongest available check that an association is not an
artifact of one dataset's measurement and selection. Mirrors the OHDSI network-study
model: same sealed protocol, executed against multiple OMOP CDM databases.

Intended contract:
  * Execute the identical sealed protocol against ≥2 independent data sources
    (each behind its own restricted-data guard).
  * Combine via random-effects meta-analysis on the *calibrated* estimates, with
    between-source heterogeneity (I², τ²) reported.
  * Downgrade when sources disagree; never pool away heterogeneity silently.

ROADMAP: Phase 3. Not yet implemented.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CrossDatasetReplication(Protocol):
    def replicate(self, sealed_protocol: Any, sources: Any) -> dict[str, Any]:
        """Run the protocol across sources; return meta-analytic, calibrated result."""
        ...


class NotImplementedReplication:
    _MSG = (
        "Cross-dataset replication is a Phase-3 stub (stubs/replication.py). The "
        "prototype runs on a single source only. See ROADMAP.md."
    )

    def replicate(self, sealed_protocol: Any, sources: Any) -> dict[str, Any]:
        raise NotImplementedError(self._MSG)
