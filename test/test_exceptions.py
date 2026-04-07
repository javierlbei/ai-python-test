"""Tests for app/exceptions.py — base exception classes."""

from exceptions import GenericClientError, GenericRepositorySaveError, QueueFullError


class TestGenericClientError:

    def test_is_exception(self):
        assert issubclass(GenericClientError, Exception)

    def test_attributes(self):
        exc = GenericClientError("msg", "retry", "TestClient")
        assert exc.message == "msg"
        assert exc.error_type == "retry"
        assert exc.client_type == "TestClient"

    def test_can_raise_and_catch(self):
        with pytest.raises(GenericClientError):
            raise GenericClientError("fail", "err", "client")


class TestGenericRepositorySaveError:

    def test_is_exception(self):
        assert issubclass(GenericRepositorySaveError, Exception)

    def test_can_raise(self):
        with pytest.raises(GenericRepositorySaveError):
            raise GenericRepositorySaveError()


class TestQueueFullError:

    def test_is_exception(self):
        assert issubclass(QueueFullError, Exception)

    def test_can_raise_and_catch(self):
        with pytest.raises(QueueFullError):
            raise QueueFullError()


import pytest
