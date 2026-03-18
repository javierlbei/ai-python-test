"""Custom exceptions for notification provider calls."""

from exceptions import GenericClientException

class NotificationClientException(GenericClientException):
    """Raised when a notification cannot be delivered."""

    def __init__(self, message, error_type):
        """Initializes the notification exception.

        Args:
            message (str): Human-readable error description.
            error_type (str): Category of the underlying failure.
        """

        super().__init__(
            message,
            error_type,
            client_type="NotificationClient"
        )

class NotificationClientCircuitBreakerException(NotificationClientException):
    """Raised when the circuit breaker is open for the notification provider."""

    def __init__(self, message):
        """Initializes the circuit breaker exception.

        Args:
            message (str): Human-readable error description.
        """

        super().__init__(message, error_type="CircuitBreakerError")

class NotificationClientRetryException(NotificationClientException):
    """Raised when the notification provider request fails after all retries."""

    def __init__(self, message):
        """Initializes the retry exception.

        Args:
            message (str): Human-readable error description.
        """

        super().__init__(message, error_type="RetryError")
