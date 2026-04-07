"""Tests for app/prompts/client.py — LLM prompt extraction client."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from circuitbreaker import CircuitBreaker
from httpx import AsyncClient, Response, TransportError
from tenacity import RetryError

from prompts.client import PromptClient
from prompts.exceptions import (
    PromptClientCircuitBreakerError,
    PromptClientRetryError,
)
from user_requests.models import UserRequest


@pytest.fixture
def prompt_client(mock_http_client, mock_circuit_breaker):
    return PromptClient(
        http_client=mock_http_client,
        circuit_breaker=mock_circuit_breaker,
        system_prompt="Extract JSON",
        max_retries=1,
    )


def _make_llm_response(content=""):
    """Builds a mock Response that mimics the LLM provider envelope."""
    response = MagicMock(spec=Response)
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "choices": [
            {"message": {"content": content}}
        ]
    }
    return response


class TestPromptClientInit:

    def test_system_prompt_stored(self, prompt_client):
        assert prompt_client._system_prompt == "Extract JSON"


class TestPromptClientWrapErrors:

    def test_wrap_retry_error(self, prompt_client):
        exc = RetryError(MagicMock())
        result = prompt_client._wrap_retry_error(exc)
        assert isinstance(result, PromptClientRetryError)

    def test_wrap_circuit_breaker_error(self, prompt_client):
        exc = MagicMock()
        result = prompt_client._wrap_circuit_breaker_error(exc)
        assert isinstance(result, PromptClientCircuitBreakerError)


class TestGenerateJson:

    async def test_success(self, mock_http_client, mock_circuit_breaker):
        llm_content = '{"to":"a@b.com","type":"email","message":"hi"}'
        response = _make_llm_response(llm_content)
        mock_http_client.request = AsyncMock(return_value=response)

        client = PromptClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
            system_prompt="Extract JSON",
            max_retries=1,
        )
        request = UserRequest(user_input="send email to a@b.com", id="req-1")
        result = await client.generate_json(request)

        assert result["user_input"] == "send email to a@b.com"
        assert result["llm_response"] == llm_content

    async def test_empty_choices(self, mock_http_client, mock_circuit_breaker):
        """When choices list is empty, llm_response should be empty string."""
        response = MagicMock(spec=Response)
        response.raise_for_status = MagicMock()
        response.json.return_value = {"choices": []}
        mock_http_client.request = AsyncMock(return_value=response)

        client = PromptClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
            system_prompt="Extract JSON",
            max_retries=1,
        )
        request = UserRequest(user_input="test", id="req-1")
        result = await client.generate_json(request)
        assert result["llm_response"] == ""

    async def test_empty_choices_raises(
        self, mock_http_client, mock_circuit_breaker,
    ):
        """Verify empty choices does not raise IndexError (audit finding 6.6)."""
        response = MagicMock(spec=Response)
        response.raise_for_status = MagicMock()
        response.json.return_value = {"choices": []}
        mock_http_client.request = AsyncMock(return_value=response)

        client = PromptClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
            system_prompt="sys",
            max_retries=1,
        )
        request = UserRequest(user_input="test", id="req-1")
        # Should not raise — gracefully handles empty choices
        result = await client.generate_json(request)
        assert result["llm_response"] == ""

    async def test_missing_message_key(
        self, mock_http_client, mock_circuit_breaker,
    ):
        response = MagicMock(spec=Response)
        response.raise_for_status = MagicMock()
        response.json.return_value = {
            "choices": [{"message": {}}],
        }
        mock_http_client.request = AsyncMock(return_value=response)

        client = PromptClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
            system_prompt="sys",
            max_retries=1,
        )
        request = UserRequest(user_input="test", id="req-1")
        result = await client.generate_json(request)
        assert result["llm_response"] == ""

    async def test_retry_error_raises_domain_exception(
        self, mock_http_client, mock_circuit_breaker,
    ):
        mock_http_client.request = AsyncMock(
            side_effect=TransportError("fail"),
        )
        client = PromptClient(
            http_client=mock_http_client,
            circuit_breaker=mock_circuit_breaker,
            system_prompt="sys",
            max_retries=1,
        )
        request = UserRequest(user_input="test", id="req-1")
        with pytest.raises(PromptClientRetryError):
            await client.generate_json(request)
