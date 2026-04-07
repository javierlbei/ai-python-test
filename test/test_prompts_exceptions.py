"""Tests for app/prompts/exceptions.py."""

from exceptions import GenericClientError
from prompts.exceptions import (
    PromptClientCircuitBreakerError,
    PromptClientRetryError,
)


class TestPromptClientRetryError:

    def test_inherits_generic_client_error(self):
        assert issubclass(PromptClientRetryError, GenericClientError)

    def test_attributes(self):
        exc = PromptClientRetryError("retry failed")
        assert exc.message == "retry failed"
        assert exc.error_type == "RetryError"
        assert exc.client_type == "PromptClient"


class TestPromptClientCircuitBreakerError:

    def test_inherits_generic_client_error(self):
        assert issubclass(
            PromptClientCircuitBreakerError, GenericClientError,
        )

    def test_attributes(self):
        exc = PromptClientCircuitBreakerError("circuit open")
        assert exc.message == "circuit open"
        assert exc.error_type == "CircuitBreakerError"
        assert exc.client_type == "PromptClient"
