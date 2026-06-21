"""Run the validation study and write a report + plot.

    python -m evidence_engine.validation [--reps N] [--n N] [--fast]

Exit code is non-zero if the overall verdict fails, so this doubles as a CI gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .dgp import DGP
from .report import plot_operating_characteristics, render_markdown
from .simulation import calibration_study, judge, recovery_study


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the causal pipeline.")
    parser.add_argument("--reps", type=int, default=300, help="replications per scenario")
    parser.add_argument("--n", type=int, default=3000, help="patients per replication")
    parser.add_argument("--out", type=Path, default=Path("outputs"))
    parser.add_argument("--fast", action="store_true", help="quick run (reps=60, fewer datasets)")
    args = parser.parse_args(argv)

    reps = 60 if args.fast else args.reps
    cal_datasets = 4 if args.fast else 10

    print(f"Running recovery study (n={args.n}, reps={reps})...", flush=True)
    recovery = recovery_study(DGP(), n=args.n, reps=reps)
    print("Running calibration study...", flush=True)
    calibration = calibration_study(datasets=cal_datasets)
    verdict = judge(recovery, calibration)

    md = render_markdown(recovery, calibration, verdict, n=args.n, reps=reps)
    (args.out / "validation_report.md").write_text(md, encoding="utf-8")
    plot_operating_characteristics(recovery, calibration, args.out / "validation_plots.png")
    (args.out / "validation_metrics.json").write_text(
        json.dumps(
            {
                "overall_pass": verdict.passed,
                "recovery": [s.to_dict() for s in recovery],
                "calibration": calibration.to_dict(),
                "verdict": verdict.to_dict(),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    badge = "PASS" if verdict.passed else "FAIL"
    print(f"\n=== VALIDATION {badge} ===")
    for c in verdict.checks:
        print(f"  [{'x' if c['pass'] else ' '}] {c['check']}: {c['detail']}")
    print(f"\nReport:  {args.out / 'validation_report.md'}")
    print(f"Plots:   {args.out / 'validation_plots.png'}")
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    sys.exit(main())
