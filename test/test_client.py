"""Tests for app/client.py — generic HTTP client with retry and circuit breaker."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from circuitbreaker import CircuitBreaker, CircuitBreakerError
from httpx import AsyncClient, Response, TransportError
from tenacity import RetryError

from client import GenericClient
from constants import HTTPMethod


class TestGenericClientInit:

    def test_attributes_set(self, mock_http_client, mock_circuit_breaker):
        client = GenericClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
            max_retries=5,
        )
        assert client._http_client is mock_http_client
        assert client._max_retries == 5
        assert client._circuit_breaker is mock_circuit_breaker
        assert client._circuit_breaker.expected_exception is RetryError


class TestGenericClientClose:

    async def test_close_calls_aclose(self, mock_http_client, mock_circuit_breaker):
        client = GenericClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
        )
        await client.close()
        mock_http_client.aclose.assert_awaited_once()


class TestGenericClientProcessResponse:

    async def test_default_returns_response_unchanged(
        self, mock_http_client, mock_circuit_breaker,
    ):
        client = GenericClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
        )
        response = MagicMock(spec=Response)
        result = await client._process_response(response)
        assert result is response


class TestGenericClientWrapErrors:

    def test_wrap_retry_error_returns_original(
        self, mock_http_client, mock_circuit_breaker,
    ):
        client = GenericClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
        )
        exc = RetryError(MagicMock())
        result = client._wrap_retry_error(exc)
        assert result is exc

    def test_wrap_circuit_breaker_error_returns_original(
        self, mock_http_client, mock_circuit_breaker,
    ):
        client = GenericClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
        )
        exc = CircuitBreakerError(mock_circuit_breaker)
        result = client._wrap_circuit_breaker_error(exc)
        assert result is exc


class TestGenericClientRequest:

    async def test_successful_request(
        self, mock_http_client, mock_circuit_breaker,
    ):
        response = MagicMock(spec=Response)
        response.raise_for_status = MagicMock()
        mock_http_client.request = AsyncMock(return_value=response)

        client = GenericClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
            max_retries=1,
        )
        result = await client.request(
            method=HTTPMethod.POST,
            endpoint="/test",
            json={"key": "value"},
        )
        assert result is response

    async def test_process_response_called(
        self, mock_http_client, mock_circuit_breaker,
    ):
        response = MagicMock(spec=Response)
        response.raise_for_status = MagicMock()
        mock_http_client.request = AsyncMock(return_value=response)

        client = GenericClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
            max_retries=1,
        )
        processed = MagicMock(spec=Response)
        client._process_response = AsyncMock(return_value=processed)

        result = await client.request(
            method=HTTPMethod.GET,
            endpoint="/check",
        )
        client._process_response.assert_awaited_once_with(response)
        assert result is processed

    async def test_retry_error_wrapped(
        self, mock_http_client, mock_circuit_breaker,
    ):
        mock_http_client.request = AsyncMock(
            side_effect=TransportError("connection failed"),
        )
        client = GenericClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
            max_retries=1,
        )
        with pytest.raises(RetryError):
            await client.request(method=HTTPMethod.GET, endpoint="/fail")

    async def test_circuit_breaker_error_wrapped(
        self, mock_http_client, mock_circuit_breaker,
    ):
        mock_http_client.request = AsyncMock(
            side_effect=TransportError("connection failed"),
        )
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        client = GenericClient(
            http_client=mock_http_client,
            circuit_breaker=cb,
            max_retries=1,
        )
        # Trip the circuit breaker
        with pytest.raises(RetryError):
            await client.request(method=HTTPMethod.GET, endpoint="/fail")

        # Now should get CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            await client.request(method=HTTPMethod.GET, endpoint="/fail")
