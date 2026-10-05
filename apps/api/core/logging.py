"""
ReportForge AI - Structured Logging Foundation
Provides consistent, production-oriented logging across services.
"""

import sys
import logging
from typing import Optional
from apps.api.core.config import settings


class Formatter(logging.Formatter):
    """Clean standard formatter with ISO timestamp and module path."""
    FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s"

    def __init__(self):
        super().__init__(fmt=self.FORMAT, datefmt="%Y-%m-%d %H:%M:%S")


def setup_logging():
    """Initializes root logger configuration based on settings."""
    # Ensure stdout and stderr use UTF-8 on Windows to safely handle all Unicode characters
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicate log entries
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(Formatter())
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Returns a configured logger instance for a given module."""
    return logging.getLogger(name or "reportforge")
