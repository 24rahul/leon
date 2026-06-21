"""The causal DAG as an explicit, validated artifact.

The DAG decides which variables are confounders, mediators, or colliders — and
that choice *determines the answer*. Letting the analyst silently pick it is the
concentration of epistemic power the three-harm model warns about (Harm c). So the
graph is made explicit, hashed, and structurally checked before any estimation:

  * it must be acyclic (a DAG, not just a "graph");
  * every confounder the protocol adjusts for must be a genuine *backdoor* node —
    a common cause with a directed path into BOTH exposure and outcome;
  * the adjustment set must not condition on a descendant of the exposure (that is
    a mediator or a treatment-affected collider) or a descendant of the outcome —
    doing so opens bias paths rather than closing them.

Reachability is computed with a pure-Python DFS so this module has no graph-library
dependency and the rules are auditable in one file.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DagValidation:
    """The result of checking a DAG against a sealed protocol."""

    is_acyclic: bool
    confounders_are_backdoor: dict[str, bool]
    bad_adjustments: tuple[str, ...]  # adjustment nodes that are descendants of X or Y
    missing_nodes: tuple[str, ...]  # protocol variables absent from the DAG
    ok: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_acyclic": self.is_acyclic,
            "confounders_are_backdoor": self.confounders_are_backdoor,
            "bad_adjustments": list(self.bad_adjustments),
            "missing_nodes": list(self.missing_nodes),
            "ok": self.ok,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class CausalDAG:
    """A directed graph over named variables plus the declared adjustment set."""

    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]  # (parent, child)
    adjustment_set: tuple[str, ...]

    def __post_init__(self) -> None:
        node_set = set(self.nodes)
        for src, dst in self.edges:
            if src not in node_set or dst not in node_set:
                raise ValueError(f"Edge ({src}->{dst}) references an unknown node.")
        for a in self.adjustment_set:
            if a not in node_set:
                raise ValueError(f"Adjustment variable {a!r} is not a DAG node.")

    # --- graph primitives --------------------------------------------------
    def _children(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {n: [] for n in self.nodes}
        for src, dst in self.edges:
            out[src].append(dst)
        return out

    def is_acyclic(self) -> bool:
        """Kahn's algorithm: a DAG iff every node can be topologically removed."""
        children = self._children()
        indeg = {n: 0 for n in self.nodes}
        for _, dst in self.edges:
            indeg[dst] += 1
        queue = [n for n in self.nodes if indeg[n] == 0]
        seen = 0
        while queue:
            n = queue.pop()
            seen += 1
            for c in children[n]:
                indeg[c] -= 1
                if indeg[c] == 0:
                    queue.append(c)
        return seen == len(self.nodes)

    def descendants(self, start: str) -> set[str]:
        """All nodes reachable from `start` along directed edges (excludes start)."""
        children = self._children()
        stack = list(children.get(start, []))
        out: set[str] = set()
        while stack:
            n = stack.pop()
            if n in out:
                continue
            out.add(n)
            stack.extend(children[n])
        return out

    def ancestors(self, target: str) -> set[str]:
        """All nodes with a directed path into `target` (excludes target)."""
        parents: dict[str, list[str]] = {n: [] for n in self.nodes}
        for src, dst in self.edges:
            parents[dst].append(src)
        stack = list(parents.get(target, []))
        out: set[str] = set()
        while stack:
            n = stack.pop()
            if n in out:
                continue
            out.add(n)
            stack.extend(parents[n])
        return out

    # --- identity ----------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": list(self.nodes),
            "edges": [list(e) for e in self.edges],
            "adjustment_set": list(self.adjustment_set),
        }

    def dag_hash(self) -> str:
        """Canonical, order-independent fingerprint reviewers sign."""
        canonical = {
            "nodes": sorted(self.nodes),
            "edges": sorted([list(e) for e in self.edges]),
            "adjustment_set": sorted(self.adjustment_set),
        }
        blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    # --- the rule that matters ---------------------------------------------
    def validate(self, exposure: str, outcome: str, confounders: list[str]) -> DagValidation:
        reasons: list[str] = []

        present = set(self.nodes)
        required = [exposure, outcome, *confounders]
        missing = tuple(v for v in required if v not in present)
        if missing:
            reasons.append(f"DAG is missing protocol variables: {list(missing)}.")

        acyclic = self.is_acyclic()
        if not acyclic:
            reasons.append("DAG contains a cycle; it is not a valid causal DAG.")

        # A confounder must be a common cause: an ancestor of BOTH exposure and outcome.
        anc_x = self.ancestors(exposure) if exposure in present else set()
        anc_y = self.ancestors(outcome) if outcome in present else set()
        backdoor: dict[str, bool] = {}
        for c in confounders:
            is_bd = c in anc_x and c in anc_y
            backdoor[c] = is_bd
            if not is_bd:
                reasons.append(
                    f"Confounder {c!r} is not a backdoor node (not a common cause of "
                    f"{exposure!r} and {outcome!r}); adjusting for it is unjustified."
                )

        # The adjustment set must not condition on descendants of X (mediators /
        # treatment-affected colliders) or descendants of Y.
        desc_x = self.descendants(exposure) if exposure in present else set()
        desc_y = self.descendants(outcome) if outcome in present else set()
        bad = tuple(
            a for a in self.adjustment_set if a in desc_x or a in desc_y
        )
        for a in bad:
            kind = "exposure" if a in desc_x else "outcome"
            reasons.append(
                f"Adjustment variable {a!r} is a descendant of the {kind}; conditioning "
                "on it opens a bias path (mediator/collider)."
            )

        ok = acyclic and not missing and all(backdoor.values()) and not bad
        return DagValidation(
            is_acyclic=acyclic,
            confounders_are_backdoor=backdoor,
            bad_adjustments=bad,
            missing_nodes=missing,
            ok=ok,
            reasons=tuple(reasons),
        )


def dag_from_protocol(
    exposure: str,
    outcome: str,
    confounders: list[str],
    extra_edges: list[tuple[str, str]] | None = None,
) -> CausalDAG:
    """Build the canonical confounding DAG implied by a protocol.

    Each confounder is a common cause (confounder -> exposure, confounder -> outcome)
    and the exposure causes the outcome (exposure -> outcome). `extra_edges` lets a
    config declare additional structure (e.g. a mediator) so the gate can be tested
    against — and can reject — a mis-specified adjustment set.
    """
    nodes = {exposure, outcome, *confounders}
    edges: list[tuple[str, str]] = [(exposure, outcome)]
    for c in confounders:
        edges.append((c, exposure))
        edges.append((c, outcome))
    for src, dst in extra_edges or []:
        nodes.update({src, dst})
        edges.append((src, dst))
    # De-duplicate while preserving determinism.
    edges = sorted(set(edges))
    return CausalDAG(
        nodes=tuple(sorted(nodes)),
        edges=tuple(edges),
        adjustment_set=tuple(sorted(confounders)),
    )
