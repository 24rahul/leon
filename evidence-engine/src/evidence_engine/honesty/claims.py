"""The claim algebra — outputs are *constructed*, never *filtered into* safety.

A `Claim` is the ONLY way this engine speaks. It is a closed sum type: a `Stance`
drawn from a four-element enum plus *structured* referents. Its natural-language
form is a **pure function** of those fields (`render`). There is no constructor
that accepts free-form assertive prose, so a forbidden claim ("X is effective")
is not rejected at runtime — it is unrepresentable in the type.

This is the primary safety mechanism. The word-blacklist in `vocabulary_guard`
is a secondary tripwire over the rendered text, not the guarantee itself.

The four stances form a deliberately impoverished vocabulary. There is no
"positive", no "negative", no "significant" — only:

    INSUFFICIENT_EVIDENCE        (the default; the only honest answer most of the time)
    CONSISTENT_WITH              (the data do not refute an association, given assumptions)
    HYPOTHESIS_GENERATING        (worth forming a hypothesis about)
    REQUIRES_CONFIRMATORY_TRIAL  (the terminal stance: only a trial can advance it)

Note what is absent: a stance that asserts truth, efficacy, safety, or action.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Final, assert_never


class Stance(enum.Enum):
    """The closed set of epistemic postures the engine may adopt."""

    INSUFFICIENT_EVIDENCE = "insufficient evidence"
    CONSISTENT_WITH = "consistent with"
    HYPOTHESIS_GENERATING = "hypothesis-generating"
    REQUIRES_CONFIRMATORY_TRIAL = "requires confirmatory trial"


# Total ordering of epistemic strength. Promotion up this ladder requires
# surviving every guardrail; the default floor is INSUFFICIENT_EVIDENCE.
_RANK: Final[dict[Stance, int]] = {
    Stance.INSUFFICIENT_EVIDENCE: 0,
    Stance.CONSISTENT_WITH: 1,
    Stance.HYPOTHESIS_GENERATING: 2,
    Stance.REQUIRES_CONFIRMATORY_TRIAL: 3,
}


def weakest(*stances: Stance) -> Stance:
    """Combine stances pessimistically — the chain is only as strong as its
    weakest link. Used to fold audit/calibration/equity downgrades together."""
    return min(stances, key=lambda s: _RANK[s])


@dataclass(frozen=True)
class Claim:
    """A single sanctioned statement. Rendered purely from its structured fields."""

    stance: Stance
    exposure: str
    outcome: str
    scope: str  # the pre-registered research context this claim is bounded to

    def render(self) -> str:
        """The one and only sentence this claim is permitted to become.

        Built by template selection on the stance; the referents are inserted as
        *quoted identifiers*, never as assertions, so no phrasing outside the
        sanctioned forms can be produced here.
        """
        x, y, scope = repr(self.exposure), repr(self.outcome), self.scope
        if self.stance is Stance.INSUFFICIENT_EVIDENCE:
            return (
                f"Within {scope}, the available observational data provide "
                f"insufficient evidence regarding any association between {x} and {y}."
            )
        if self.stance is Stance.CONSISTENT_WITH:
            return (
                f"Within {scope}, the observational data are consistent with an "
                f"association between {x} and {y}, conditional on the stated "
                f"identifying assumptions; this is hypothesis-generating."
            )
        if self.stance is Stance.HYPOTHESIS_GENERATING:
            return (
                f"Within {scope}, an association between {x} and {y} is "
                f"hypothesis-generating and requires confirmatory trial before any "
                f"interpretation beyond this research context."
            )
        if self.stance is Stance.REQUIRES_CONFIRMATORY_TRIAL:
            return (
                f"Within {scope}, any association between {x} and {y} requires "
                f"confirmatory trial; the observational data alone cannot advance it."
            )
        # Exhaustiveness: if a Stance is ever added without a branch here, mypy
        # flags this line at type-check time (and it raises at runtime).
        assert_never(self.stance)

    def to_dict(self) -> dict[str, str]:
        return {
            "stance": self.stance.name,
            "stance_phrase": self.stance.value,
            "exposure": self.exposure,
            "outcome": self.outcome,
            "scope": self.scope,
            "statement": self.render(),
        }
