"""Custom exceptions for notification provider calls."""

from exceptions import GenericClientError


class NotificationClientCircuitBreakerError(GenericClientError):
    """Raised when the circuit breaker is open for the notification provider."""

    def __init__(self, message):
        """Initializes the circuit breaker error.

        Args:
            message (str): Human-readable error description.
        """

        super().__init__(
            message,
            error_type="CircuitBreakerError",
            client_type="NotificationClient",
        )


class NotificationClientRetryError(GenericClientError):
    """Raised when the notification provider request fails after all retries."""

    def __init__(self, message):
        """Initializes the retry error.

        Args:
            message (str): Human-readable error description.
        """

        super().__init__(
            message,
            error_type="RetryError",
            client_type="NotificationClient",
        )
