"""Tests for app/utils.py — shared logging utilities."""

import logging

from utils import get_logger


class TestGetLogger:

    def test_returns_uvicorn_error_logger(self):
        logger = get_logger()
        assert logger.name == 'uvicorn.error'

    def test_returns_logger_instance(self):
        logger = get_logger()
        assert isinstance(logger, logging.Logger)

    def test_returns_same_instance(self):
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2
