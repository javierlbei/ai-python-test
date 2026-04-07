"""Concurrency service specialized for user request queuing."""

from concurrency import ConcurrencyService
from user_requests.models import UserRequest


class UserRequestConcurrencyService(ConcurrencyService[UserRequest]):
    """Concurrency service specialized for UserRequest objects."""
    pass
