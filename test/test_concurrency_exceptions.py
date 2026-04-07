"""Tests for QueueFullError from app/exceptions.py (concurrency errors)."""

import pytest

from exceptions import QueueFullError


class TestQueueFullError:

    def test_is_exception(self):
        assert issubclass(QueueFullError, Exception)

    def test_can_raise_and_catch(self):
        with pytest.raises(QueueFullError):
            raise QueueFullError()
