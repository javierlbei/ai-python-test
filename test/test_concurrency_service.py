"""Tests for app/concurrency.py — bounded async queue service."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from concurrency import ConcurrencyService
from exceptions import QueueFullError
from user_requests.constants import RequestStatus
from user_requests.models import UserRequest


class TestConcurrencyServiceInit:

    def test_default_unbounded(self):
        service = ConcurrencyService()
        assert service._queue.maxsize == 0

    def test_bounded_queue(self):
        service = ConcurrencyService(queue_size=5)
        assert service._queue.maxsize == 5


class TestAddToQueue:

    async def test_add_request(self):
        service = ConcurrencyService()
        request = UserRequest(user_input="test", id="req-1")

        await service.add_to_queue(request)

        assert "req-1" in service._enqueued_requests
        assert service._queue.qsize() == 1

    async def test_duplicate_skipped(self):
        service = ConcurrencyService()
        request = UserRequest(user_input="test", id="req-1")

        await service.add_to_queue(request)
        await service.add_to_queue(request)

        assert service._queue.qsize() == 1

    async def test_queue_full_raises(self):
        service = ConcurrencyService(queue_size=1)
        req1 = UserRequest(user_input="first", id="req-1")
        req2 = UserRequest(user_input="second", id="req-2")

        await service.add_to_queue(req1)

        with pytest.raises(QueueFullError):
            await service.add_to_queue(req2)


class TestGetNextRequest:

    async def test_fifo_order(self):
        service = ConcurrencyService()
        req1 = UserRequest(user_input="first", id="req-1")
        req2 = UserRequest(user_input="second", id="req-2")

        await service.add_to_queue(req1)
        await service.add_to_queue(req2)

        result1 = await service.get_next_request()
        result2 = await service.get_next_request()

        assert result1.id == "req-1"
        assert result2.id == "req-2"


class TestCompleteTask:

    async def test_removes_from_enqueued(self):
        service = ConcurrencyService()
        request = UserRequest(user_input="test", id="req-1")

        await service.add_to_queue(request)
        await service.get_next_request()
        await service.complete_task("req-1")

        assert "req-1" not in service._enqueued_requests

    async def test_complete_unknown_id(self):
        service = ConcurrencyService()
        request = UserRequest(user_input="test", id="req-1")

        await service.add_to_queue(request)
        await service.get_next_request()

        # Complete with a different ID — logs warning but no error
        await service.complete_task("unknown-id")

    async def test_can_resubmit_after_complete(self):
        service = ConcurrencyService()
        request = UserRequest(user_input="test", id="req-1")

        await service.add_to_queue(request)
        await service.get_next_request()
        await service.complete_task("req-1")

        # Should be able to resubmit after completion
        await service.add_to_queue(request)
        assert "req-1" in service._enqueued_requests


