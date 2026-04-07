"""Tests for app/user_requests/repository.py — specialized request repo."""

from repository import GenericRepository
from user_requests.models import UserRequest
from user_requests.repository import RequestRepository


class TestRequestRepository:

    def test_is_generic_repository(self):
        assert issubclass(RequestRepository, GenericRepository)

    async def test_save_and_get(self):
        repo = RequestRepository()
        request = UserRequest(user_input="test")
        request_id = await repo.save(request)

        result = await repo.get(request_id)
        assert result is request
        assert result.user_input == "test"
