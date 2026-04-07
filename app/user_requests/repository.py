"""In-memory repository for request persistence."""

from repository import GenericRepository
from user_requests.models import UserRequest


class RequestRepository(GenericRepository[UserRequest]):
    """In-memory repository for ``UserRequest`` entities."""
    pass
