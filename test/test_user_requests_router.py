"""Tests for app/user_requests/router.py — API endpoint tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from exceptions import QueueFullError
from user_requests.concurrency import UserRequestConcurrencyService
from user_requests.constants import RequestStatus
from user_requests.exceptions import RequestServiceSaveError
from user_requests.models import UserRequest
from user_requests.processor import RequestProcessor
from user_requests.schemas import CreateRequestBody
from user_requests.service import RequestService


@pytest.fixture
def mock_request_service():
    service = AsyncMock(spec=RequestService)
    service.save_request = AsyncMock(return_value="abc12345678901234567890123456789")
    service.get_request = AsyncMock(return_value=None)
    return service


@pytest.fixture
def mock_processor():
    return AsyncMock(spec=RequestProcessor)


@pytest.fixture
def mock_concurrency_service():
    return AsyncMock(spec=UserRequestConcurrencyService)


class TestStartupShutdown:

    async def test_startup(self, mock_processor):
        with patch(
            "user_requests.router.Provide",
            new_callable=lambda: type("FakeProvide", (), {"__getitem__": lambda s, k: k}),
        ):
            from user_requests.router import startup

            # Call startup with injected processor
            await startup(request_processor=mock_processor)
            mock_processor.start.assert_awaited_once()

    async def test_shutdown(self, mock_processor, mock_http_client):
        from user_requests.router import shutdown

        mock_notification = AsyncMock()
        mock_prompt = AsyncMock()
        await shutdown(
            request_processor=mock_processor,
            notification_client=mock_notification,
            prompt_client=mock_prompt,
        )
        mock_processor.stop.assert_awaited_once()
        mock_notification.close.assert_awaited_once()
        mock_prompt.close.assert_awaited_once()


class TestSaveRequestEndpoint:

    async def test_create_request_success(self, mock_request_service):
        from user_requests.router import save_request

        body = CreateRequestBody(user_input="Send email to test@example.com")
        result = await save_request(
            request=body,
            request_service=mock_request_service,
        )
        assert result.id == "abc12345678901234567890123456789"

    async def test_create_request_save_error(self, mock_request_service):
        from fastapi import HTTPException
        from user_requests.router import save_request

        mock_request_service.save_request.side_effect = (
            RequestServiceSaveError("fail")
        )
        body = CreateRequestBody(user_input="test")

        with pytest.raises(HTTPException) as exc_info:
            await save_request(
                request=body,
                request_service=mock_request_service,
            )
        assert exc_info.value.status_code == 500


class TestProcessRequestEndpoint:

    async def test_process_not_found(
        self, mock_request_service, mock_processor, mock_concurrency_service,
    ):
        from fastapi import HTTPException
        from user_requests.router import process_request

        mock_request_service.get_request.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await process_request(
                request_id="a" * 32,
                request_service=mock_request_service,
                request_processor=mock_processor,
                concurrency_service=mock_concurrency_service,
            )
        assert exc_info.value.status_code == 404

    async def test_process_already_sent(
        self, mock_request_service, mock_processor, mock_concurrency_service,
    ):
        from user_requests.router import process_request

        request = UserRequest(
            user_input="test", id="a" * 32, status=RequestStatus.SENT,
        )
        mock_request_service.get_request.return_value = request

        result = await process_request(
            request_id="a" * 32,
            request_service=mock_request_service,
            request_processor=mock_processor,
            concurrency_service=mock_concurrency_service,
        )
        assert result.status_code == 200

    async def test_process_already_failed(
        self, mock_request_service, mock_processor, mock_concurrency_service,
    ):
        from user_requests.router import process_request

        request = UserRequest(
            user_input="test", id="a" * 32, status=RequestStatus.FAILED,
        )
        mock_request_service.get_request.return_value = request

        result = await process_request(
            request_id="a" * 32,
            request_service=mock_request_service,
            request_processor=mock_processor,
            concurrency_service=mock_concurrency_service,
        )
        assert result.status_code == 200

    async def test_process_already_processing(
        self, mock_request_service, mock_processor, mock_concurrency_service,
    ):
        from user_requests.router import process_request

        request = UserRequest(
            user_input="test", id="a" * 32, status=RequestStatus.PROCESSING,
        )
        mock_request_service.get_request.return_value = request

        result = await process_request(
            request_id="a" * 32,
            request_service=mock_request_service,
            request_processor=mock_processor,
            concurrency_service=mock_concurrency_service,
        )
        assert result.status_code == 202

    async def test_process_queued_success(
        self, mock_request_service, mock_processor, mock_concurrency_service,
    ):
        from user_requests.router import process_request

        request = UserRequest(
            user_input="test", id="a" * 32, status=RequestStatus.QUEUED,
        )
        mock_request_service.get_request.return_value = request

        result = await process_request(
            request_id="a" * 32,
            request_service=mock_request_service,
            request_processor=mock_processor,
            concurrency_service=mock_concurrency_service,
        )
        assert result.status_code == 202
        mock_concurrency_service.add_to_queue.assert_awaited_once_with(request)

    async def test_process_queue_full(
        self, mock_request_service, mock_processor, mock_concurrency_service,
    ):
        from fastapi import HTTPException
        from user_requests.router import process_request

        request = UserRequest(
            user_input="test", id="a" * 32, status=RequestStatus.QUEUED,
        )
        mock_request_service.get_request.return_value = request
        mock_concurrency_service.add_to_queue.side_effect = QueueFullError()

        with pytest.raises(HTTPException) as exc_info:
            await process_request(
                request_id="a" * 32,
                request_service=mock_request_service,
                request_processor=mock_processor,
                concurrency_service=mock_concurrency_service,
            )
        assert exc_info.value.status_code == 429


class TestGetRequestEndpoint:

    async def test_get_found(self, mock_request_service):
        from user_requests.router import get_request

        request = UserRequest(
            user_input="test", id="a" * 32, status=RequestStatus.QUEUED,
        )
        mock_request_service.get_request.return_value = request

        result = await get_request(
            request_id="a" * 32,
            request_service=mock_request_service,
        )
        assert result is request

    async def test_get_not_found(self, mock_request_service):
        from fastapi import HTTPException
        from user_requests.router import get_request

        mock_request_service.get_request.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_request(
                request_id="a" * 32,
                request_service=mock_request_service,
            )
        assert exc_info.value.status_code == 404
