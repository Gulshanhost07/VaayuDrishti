
from __future__ import annotations

import logging
import sys

from shared.config import settings


def setup_logging(name: str | None = None) -> logging.Logger:
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":%(message)s}',
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
    return logging.getLogger(name or "vaayu")


def q(msg: str) -> str:
    return '"' + msg.replace('"', "'").replace("\n", " ") + '"'
