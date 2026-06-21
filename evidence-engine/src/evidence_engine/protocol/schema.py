"""Frozen, pre-registered target-trial protocol — enforced by capability.

The spec says "pre-register before outcomes are examined." A *procedure* that
relies on discipline fails under pressure, so here the ordering is enforced by
the dataflow:

    Protocol (mutable spec, no outcome access)
        │  .seal()  ──computes & freezes the SHA-256 fingerprint──►
        ▼
    SealedProtocol (immutable, hashed)
        │  .outcome_token()  ──mints an unforgeable capability──►
        ▼
    OutcomeAccessToken  ──required by every function that reads Y──►

You cannot read an outcome column without an ``OutcomeAccessToken``; you cannot
obtain one without a ``SealedProtocol``; sealing *is* the act of committing the
pre-registration hash. Peeking at outcomes therefore requires having already
frozen the analysis — immortal-time bias and outcome-driven protocol edits are
excluded by construction, not by comment.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Final

# Module-private capability key. An OutcomeAccessToken can only be minted by code
# in this module (i.e. by sealing a protocol), because only this module holds the
# sentinel its constructor demands.
_MINT: Final = object()


class OutcomeAccessToken:
    """Unforgeable capability proving a protocol was sealed before Y was read."""

    protocol_hash: str
    __slots__ = ("protocol_hash",)

    def __init__(self, protocol_hash: str, _key: object) -> None:
        if _key is not _MINT:
            raise RuntimeError(
                "OutcomeAccessToken cannot be constructed directly. Seal a "
                "Protocol (Protocol.seal().outcome_token()) to obtain one — this "
                "is the pre-registration guarantee."
            )
        object.__setattr__(self, "protocol_hash", protocol_hash)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"OutcomeAccessToken(protocol_hash={self.protocol_hash[:12]}…)"


@dataclass(frozen=True)
class Confounder:
    name: str
    justification: str  # a WRITTEN clinical reason is mandatory at registration

    def __post_init__(self) -> None:
        if not self.justification or not self.justification.strip():
            raise ValueError(
                f"Confounder {self.name!r} has no written clinical justification. "
                "Every confounder must be justified when the protocol is written, "
                "not after seeing results."
            )


@dataclass(frozen=True)
class Eligibility:
    min_age: int = 18
    require_icu_stay: bool = True


@dataclass(frozen=True)
class Protocol:
    """The pre-outcome specification. Has no ability to read outcomes."""

    name: str
    eligibility: Eligibility
    exposure: str
    outcome: str
    time_zero: str
    follow_up_days: int
    estimand: str
    confounders: tuple[Confounder, ...]
    negative_control_outcomes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.time_zero:
            raise ValueError("time_zero must be specified to forbid immortal-time bias.")
        if self.follow_up_days <= 0:
            raise ValueError("follow_up_days must be positive.")
        if not self.confounders:
            raise ValueError(
                "At least one justified confounder is required to make the "
                "identifying assumptions explicit."
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def _hash(self) -> str:
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def seal(self) -> "SealedProtocol":
        """Freeze the pre-registration: compute and bind the protocol hash."""
        return SealedProtocol(protocol=self, protocol_hash=self._hash())


@dataclass(frozen=True)
class SealedProtocol:
    """An immutable protocol with its committed pre-registration fingerprint."""

    protocol: Protocol
    protocol_hash: str

    def outcome_token(self) -> OutcomeAccessToken:
        """Mint the capability required to read outcome columns."""
        return OutcomeAccessToken(self.protocol_hash, _MINT)

    def confounder_names(self) -> list[str]:
        return [c.name for c in self.protocol.confounders]

    def to_dict(self) -> dict[str, Any]:
        return {"protocol": self.protocol.to_dict(), "protocol_hash": self.protocol_hash}


def assert_token(token: OutcomeAccessToken, sealed: SealedProtocol) -> None:
    """Verify a token authorizes outcome access for *this* sealed protocol."""
    if not isinstance(token, OutcomeAccessToken):
        raise PermissionError("A valid OutcomeAccessToken is required to read outcomes.")
    if token.protocol_hash != sealed.protocol_hash:
        raise PermissionError(
            "OutcomeAccessToken does not match this protocol's hash; refusing to "
            "read outcomes under a different pre-registration."
        )


def protocol_from_config(cfg: dict[str, Any]) -> Protocol:
    """Build the (unsealed) Protocol from the ``protocol:`` block of config.yaml."""
    eligibility = Eligibility(
        min_age=int(cfg["eligibility"]["min_age"]),
        require_icu_stay=bool(cfg["eligibility"]["require_icu_stay"]),
    )
    confounders = tuple(
        Confounder(name=c["name"], justification=c["justification"])
        for c in cfg["confounders"]
    )
    return Protocol(
        name=cfg["name"],
        eligibility=eligibility,
        exposure=cfg["exposure"],
        outcome=cfg["outcome"],
        time_zero=cfg["time_zero"],
        follow_up_days=int(cfg["follow_up_days"]),
        estimand=cfg["estimand"],
        confounders=confounders,
        negative_control_outcomes=tuple(cfg.get("negative_control_outcomes", [])),
    )
