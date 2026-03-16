"""Dependency providers and validators for request routes."""

import asyncio
import logging
import time

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

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

class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce a timeout on request processing.

    This middleware wraps each request and ensures that it completes within a specified
    threshold (in seconds). If the request takes longer than the threshold, a 504 Gateway
    Timeout response is returned.

    Attributes:
        _threshold (int): Maximum allowed processing time for a request in seconds.
    """

    def __init__(self, app: FastAPI, threshold: int = 10):
        """Initializes the TimeoutMiddleware.

        Args:
            app (FastAPI): The FastAPI application instance.
            threshold (int, optional): Timeout threshold in seconds. Defaults to 10.
        """
        super().__init__(app)
        self._threshold = threshold

    async def dispatch(self, request: Request, call_next) -> Response:
        """Intercepts the request and enforces the timeout.

        Args:
            request (Request): The incoming FastAPI request.
            call_next (Callable): The next middleware or route handler.

        Returns:
            Response: The response from the route handler or a timeout response.
        """
        try:
            start_time = time.time()

            response_task = asyncio.create_task(call_next(request))
            response = await asyncio.wait_for(response_task, timeout=self._threshold)

            process_time = time.time() - start_time
            response.headers['X-Process-Time'] = str(process_time)

            return response
        except asyncio.TimeoutError:
            _logger.warning(
                'Request processing exceeded timeout threshold of %s seconds',
                self._threshold
            )
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={'detail': 'Request timed out. Please try again later.'},
            )
