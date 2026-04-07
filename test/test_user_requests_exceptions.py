"""Tests for app/user_requests/exceptions.py."""

import pytest

from user_requests.exceptions import InvalidJSONContentError, RequestServiceSaveError


class TestRequestServiceSaveError:

    def test_is_exception(self):
        assert issubclass(RequestServiceSaveError, Exception)

    def test_can_raise(self):
        with pytest.raises(RequestServiceSaveError):
            raise RequestServiceSaveError()


class TestInvalidJSONContentError:

    def test_is_exception(self):
        assert issubclass(InvalidJSONContentError, Exception)

    def test_can_raise(self):
        with pytest.raises(InvalidJSONContentError):
            raise InvalidJSONContentError()
