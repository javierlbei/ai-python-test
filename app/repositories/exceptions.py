"""Custom exceptions for repository operations."""


class RequestRepositorySaveException(Exception):
    """Raised when the repository cannot generate a unique request ID."""
