"""`python -m evidence_engine [config.yaml]` — run the full pipeline."""

from __future__ import annotations

import sys

from .pipeline import run


def main() -> int:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    result = run(config_path)
    claim = result["claim"]
    print("\n=== EVIDENCE OBJECT (summary) ===")
    print(f"tier      : {result['evidence_tier']}")
    print(f"statement : {claim['statement']}")
    print(f"root      : {result['artifact_root']}")
    print("Full object written to outputs/evidence_object.json")
    print("Phase-0 audit written to outputs/phase0_audit_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
