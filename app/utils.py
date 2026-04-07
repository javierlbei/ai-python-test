"""Shared logging utilities for the application."""

import logging


def get_logger() -> logging.Logger:
    return logging.getLogger('uvicorn.error')
