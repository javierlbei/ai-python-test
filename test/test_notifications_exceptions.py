"""Tests for app/notifications/exceptions.py."""

from exceptions import GenericClientError
from notifications.exceptions import (
    NotificationClientCircuitBreakerError,
    NotificationClientRetryError,
)


class TestNotificationClientRetryError:

    def test_inherits_generic_client_error(self):
        assert issubclass(NotificationClientRetryError, GenericClientError)

    def test_attributes(self):
        exc = NotificationClientRetryError("retry failed")
        assert exc.message == "retry failed"
        assert exc.error_type == "RetryError"
        assert exc.client_type == "NotificationClient"


class TestNotificationClientCircuitBreakerError:

    def test_inherits_generic_client_error(self):
        assert issubclass(
            NotificationClientCircuitBreakerError, GenericClientError,
        )

    def test_attributes(self):
        exc = NotificationClientCircuitBreakerError("circuit open")
        assert exc.message == "circuit open"
        assert exc.error_type == "CircuitBreakerError"
        assert exc.client_type == "NotificationClient"
