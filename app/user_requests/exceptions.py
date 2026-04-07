"""Custom exceptions raised by request service helpers."""


class RequestServiceSaveError(Exception):
    """Raised when a request cannot be persisted by the service."""


class InvalidJSONContentError(Exception):
    """Raised when model output does not contain valid notification JSON."""
