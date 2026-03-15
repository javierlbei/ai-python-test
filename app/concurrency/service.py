"""Concurrency service for managing a bounded async request queue.

Provides ConcurrencyService, which serialises incoming UserRequest objects
into an asyncio.Queue, prevents duplicate submissions, and exposes helpers
for consumers to retrieve and acknowledge processed requests.
"""

import logging
import asyncio

from concurrency.exceptions import QueueFullException
from requests.models import UserRequest

class ConcurrencyService:
    """Manages a bounded async queue of pending user requests.

    Ensures each request is processed at most once at a time by tracking
    enqueued request IDs under a lock before admission.

    Attributes:
        _queue (asyncio.Queue): Bounded async FIFO queue holding pending requests.
        _lock (asyncio.Lock): Ensures exclusive access when reading/writing
            the enqueued-request set and performing queue operations.
        _enqueued_requests (set[str]): IDs of requests currently in the queue,
            used to prevent duplicate submissions.
    """

    def __init__(self, queue_size: int = 0):
        """Creates a new ConcurrencyService with a bounded async queue.

        Args:
            queue_size (int): Maximum number of requests the queue can hold
                simultaneously. ``0`` means unbounded (default: ``0``).
        """

        self._queue = asyncio.Queue(queue_size)
        self._lock = asyncio.Lock()
        self._enqueued_requests = set()
        self._logger = logging.getLogger('uvicorn.error')

    async def add_to_queue(self, request: UserRequest):
        """Adds a request to the queue if it is not already enqueued.

        Acquires the internal lock to atomically check for duplicates and
        insert the request. If the same request ID is already present the
        call is a no-op and a warning is logged. If the queue has reached
        its capacity a ``QueueFullException`` is raised.

        Args:
            request (UserRequest): The request to enqueue.

        Raises:
            QueueFullException: Raised when the queue is at full capacity and
                cannot accept additional requests.
        """

        async with self._lock:
            # Protects the same request from being processed multiple times
            # in a short space of time

            if request.id in self._enqueued_requests:
                self._logger.warning(
                    'Request with ID: %s is already enqueued, skipping',
                    request.id,
                )
                return

            try:
                self._queue.put_nowait(request)
                self._logger.info(
                    'Request with ID: %s added to the queue', request.id
                )
            except asyncio.QueueFull:
                self._logger.error(
                    'Queue is full, cannot add request with ID: %s', request.id
                )
                raise QueueFullException()

            self._enqueued_requests.add(request.id)

    async def get_next_request(self):
        """Retrieves and removes the next request from the queue.

        Suspends the caller until a request becomes available if the queue
        is currently empty.

        Returns:
            UserRequest: The next request in FIFO order.
        """

        return await self._queue.get()

    async def complete_task(self, request_id: str):
        """Marks a previously dequeued request as fully processed.

        Acquires the internal lock, signals ``asyncio.Queue.task_done`` so
        that any ``join()`` waiters are notified, and removes the request ID
        from the tracking set so the same request can be re-submitted in the
        future if needed.

        Args:
            request_id (str): The ID of the request to mark as complete.
        """

        async with self._lock:
            self._queue.task_done()

            if request_id in self._enqueued_requests:
                self._enqueued_requests.remove(request_id)
                self._logger.info('Request with ID: %s completed and removed '
                                  'from the queue', request_id)
                return

            self._logger.warning(
                'Request with ID: %s was completed but not found in the queue set',
                request_id,
            )
