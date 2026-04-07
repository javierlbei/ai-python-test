"""Custom exceptions for provider client calls."""


class GenericClientError(Exception):
    """Raised when a request to the provider cannot be completed."""

    def __init__(self, message, error_type, client_type):
        """Initializes the error with diagnostic details.

        Args:
            message (str): Human-readable error description.
            error_type (str): Category of the underlying failure.
            client_type (str): Name of the client that raised the error.
        """

        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.client_type = client_type


class GenericRepositorySaveError(Exception):
    """Raised when the repository cannot generate a unique entity ID."""


class QueueFullError(Exception):
    """Raised when the queue is at capacity and cannot accept requests."""
