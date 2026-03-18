"""Business logic for request lifecycle and asynchronous processing."""

import asyncio
import logging

from cache import AsyncTTL

from client import GenericClient
from concurrency.service import ConcurrencyService
from exceptions import GenericClientException
from requests.constants import RequestStatus
from requests.exceptions import (
    InvalidJSONContentException,
    RequestServiceSaveException,
    InvalidPayloadException,
)
from requests.models import UserRequest
from requests.schemas import CreateRequestBody
from requests.utils import json_extractor
from repositories.exceptions import RequestRepositorySaveException
from repositories.requests import RequestRepository


class RequestService:
    """Coordinates persistence, prompt generation, and notification delivery.

    Attributes:
        _concurrency_service (ConcurrencyService): Queue and task tracker.
        _notification_client (NotificationClient): Notification transport.
        _num_tasks (int): Number of background worker tasks.
        _processing_tasks (list[asyncio.Task]): Running processor tasks.
        _prompt_client (PromptClient): Prompt provider client.
        _requests_repository (RequestRepository): Persistence abstraction.
        _logger (logging.Logger): Service logger.
    """

    def __init__(
        self,
        concurrency_service: ConcurrencyService,
        notification_client: GenericClient,
        prompt_client: GenericClient,
        num_tasks: int = 10
    ):
        """Initializes the request service dependencies.

        Args:
            concurrency_service (ConcurrencyService): Queue and synchronization
                service for background processing.
            notification_client (GenericClient): Client responsible for
                sending notifications.
            prompt_client (GenericClient): Client used to generate model output.
            num_tasks (int): Number of background processor tasks to spawn.
        """

        self._concurrency_service = concurrency_service
        self._notification_client = notification_client
        self._num_tasks = num_tasks
        self._processing_tasks = []
        self._prompt_client = prompt_client
        self._requests_repository = RequestRepository()
        self._logger = logging.getLogger('uvicorn.error')

    # ---------- CRUD OPERATIONS ----------


    async def save_request(self, request: CreateRequestBody | UserRequest) -> str:
        """Persists a new or existing request.

        Accepts either API payload schema objects or already-built domain
        objects and writes them through the repository.

        Args:
            request (CreateRequestBody | UserRequest): Request content to
                persist.

        Returns:
            str: ID of the saved request.

        Raises:
            InvalidPayloadException: If the request object is not a recognised
                type.
            RequestServiceSaveException: If the repository cannot save the
                request.
        """

        if isinstance(request, CreateRequestBody):
            request_to_save = UserRequest(request.user_input)
        elif isinstance(request, UserRequest):
            request_to_save = request
        else:
            raise InvalidPayloadException()

        try:
            saved_request_id = await self._requests_repository.save(request_to_save)
            return saved_request_id
        except RequestRepositorySaveException as exc:
            raise RequestServiceSaveException() from exc

    @AsyncTTL(time_to_live=600)
    async def get_request(self, request_id: str) -> UserRequest | None:
        """Retrieves a request by ID.

        Args:
            request_id (str): Request identifier.

        Returns:
            UserRequest | None: Stored request when found, otherwise ``None``.
        """

        return await self._requests_repository.get_request_by_id(request_id)

    # ---------- USER PROMPT PROCESSING ----------


    async def start(self):
        """Starts background request processor tasks."""

        for _ in range(self._num_tasks):
            task = asyncio.create_task(self._request_processor())
            self._processing_tasks.append(task)

    async def stop(self):
        """Stops all active processor tasks and waits for cancellation."""

        for task in self._processing_tasks:
            task.cancel()

        await asyncio.gather(*self._processing_tasks, return_exceptions=True)

    async def _request_processor(self):
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

                try:
                    self._logger.info(
                        'Generating LLM response for request with ID: %s',
                        request.id
                    )
                    llm_response = await self._prompt_client.generate_json(
                        request
                    )


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


                    self._logger.info(
                        'Notification sent for request with ID: %s',
                        request.id
                    )
                    request.status = RequestStatus.SENT
                except GenericClientException as e:
                    client_type = e.client_type

                    self._logger.info(
                        '%s sending failed for request with ID: %s',
                        client_type,
                        request.id
                    )

                    request.status = RequestStatus.QUEUED
                except InvalidJSONContentException:
                    self._logger.info(
                        'Request with ID: %s failed due to invalid LLM response',
                        request.id
                    )
                    request.status = RequestStatus.FAILED
                except Exception:
                    self._logger.error(
                        'Unhandled exception while processing request with ID: %s',
                        request.id,
                        exc_info=True,
                    )
                    request.status = RequestStatus.FAILED
                finally:
                    try:
                        await self._requests_repository.save(request)
                    except RequestRepositorySaveException:
                        self._logger.error(
                            'Could not persist final status for request with ID: %s',
                            request.id,
                            exc_info=True,
                        )

                    await self._concurrency_service.complete_task(request.id)
            except asyncio.CancelledError:
                self._logger.info('Request processor cancelled')
                raise
            except Exception:
                self._logger.error(
                    'CRITICAL: Unhandled exception in processor loop',
                    exc_info=True,
                )
