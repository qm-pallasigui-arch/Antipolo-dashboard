"""
Central logging setup.

The dashboard already shows data-quality and model-fit warnings directly in
the UI (that's for the end user). This module is the separate, complementary
channel for the *operator/developer* audience: anyone running this on a server
needs these events in their logs even if no one is looking at the browser tab
at that moment. Two different audiences, two different channels -- the UI
warnings are not a substitute for this, and vice versa.

Usage in any module:
    from dashboard.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("...")
"""

import logging
import os
import sys

_CONFIGURED = False


def configure_logging() -> None:
    """Idempotent: safe to call multiple times (e.g. once from app.py, and
    again if a WSGI server imports this module separately)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root = logging.getLogger("dashboard")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
