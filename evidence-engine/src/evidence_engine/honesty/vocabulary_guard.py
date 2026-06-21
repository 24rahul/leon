"""Controlled-vocabulary guard (Safety Invariant #3).

Outputs of this engine are HYPOTHESES, never claims of fact and never
recommendations. To make that impossible to violate by accident, every string
that is about to be serialized into a result is scanned. If it contains a
forbidden word it RAISES — the result cannot be written.

Allowed framing phrases (the only sanctioned ways to describe a finding):
    - "consistent with"
    - "hypothesis-generating"
    - "requires confirmatory trial"

Forbidden words (claims of truth, efficacy, safety, or action):
    true, effective, safe, proven, recommend, should, causes

The guard is intentionally blunt: it matches whole words, case-insensitively,
including common inflections (e.g. "proven", "pro ven" is not matched but
"proves"/"caused" are). False positives are acceptable; a missed claim is not.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# Whole-word stems. We append optional inflectional suffixes so that
# "causes"/"caused"/"causing", "recommends"/"recommended", "proven"/"proves"
# are all caught. "should" is matched as-is.
_FORBIDDEN_STEMS: dict[str, str] = {
    "true": r"true",
    "effective": r"effective(?:ly|ness)?",
    "safe": r"safe(?:r|st|ty|ly)?",
    "proven": r"prov(?:en|es|e|ed|ing)",
    "recommend": r"recommend(?:s|ed|ing|ation|ations)?",
    "should": r"should",
    "causes": r"caus(?:e|es|ed|ing|al|ality|ation)",
}

# Compiled once. \b word boundaries; IGNORECASE.
_FORBIDDEN_RE: dict[str, re.Pattern[str]] = {
    label: re.compile(rf"\b{pattern}\b", re.IGNORECASE)
    for label, pattern in _FORBIDDEN_STEMS.items()
}

ALLOWED_PHRASES: tuple[str, ...] = (
    "consistent with",
    "hypothesis-generating",
    "requires confirmatory trial",
)


class ControlledVocabularyError(ValueError):
    """Raised when a generated output contains a forbidden word."""


def find_violations(text: str) -> list[str]:
    """Return the list of forbidden stems present in ``text`` (possibly empty)."""
    violations: list[str] = []
    for label, rx in _FORBIDDEN_RE.items():
        if rx.search(text):
            violations.append(label)
    return violations


def guard_text(text: str, *, where: str = "<output>") -> str:
    """Raise if ``text`` contains a forbidden word; otherwise return it unchanged."""
    violations = find_violations(text)
    if violations:
        raise ControlledVocabularyError(
            f"Forbidden vocabulary {sorted(violations)} found in {where!r}. "
            f"Outputs may only use: {ALLOWED_PHRASES}. "
            f"Offending text: {text!r}"
        )
    return text


def _walk_strings(obj: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    """Yield (json-path, string) for every string nested in ``obj``."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            # Keys are part of the human-facing output too; scan them.
            if isinstance(key, str):
                yield f"{path}.{key} (key)", key
            yield from _walk_strings(value, f"{path}.{key}")
    elif isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            yield from _walk_strings(value, f"{path}[{i}]")


def guard_object(obj: Any) -> Any:
    """Recursively scan every string in a (JSON-serializable) object.

    Returns the object unchanged if clean; raises ``ControlledVocabularyError``
    listing every offending path otherwise.
    """
    problems: list[str] = []
    for path, text in _walk_strings(obj):
        violations = find_violations(text)
        if violations:
            problems.append(f"{path}: {sorted(violations)} in {text!r}")
    if problems:
        raise ControlledVocabularyError(
            "Controlled-vocabulary guard rejected serialization:\n  "
            + "\n  ".join(problems)
        )
    return obj
