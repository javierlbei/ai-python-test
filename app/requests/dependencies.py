"""Dependency providers and validators for request routes."""

import logging

from fastapi import Depends, HTTPException, Request, status

from concurrency.service import ConcurrencyService
from requests.models import UserRequest
from requests.service import RequestService


_logger = logging.getLogger('uvicorn.error')


async def get_concurrency_service(request: Request) -> ConcurrencyService:
    """Returns the concurrency service stored in app state.

    Args:
        request (Request): Active FastAPI request object.

    Returns:
        ConcurrencyService: Shared concurrency service instance.
    """

    return request.app.state.concurrency_service

async def get_request_service(request: Request) -> RequestService:
    """Returns the request service stored in app state.

    Args:
        request (Request): Active FastAPI request object.

    Returns:
        RequestService: Shared request service instance.
    """

    return request.app.state.request_service

async def existant_request_id(
    request_id: str,
    request_service: RequestService = Depends(get_request_service),
) -> UserRequest:
    """Validates that a request ID exists and returns the request.

    Args:
        request_id (str): Request identifier from path parameters.
        request_service (RequestService): Service used to retrieve requests.

    Returns:
        UserRequest: Retrieved request entity.

    Raises:
        HTTPException: Raised with status 404 when the request does not exist.
    """

    request = await request_service.get_request(request_id)

    if request is None:
        _logger.warning('Request with ID %s was not found', request_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Request not found',
        )

    _logger.debug('Request with ID %s exists', request_id)

    return request
