"""Custom exceptions for the concurrency package."""


class QueueFullException(Exception):
    """Raised when a request cannot be enqueued because the queue is at capacity."""
