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
