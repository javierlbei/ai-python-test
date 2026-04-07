"""Tests for app/user_requests/processor.py — background request processor."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from exceptions import GenericClientError, GenericRepositorySaveError
from notifications.client import NotificationClient
from prompts.client import PromptClient
from user_requests.concurrency import UserRequestConcurrencyService
from user_requests.constants import RequestStatus
from user_requests.exceptions import InvalidJSONContentError
from user_requests.models import UserRequest
from user_requests.processor import RequestProcessor
from user_requests.repository import RequestRepository


@pytest.fixture
def mock_concurrency():
    return AsyncMock(spec=UserRequestConcurrencyService)


@pytest.fixture
def mock_notification_client():
    return AsyncMock(spec=NotificationClient)


@pytest.fixture
def mock_prompt_client():
    return AsyncMock(spec=PromptClient)


@pytest.fixture
def mock_requests_repo():
    return AsyncMock(spec=RequestRepository)


@pytest.fixture
def processor(
    mock_concurrency,
    mock_notification_client,
    mock_requests_repo,
    mock_prompt_client,
):
    return RequestProcessor(
        concurrency_service=mock_concurrency,
        notification_client=mock_notification_client,
        requests_repository=mock_requests_repo,
        prompt_client=mock_prompt_client,
        num_workers=2,
    )


class TestProcessorStartStop:

    async def test_start_creates_tasks(self, processor):
        await processor.start()
        assert len(processor._processing_tasks) == 2
        await processor.stop()

    async def test_stop_cancels_tasks(self, processor):
        await processor.start()
        tasks = list(processor._processing_tasks)
        await processor.stop()

        for task in tasks:
            assert task.cancelled() or task.done()


class TestProcessRequest:

    async def test_success_pipeline(
        self, processor, mock_prompt_client, mock_notification_client,
        mock_requests_repo, mock_concurrency,
    ):
        request = UserRequest(user_input="send email", id="req-1")
        mock_prompt_client.generate_json.return_value = {
            "user_input": "send email",
            "llm_response": '{"to":"a@b.com","type":"email","message":"hi"}',
        }

        with patch(
            "user_requests.processor.json_extractor",
            new_callable=AsyncMock,
        ) as mock_extractor:
            mock_extractor.return_value = {
                "to": "a@b.com", "type": "email", "message": "hi",
            }

            await processor._process_request(request)

        assert request.status == RequestStatus.SENT
        mock_notification_client.send_notification.assert_awaited_once()
        mock_requests_repo.save.assert_awaited()
        mock_concurrency.complete_task.assert_awaited_once_with("req-1")

    async def test_generic_client_error_marks_failed(
        self, processor, mock_concurrency, mock_prompt_client,
        mock_requests_repo,
    ):
        request = UserRequest(user_input="test", id="req-1")
        mock_prompt_client.generate_json.side_effect = GenericClientError(
            "fail", "RetryError", "PromptClient",
        )

        await processor._process_request(request)

        assert request.status == RequestStatus.FAILED
        mock_requests_repo.save.assert_awaited()
        mock_concurrency.complete_task.assert_awaited_once_with("req-1")

    async def test_invalid_json_error_marks_failed(
        self, processor, mock_concurrency, mock_prompt_client,
        mock_requests_repo,
    ):
        request = UserRequest(user_input="test", id="req-1")
        mock_prompt_client.generate_json.return_value = {
            "user_input": "test",
            "llm_response": "not json",
        }

        with patch(
            "user_requests.processor.json_extractor",
            new_callable=AsyncMock,
            side_effect=InvalidJSONContentError(),
        ):
            await processor._process_request(request)

        assert request.status == RequestStatus.FAILED
        mock_concurrency.complete_task.assert_awaited_once_with("req-1")

    async def test_unexpected_error_marks_failed(
        self, processor, mock_concurrency, mock_prompt_client,
        mock_requests_repo,
    ):
        request = UserRequest(user_input="test", id="req-1")
        mock_prompt_client.generate_json.side_effect = RuntimeError("boom")

        await processor._process_request(request)

        assert request.status == RequestStatus.FAILED
        mock_requests_repo.save.assert_awaited()
        mock_concurrency.complete_task.assert_awaited_once_with("req-1")

    async def test_finalize_handles_save_error(
        self, processor, mock_requests_repo, mock_concurrency,
    ):
        request = UserRequest(user_input="test", id="req-1")

        call_count = 0

        async def save_side_effect(entity):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise GenericRepositorySaveError()
            return entity.id

        mock_requests_repo.save = AsyncMock(side_effect=save_side_effect)

        with patch(
            "user_requests.processor.json_extractor",
            new_callable=AsyncMock,
        ) as mock_extractor:
            mock_extractor.return_value = {
                "to": "a@b.com", "type": "email", "message": "hi",
            }

            await processor._process_request(request)

        mock_concurrency.complete_task.assert_awaited()


class TestRequestProcessorLoop:

    async def test_processes_then_stops_on_cancel(
        self, processor, mock_concurrency, mock_prompt_client,
        mock_notification_client, mock_requests_repo,
    ):
        request = UserRequest(user_input="test", id="req-1")
        mock_concurrency.get_next_request = AsyncMock(
            side_effect=[request, asyncio.CancelledError()],
        )
        mock_prompt_client.generate_json.return_value = {
            "user_input": "test",
            "llm_response": '{"to":"a@b.com","type":"email","message":"hi"}',
        }

        with patch(
            "user_requests.processor.json_extractor",
            new_callable=AsyncMock,
        ) as mock_extractor:
            mock_extractor.return_value = {
                "to": "a@b.com", "type": "email", "message": "hi",
            }

            with pytest.raises(asyncio.CancelledError):
                await processor._request_processor()

        assert request.status == RequestStatus.SENT

    async def test_outer_exception_does_not_crash_loop(
        self, processor, mock_concurrency, mock_requests_repo,
    ):
        request = UserRequest(user_input="test", id="req-1")

        call_count = 0

        async def get_next_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return request
            raise asyncio.CancelledError()

        mock_concurrency.get_next_request = AsyncMock(
            side_effect=get_next_side_effect,
        )
        mock_requests_repo.save = AsyncMock(
            side_effect=Exception("unexpected"),
        )

        with pytest.raises(asyncio.CancelledError):
            await processor._request_processor()
