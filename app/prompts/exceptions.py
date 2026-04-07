"""Custom exceptions for prompt provider interactions."""

from exceptions import GenericClientError


class PromptClientCircuitBreakerError(GenericClientError):
    """Raised when the circuit breaker is open for the prompt provider."""

    def __init__(self, message):
        """Initializes the circuit breaker error.

        Args:
            message (str): Human-readable error description.
        """

        super().__init__(
            message,
            error_type="CircuitBreakerError",
            client_type="PromptClient",
        )


class PromptClientRetryError(GenericClientError):
    """Raised when the prompt provider request fails after all retries."""

    def __init__(self, message):
        """Initializes the retry error.

        Args:
            message (str): Human-readable error description.
        """

        super().__init__(
            message,
            error_type="RetryError",
            client_type="PromptClient",
        )
