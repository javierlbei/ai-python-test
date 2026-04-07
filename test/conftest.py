"""Shared fixtures and helpers for the test suite."""

import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from circuitbreaker import CircuitBreaker
from httpx import AsyncClient

from user_requests.models import UserRequest
from user_requests.constants import RequestStatus


@pytest.fixture
def user_request():
    """Returns a UserRequest with a pre-assigned ID."""
    return UserRequest(user_input="Send email to test@example.com", id="abc123")


@pytest.fixture
def queued_request():
    """Returns a UserRequest in QUEUED status."""
    return UserRequest(
        user_input="Send email to test@example.com",
        id="abc123",
        status=RequestStatus.QUEUED,
    )


@pytest.fixture
def mock_http_client():
    """Returns a mocked AsyncClient."""
    client = AsyncMock(spec=AsyncClient)
    return client


@pytest.fixture
def mock_circuit_breaker():
    """Returns a real CircuitBreaker with high threshold for test stability."""
    return CircuitBreaker(failure_threshold=100, recovery_timeout=1)
