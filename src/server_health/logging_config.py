"""Logging configuration for Server Health Monitor.

Sets up structured, levelled logging with optional console and file handlers.
Never logs sensitive information.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_FORMAT_VERBOSE = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
LOG_FORMAT_STANDARD = "%(asctime)s | %(levelname)-8s | %(message)s"
LOG_FORMAT_QUIET = "%(levelname)s - %(message)s"

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(
    level: str = "INFO",
    verbose: bool = False,
    quiet: bool = False,
    log_file: Path | None = None,
) -> None:
    """Configure application-wide logging.

    Args:
        level: Base log level string (e.g. "DEBUG", "INFO", "WARNING").
        verbose: If True, use a more detailed log format and set level to DEBUG.
        quiet: If True, suppress all output below WARNING.
        log_file: Optional path to write log output to a file.
    """
    if quiet:
        effective_level = logging.WARNING
        fmt = LOG_FORMAT_QUIET
    elif verbose:
        effective_level = logging.DEBUG
        fmt = LOG_FORMAT_VERBOSE
    else:
        effective_level = getattr(logging, level.upper(), logging.INFO)
        fmt = LOG_FORMAT_STANDARD

    root_logger = logging.getLogger()
    root_logger.setLevel(effective_level)

    # Remove existing handlers to avoid duplicate output during testing.
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(effective_level)
    console_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=DATE_FORMAT))
    root_logger.addHandler(console_handler)

    # Optional file handler
    if log_file is not None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(effective_level)
            file_handler.setFormatter(
                logging.Formatter(fmt=LOG_FORMAT_VERBOSE, datefmt=DATE_FORMAT)
            )
            root_logger.addHandler(file_handler)
        except OSError as exc:
            logging.warning("Could not open log file %s: %s", log_file, exc)

    # Suppress overly chatty third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("docker").setLevel(logging.WARNING)
