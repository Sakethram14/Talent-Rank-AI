"""
Structured logging for TalentRank AI.

Provides a consistent logging format across all modules with both
console and file output support.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_initialized_loggers: dict[str, logging.Logger] = {}


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    Get or create a named logger with consistent formatting.

    Args:
        name: Logger name, typically the module name (e.g., 'data.parser').
        level: Logging level (default: INFO).
        log_file: Optional file path for log output.

    Returns:
        Configured logger instance.
    """
    if name in _initialized_loggers:
        return _initialized_loggers[name]

    logger = logging.getLogger(f"talentrank.{name}")
    logger.setLevel(level)
    logger.propagate = False

    # Console handler
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(
            logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
        )
        logger.addHandler(console_handler)

        # File handler (optional)
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(
                logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
            )
            logger.addHandler(file_handler)

    _initialized_loggers[name] = logger
    return logger
