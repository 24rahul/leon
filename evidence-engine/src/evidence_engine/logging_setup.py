"""Structured (JSON-line) logging.

Logs are deterministic in content (no timestamps in the hashed payloads) so that
the pipeline's *outputs* remain byte-identical across runs even though the log
stream carries wall-clock times.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.args and isinstance(record.args, dict):
            payload.update(record.args)
        extra = getattr(record, "context", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, sort_keys=True, default=str)


def get_logger(name: str = "evidence_engine", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonLineFormatter())
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
