"""Custom exceptions for prompt provider interactions."""

from exceptions import GenericClientException

class PromptClientException(GenericClientException):
    """Raised when the prompt provider request cannot be completed."""

    def __init__(self, message, error_type):
        """Initializes the prompt exception.

        Args:
            message (str): Human-readable error description.
            error_type (str): Category of the underlying failure.
        """

        super().__init__(
            message,
            error_type,
            client_type="PromptClient"
        )

class PromptClientCircuitBreakerException(PromptClientException):
    """Raised when the circuit breaker is open for the prompt provider."""

    def __init__(self, message):
        """Initializes the circuit breaker exception.

        Args:
            message (str): Human-readable error description.
        """

        super().__init__(message, error_type="CircuitBreakerError")

class PromptClientRetryException(PromptClientException):
    """Raised when the prompt provider request fails after all retries."""

    def __init__(self, message):
        """Initializes the retry exception.

        Args:
            message (str): Human-readable error description.
        """

        super().__init__(message, error_type="RetryError")
