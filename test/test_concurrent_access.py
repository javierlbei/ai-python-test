"""Tests for concurrent access patterns (audit finding 10.7).

Validates that the ConcurrencyService and RequestProcessor handle
concurrent operations safely within the asyncio event loop.
"""

import asyncio

import pytest

from concurrency import ConcurrencyService
from user_requests.models import UserRequest


class TestConcurrentQueueAccess:

    async def test_concurrent_enqueue_no_duplicates(self):
        """Multiple coroutines enqueuing distinct requests concurrently."""
        service = ConcurrencyService(queue_size=100)
        requests = [
            UserRequest(user_input=f"test-{i}", id=f"req-{i}")
            for i in range(20)
        ]

        await asyncio.gather(
            *[service.add_to_queue(r) for r in requests]
        )

        assert service._queue.qsize() == 20
        assert len(service._enqueued_requests) == 20

    async def test_concurrent_enqueue_same_request(self):
        """Multiple coroutines trying to enqueue the same request."""
        service = ConcurrencyService(queue_size=100)
        request = UserRequest(user_input="test", id="req-1")

        await asyncio.gather(
            *[service.add_to_queue(request) for _ in range(10)]
        )

        assert service._queue.qsize() == 1
        assert len(service._enqueued_requests) == 1

    async def test_concurrent_complete_and_resubmit(self):
        """Complete a task and resubmit concurrently."""
        service = ConcurrencyService(queue_size=100)
        request = UserRequest(user_input="test", id="req-1")

        await service.add_to_queue(request)
        await service.get_next_request()
        await service.complete_task("req-1")

        # After completion, concurrent resubmits should result in only one
        await asyncio.gather(
            *[service.add_to_queue(request) for _ in range(5)]
        )

        assert service._queue.qsize() == 1

    async def test_producer_consumer_pattern(self):
        """Simulate producer/consumer with multiple concurrent producers."""
        service = ConcurrencyService(queue_size=50)
        processed = []

        async def producer(start, count):
            for i in range(start, start + count):
                req = UserRequest(user_input=f"msg-{i}", id=f"req-{i}")
                await service.add_to_queue(req)

        async def consumer():
            while True:
                try:
                    req = await asyncio.wait_for(
                        service.get_next_request(), timeout=0.5,
                    )
                    processed.append(req.id)
                    await service.complete_task(req.id)
                except asyncio.TimeoutError:
                    break

        # Run 3 producers concurrently, then one consumer
        await asyncio.gather(
            producer(0, 10),
            producer(10, 10),
            producer(20, 10),
        )

        await consumer()

        assert len(processed) == 30
        assert len(set(processed)) == 30  # All unique
