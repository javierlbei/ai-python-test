"""Custom exceptions raised by request service helpers."""


class RequestServiceSaveException(Exception):
    """Raised when a request cannot be persisted by the service."""


class InvalidJSONContentException(Exception):
    """Raised when model output does not contain valid notification JSON."""


class InvalidPayloadException(Exception):
    """Raised when a notification payload is missing required fields or has invalid values."""
