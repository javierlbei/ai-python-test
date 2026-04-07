"""Tests for app/user_requests/service.py — request business logic."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from user_requests.models import UserRequest
from user_requests.repository import RequestRepository
from user_requests.schemas import CreateRequestBody
from user_requests.service import RequestService


class TestRequestService:

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock(spec=RequestRepository)
        repo.save = AsyncMock(return_value="generated-id")
        repo.get = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def service(self, mock_repo):
        return RequestService(requests_repository=mock_repo)

    async def test_save_request(self, service, mock_repo):
        body = CreateRequestBody(user_input="Send email to test@example.com")
        result = await service.save_request(body)

        assert result == "generated-id"
        mock_repo.save.assert_awaited_once()
        saved_entity = mock_repo.save.call_args[0][0]
        assert isinstance(saved_entity, UserRequest)
        assert saved_entity.user_input == "Send email to test@example.com"

    async def test_get_request_found(self, service, mock_repo):
        expected = UserRequest(user_input="test", id="abc")
        mock_repo.get.return_value = expected

        result = await service.get_request("abc")
        assert result is expected
        mock_repo.get.assert_awaited_once_with("abc")

    async def test_get_request_not_found(self, service, mock_repo):
        mock_repo.get.return_value = None

        result = await service.get_request("nonexistent")
        assert result is None
