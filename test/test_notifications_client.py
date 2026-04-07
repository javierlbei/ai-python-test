"""Tests for app/notifications/client.py — notification delivery client."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from circuitbreaker import CircuitBreaker, CircuitBreakerError
from httpx import AsyncClient, Response, TransportError
from tenacity import RetryError

from notifications.client import NotificationClient
from notifications.exceptions import (
    NotificationClientCircuitBreakerError,
    NotificationClientRetryError,
)


@pytest.fixture
def notification_client(mock_http_client, mock_circuit_breaker):
    return NotificationClient(
        http_client=mock_http_client,
        circuit_breaker=mock_circuit_breaker,
        max_retries=1,
    )


class TestNotificationClientWrapErrors:

    def test_wrap_retry_error(self, notification_client):
        exc = RetryError(MagicMock())
        result = notification_client._wrap_retry_error(exc)
        assert isinstance(result, NotificationClientRetryError)

    def test_wrap_circuit_breaker_error(self, notification_client):
        exc = CircuitBreakerError(MagicMock())
        result = notification_client._wrap_circuit_breaker_error(exc)
        assert isinstance(result, NotificationClientCircuitBreakerError)


class TestSendNotification:

    async def test_success(self, mock_http_client, mock_circuit_breaker):
        response = MagicMock(spec=Response)
        response.raise_for_status = MagicMock()
        mock_http_client.request = AsyncMock(return_value=response)

        client = NotificationClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
            max_retries=1,
        )
        payload = {"to": "test@example.com", "type": "email", "message": "hi"}
        result = await client.send_notification(payload)
        assert result is response

    async def test_retry_error_raises_domain_exception(
        self, mock_http_client, mock_circuit_breaker,
    ):
        mock_http_client.request = AsyncMock(
            side_effect=TransportError("connection failed"),
        )
        client = NotificationClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
            max_retries=1,
        )
        payload = {"to": "test@example.com", "type": "email", "message": "hi"}
        with pytest.raises(NotificationClientRetryError):
            await client.send_notification(payload)
