"""Unit tests for logging configuration."""

from __future__ import annotations

import logging
from pathlib import Path

from server_health.logging_config import setup_logging


def test_setup_logging_defaults():
    setup_logging(level="INFO")
    logger = logging.getLogger("test_default")
    assert logger.getEffectiveLevel() == logging.INFO


def test_setup_logging_verbose():
    setup_logging(verbose=True)
    root = logging.getLogger()
    assert root.getEffectiveLevel() == logging.DEBUG


def test_setup_logging_quiet():
    setup_logging(quiet=True)
    root = logging.getLogger()
    assert root.getEffectiveLevel() == logging.WARNING


def test_setup_logging_file(tmp_path: Path):
    log_file = tmp_path / "test.log"
    setup_logging(level="INFO", log_file=log_file)
    logger = logging.getLogger("test_file")
    logger.info("Test message to file")
    assert log_file.exists()
