"""API routes for creating, processing, and retrieving requests."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status

from concurrency.exceptions import QueueFullException
from requests.constants import RequestStatus
from requests.dependencies import get_concurrency_service, get_request_service
from requests.models import UserRequest
from requests.exceptions import InvalidPayloadException, RequestServiceSaveException
from requests.schemas import CreateRequestBody, CreateRequestResponse, GetRequestResponse


_logger = logging.getLogger('uvicorn.error')

router = APIRouter(prefix='/v1/requests')


@router.post(
    '',
    status_code=status.HTTP_201_CREATED,
    response_model=CreateRequestResponse,
)
async def save_request(
    request: CreateRequestBody,
    request_service=Depends(get_request_service),
) -> CreateRequestResponse:
    """Creates a new request and persists it.

    Args:
        request (CreateRequestBody): Payload containing user input.
        request_service (RequestService): Service used for persistence.

    Returns:
        CreateRequestResponse: Response containing the created request ID.

    Raises:
        HTTPException: Raised with status 500 when request persistence fails.
    """

    try:
        _logger.info('Creating request')
        created_request_id = await request_service.save_request(request)

        return CreateRequestResponse(id=created_request_id)
    except RequestServiceSaveException:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=('The service could not save the request. '
                    'Please try again later.')
        )
    except InvalidPayloadException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=('Invalid request payload. Please ensure the input is valid.')
        )

@router.post('/{request_id}/process', status_code=status.HTTP_202_ACCEPTED)
async def process_request(
    request_id: str,
    request_service=Depends(get_request_service),
    concurrency_service=Depends(get_concurrency_service),
) -> Response:
    """Enqueues an existing request for asynchronous processing.

    Args:
        user_request (UserRequest): Existing request resolved by dependency.
        concurrency_service (ConcurrencyService): Queue manager for background
            processing.

    Returns:
        Response: Empty response with status code 200 or 202 depending on the
            request state.

    Raises:
        HTTPException: Raised with status 429 when the processing queue is
            full.
    """

    user_request = await request_service.get_request(request_id)

    if user_request is None:
        _logger.warning('Request with ID %s was not found', request_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Request not found',
        )

    if user_request.status in [RequestStatus.SENT, RequestStatus.FAILED]:
        _logger.info('Request %s already sent or failed', user_request.id)
        return Response()

    if user_request.status == RequestStatus.PROCESSING:
        _logger.info('Request %s already processing', user_request.id)
        return Response(status_code=status.HTTP_202_ACCEPTED)

    try:
        _logger.info('Queueing request %s for processing', user_request.id)
        await concurrency_service.add_to_queue(user_request)
        return Response(status_code=status.HTTP_202_ACCEPTED)
    except QueueFullException:
        _logger.warning('Queue full while processing request %s', user_request.id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=('You are being rate-limited. Please try again later.')
        )


@router.get(
    '/{request_id}',
    status_code=status.HTTP_200_OK,
    response_model=GetRequestResponse,
)

async def get_request(
    request_id: str,
    request_service=Depends(get_request_service),
) -> UserRequest:
    """Retrieves a request by ID.

    Args:
        user_request (UserRequest): Existing request resolved by dependency.

    Returns:
        UserRequest: Request entity serialized by the response model.
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
