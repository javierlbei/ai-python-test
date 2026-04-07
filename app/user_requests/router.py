"""API routes for creating, processing, and retrieving requests."""

from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, HTTPException, Path, Response, status

from dependencies import Container
from exceptions import QueueFullError
from user_requests.concurrency import UserRequestConcurrencyService
from user_requests.constants import RequestStatus
from user_requests.exceptions import RequestServiceSaveError
from user_requests.models import UserRequest
from user_requests.processor import RequestProcessor
from user_requests.schemas import (
    CreateRequestBody,
    CreateRequestResponse,
    GetRequestResponse,
)
from user_requests.service import RequestService
from utils import get_logger

router = APIRouter(prefix='/v1/requests')
_logger = get_logger()


@inject
async def startup(
    request_processor: RequestProcessor = Provide[
        Container.request_processor
    ],
):
    await request_processor.start()


@inject
async def shutdown(
    request_processor: RequestProcessor = Provide[
        Container.request_processor
    ],
    notification_client = Provide[Container.notification_client],
    prompt_client = Provide[Container.prompt_client],
):
    await request_processor.stop()
    await notification_client.close()
    await prompt_client.close()


@router.post(
    '',
    status_code=status.HTTP_201_CREATED,
    response_model=CreateRequestResponse,
)
@inject
async def save_request(
    request: CreateRequestBody,
    request_service: Annotated[
        RequestService,
        Depends(Provide[Container.request_service]),
    ],
) -> CreateRequestResponse:
    """Creates a new request and persists it.

    Args:
        request (CreateRequestBody): Payload containing user input.

    Returns:
        CreateRequestResponse: Response containing the created request ID.

    Raises:
        HTTPException: Raised with status 500 when request persistence fails.
    """

    try:
        _logger.info('Creating request')
        created_request_id = await request_service.save_request(request)

        return CreateRequestResponse(id=created_request_id)
    except RequestServiceSaveError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=('The service could not save the request. '
                    'Please try again later.')
        ) from exc


@router.post(
    '/{request_id}/process',
    status_code=status.HTTP_202_ACCEPTED,
)
@inject
async def process_request(
    request_id: Annotated[str, Path(pattern=r'^[a-f0-9]{32}$')],
    request_service: Annotated[
        RequestService,
        Depends(Provide[Container.request_service]),
    ],
    request_processor: Annotated[
        RequestProcessor,
        Depends(Provide[Container.request_processor]),
    ],
    concurrency_service: Annotated[
        UserRequestConcurrencyService,
        Depends(Provide[Container.concurrency_service]),
    ],
) -> Response:
    """Enqueues an existing request for asynchronous processing.

    Args:
        request_id (str): Identifier of the request to process.

    Returns:
        Response: Empty response with status 200 when already sent or failed,
            or 202 when processing or newly queued.

    Raises:
        HTTPException: Raised with status 404 when the request is not found,
            or status 429 when the processing queue is full.
    """

    user_request = await request_service.get_request(request_id)

    if user_request is None:
        _logger.warning('Request with ID %s was not found', request_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Request not found',
        )

    if user_request.status in (RequestStatus.SENT, RequestStatus.FAILED):
        _logger.info('Request %s already sent or failed', user_request.id)
        return Response()

    if user_request.status == RequestStatus.PROCESSING:
        _logger.info('Request %s already processing', user_request.id)
        return Response(status_code=status.HTTP_202_ACCEPTED)

    try:
        _logger.info('Queueing request %s for processing', user_request.id)
        await concurrency_service.add_to_queue(user_request)
        return Response(status_code=status.HTTP_202_ACCEPTED)
    except QueueFullError as exc:
        _logger.warning(
            'Queue full while processing request %s',
            user_request.id,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail='You are being rate-limited. '
                   'Please try again later.',
        ) from exc


@router.get(
    '/{request_id}',
    status_code=status.HTTP_200_OK,
    response_model=GetRequestResponse,
)
@inject
async def get_request(
    request_id: Annotated[str, Path(pattern=r'^[a-f0-9]{32}$')],
    request_service: Annotated[
        RequestService,
        Depends(Provide[Container.request_service]),
    ],
) -> UserRequest:
    """Retrieves a request by ID.

    Args:
        request_id (str): Identifier of the request to retrieve.

    Returns:
        UserRequest: Request entity serialized by the response model.

    Raises:
        HTTPException: Raised with status 404 when the request is not found.
    """

    user_request = await request_service.get_request(request_id)

    if user_request is None:
        _logger.warning('Request with ID %s was not found', request_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Request not found',
        )

    _logger.debug('Returning request %s', user_request.id)

    return user_request
