"""Provenance as a content-addressed artifact chain (Harm (c): verify, don't trust).

Two layers:

1. ``Provenance`` — the static fingerprint of a run: engine version, git commit,
   config hash, protocol hash, data version, seed. Necessary but not sufficient:
   it tells you *what* was claimed to produce a result, not whether the result is
   internally consistent.

2. ``ArtifactLedger`` — a Merkle-style DAG over pipeline stages. Each stage emits
   an ``Artifact`` whose id is ``H(stage || canonical(payload) || parent_ids)``.
   Because every id folds in its parents' ids, the final ``root`` id transitively
   commits to the entire computation. Anyone re-running the pipeline can recompute
   the root and compare: equality is a *proof of reproduction*, not a promise of
   one. This is the concrete mechanism by which a third party can audit a finding
   rather than trust its author.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any

from . import __version__


# --------------------------------------------------------------------------- #
# Canonical hashing                                                           #
# --------------------------------------------------------------------------- #
def canonical_hash(obj: Any) -> str:
    """SHA-256 over a canonical JSON encoding (order-independent, whitespace-free).

    ``default=str`` makes non-JSON scalars (e.g. numpy types, datetimes) hashable
    deterministically. The same object always yields the same digest.
    """
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Static provenance fingerprint                                              #
# --------------------------------------------------------------------------- #
def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:  # pragma: no cover - environment dependent
        pass
    return "unknown"


@dataclass(frozen=True)
class Provenance:
    engine_version: str
    git_commit: str
    config_hash: str
    protocol_hash: str
    data_version: str
    seed: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_provenance(
    *, config_hash: str, protocol_hash: str, data_version: str, seed: int
) -> Provenance:
    return Provenance(
        engine_version=__version__,
        git_commit=_git_commit(),
        config_hash=config_hash,
        protocol_hash=protocol_hash,
        data_version=data_version,
        seed=seed,
    )


# --------------------------------------------------------------------------- #
# Content-addressed artifact ledger                                          #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Artifact:
    """An immutable, content-addressed record of one pipeline stage's output."""

    stage: str
    artifact_id: str
    parents: tuple[str, ...]
    payload_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArtifactLedger:
    """Append-only DAG of artifacts; the last id transitively commits to all."""

    artifacts: list[Artifact] = field(default_factory=list)

    def add(self, stage: str, payload: Any, parents: tuple[str, ...] = ()) -> str:
        payload_digest = canonical_hash(payload)
        artifact_id = canonical_hash(
            {"stage": stage, "payload": payload_digest, "parents": list(parents)}
        )
        self.artifacts.append(
            Artifact(
                stage=stage,
                artifact_id=artifact_id,
                parents=tuple(parents),
                payload_digest=payload_digest,
            )
        )
        return artifact_id

    @property
    def root(self) -> str:
        """The id of the most recently added artifact (the run's Merkle root)."""
        if not self.artifacts:
            raise ValueError("Ledger is empty; nothing to root.")
        return self.artifacts[-1].artifact_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root if self.artifacts else None,
            "chain": [a.to_dict() for a in self.artifacts],
        }
