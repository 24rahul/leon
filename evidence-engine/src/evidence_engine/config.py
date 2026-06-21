"""Configuration loading and content-hashing.

The config is the single source of truth for the run. Its SHA-256 is stamped on
every result for provenance, so an accidental edit changes the recorded hash.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Config:
    """Immutable view over the parsed config plus its content hash."""

    raw: dict[str, Any]
    path: Path
    config_hash: str

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)


def _canonical_hash(obj: Any) -> str:
    """Stable hash independent of key ordering / whitespace in the YAML file."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def load_config(path: str | Path = "config.yaml") -> Config:
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise ValueError(f"Config at {path} did not parse to a mapping.")
    return Config(raw=raw, path=path, config_hash=_canonical_hash(raw))
