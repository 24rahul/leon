"""Scale-safe measurement units in the type system.

Both the natural risk-ratio scale and the log scale flow through the estimator,
and confusing them is a silent, catastrophic bug (an E-value computed on a log-RR,
or a calibration applied to an RR, is nonsense that still "runs"). `NewType` makes
the scale part of the static type: `mypy` rejects passing a `LogRiskRatio` where a
`RiskRatio` is expected, even though both are `float` at runtime (zero overhead).
"""

from __future__ import annotations

from typing import NewType

RiskRatio = NewType("RiskRatio", float)        # natural scale, null = 1.0
LogRiskRatio = NewType("LogRiskRatio", float)  # log scale, null = 0.0
