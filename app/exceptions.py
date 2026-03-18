"""Custom exceptions for provider client calls."""


class GenericClientException(Exception):
    """Raised when a request to the provider cannot be completed."""

    def __init__(self, message, error_type, client_type):
        """Initializes the exception with diagnostic details.

        Args:
            message (str): Human-readable error description.
            error_type (str): Category of the underlying failure.
            client_type (str): Name of the client that raised the error.
        """

        self.message = message
        self.error_type = error_type
        self.client_type = client_type
