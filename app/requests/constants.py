"""Constants and enums used by the requests domain."""

from enum import Enum


class CreateNotificationBodyAttribute(str, Enum):
    """Allowed keys in sanitized notification payloads."""

    TO = 'to'
    TYPE = 'type'
    MESSAGE = 'message'

class RequestType(str, Enum):
    """Supported outbound notification channels."""

    EMAIL = 'email'
    SMS = 'sms'
    PUSH = 'push'

class RequestStatus(str, Enum):
    """Lifecycle states for request processing."""

    QUEUED = 'queued'
    PROCESSING = 'processing'
    SENT = 'sent'
    FAILED = 'failed'
