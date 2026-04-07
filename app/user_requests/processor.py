"""Business logic for request lifecycle and asynchronous processing."""

import asyncio

from exceptions import GenericClientError, GenericRepositorySaveError
from notifications.client import NotificationClient
from prompts.client import PromptClient
from user_requests.concurrency import UserRequestConcurrencyService
from user_requests.constants import RequestStatus
from user_requests.exceptions import InvalidJSONContentError
from user_requests.models import UserRequest
from user_requests.repository import RequestRepository
from user_requests.utils import json_extractor
from utils import get_logger


class RequestProcessor:
    """Coordinates persistence, prompt generation, and notification delivery.

    Attributes:
        _concurrency_service (UserRequestConcurrencyService):
            Queue and task tracker.
        _notification_client (NotificationClient): Notification transport.
        _num_tasks (int): Number of background worker tasks.
        _processing_tasks (list[asyncio.Task]): Running processor tasks.
        _prompt_client (PromptClient): Prompt provider client.
        _requests_repository (RequestRepository): Persistence abstraction.
        _logger (logging.Logger): Service logger.
    """

    def __init__(
        self,
        concurrency_service: UserRequestConcurrencyService,
        notification_client: NotificationClient,
        requests_repository: RequestRepository,
        prompt_client: PromptClient,
        num_workers: int = 10,
    ):
        """Initializes the request service dependencies.

        Args:
            concurrency_service (UserRequestConcurrencyService):
                Queue and synchronization service for
                background processing.
            notification_client (NotificationClient): Client responsible for
                sending notifications.
            requests_repository (RequestRepository): Persistence
                abstraction for request entities.
            prompt_client (PromptClient): Client used to generate model output.
            num_workers (int): Number of background processor tasks to spawn.
        """

        self._concurrency_service = concurrency_service
        self._notification_client = notification_client
        self._num_workers = num_workers
        self._prompt_client = prompt_client
        self._requests_repository = requests_repository
        self._logger = get_logger()

        self._processing_tasks = []

    async def start(self) -> None:
        """Starts background request processor tasks."""

        for _ in range(self._num_workers):
            task = asyncio.create_task(self._request_processor())
            self._processing_tasks.append(task)

    async def stop(self) -> None:
        """Stops all active processor tasks and waits for cancellation."""

        for task in self._processing_tasks:
            task.cancel()

        await asyncio.gather(*self._processing_tasks, return_exceptions=True)

    async def _send_notification(
        self,
        request: UserRequest,
    ) -> None:
        self._logger.info('Generating LLM response for request with ID: %s',
                            request.id)
        llm_response = await self._prompt_client.generate_json(request)

        self._logger.info(
            'LLM response generated for request with ID: %s, '
            'extracting JSON content',
            request.id
        )
        extracted_data = await json_extractor(llm_response)

        self._logger.info(
            'JSON content extracted for request with ID: %s, '
            'sending notification',
            request.id
        )
        await self._notification_client.send_notification(
            extracted_data
        )

        self._logger.info('Notification sent for request with ID: %s',
                            request.id)

    async def _finalize_request(
        self,
        request: UserRequest
    ) -> None:
        try:
            await self._requests_repository.save(request)
        except GenericRepositorySaveError:
            self._logger.error(
                'Could not persist final status '
                'for request with ID: %s',
                request.id,
                exc_info=True,
            )

        await self._concurrency_service.complete_task(request.id)

    async def _process_request(
        self,
        request: UserRequest,
    ) -> None:
        task_completed_by_retry = False
        try:
            await self._send_notification(request)

            request.status = RequestStatus.SENT
        except GenericClientError as e:
            client_type = e.client_type

            self._logger.info(
                '%s sending failed for request with ID: %s',
                client_type,
                request.id
            )

            request.status = RequestStatus.FAILED
        except InvalidJSONContentError:
            self._logger.info(
                'Request with ID: %s failed '
                'due to invalid LLM response',
                request.id
            )

            request.status = RequestStatus.FAILED
        except Exception:
            self._logger.error(
                'Unhandled exception while processing '
                'request with ID: %s',
                request.id,
                exc_info=True,
            )

            request.status = RequestStatus.FAILED
        finally:
            await self._finalize_request(request)

    async def _request_processor(self) -> None:
        """Consumes queued requests and executes the processing pipeline.

        The pipeline updates request status, asks the prompt provider for
        content, validates extracted JSON, sends notifications, and stores the
        final state.

        Raises:
            asyncio.CancelledError: Raised when processor task is cancelled.
        """

        while True:
            try:
                request = await self._concurrency_service.get_next_request()

                self._logger.info('Processing request with ID: %s', request.id)

                request.status = RequestStatus.PROCESSING
                await self._requests_repository.save(request)

                await self._process_request(request)
            except asyncio.CancelledError:
                self._logger.info('Request processor cancelled')
                raise
            except Exception:
                self._logger.error(
                    'CRITICAL: Unhandled exception in processor loop',
                    exc_info=True,
                )
