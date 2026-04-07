"""Client for generating structured content from user prompts."""

from circuitbreaker import CircuitBreakerError
from httpx import Response
from tenacity import RetryError

from client import GenericClient
from constants import HTTPMethod
from prompts.exceptions import (
    PromptClientCircuitBreakerError,
    PromptClientRetryError,
)
from prompts.utils import generate_payload
from user_requests.models import UserRequest


class PromptClient(GenericClient):
    """Specializes ``GenericClient`` for LLM prompt extraction."""

    def __init__(self, *, system_prompt: str, **kwargs):
        """Creates a PromptClient from the supplied dependencies.

        Args:
            http_client (AsyncClient): Pre-configured async HTTP client used
                for communicating with the prompt provider.
            circuit_breaker (CircuitBreaker): Circuit breaker instance that
                guards prompt provider calls.
            system_prompt (str): System instruction prepended to every
                extraction request.
            max_retries (int): Maximum number of delivery attempts before
                raising an exception.
        """

        super().__init__(**kwargs)
        self._system_prompt = system_prompt

    def _wrap_retry_error(self, exc: RetryError) -> Exception:
        return PromptClientRetryError(
            "Failed to generate JSON after maximum retries"
        )

    def _wrap_circuit_breaker_error(
        self, exc: CircuitBreakerError,
    ) -> Exception:
        return PromptClientCircuitBreakerError(
            "Circuit breaker is open, skipping JSON generation"
        )

    async def generate_json(
        self, user_request: UserRequest,
    ) -> dict:
        """Sends user input to the LLM and returns structured output.

        Builds a prompt payload, posts it to the extraction endpoint, and
        parses the model's response into a dictionary containing the
        original user input and the raw LLM output.

        Args:
            user_request (UserRequest): Domain object holding the user's
                raw input text.

        Returns:
            dict: Dictionary with ``user_input`` and ``llm_response`` keys.

        Raises:
            PromptClientRetryError: If the request fails after all
                retries.
            PromptClientCircuitBreakerError: If the circuit breaker
                is open.
        """

        response = await super().request(
            method=HTTPMethod.POST,
            endpoint="/v2/ai/extract",
            json=generate_payload(self._system_prompt, user_request.user_input),
        )

        choices = response.json().get("choices", [])
        llm_response = (
            choices[0].get("message", {}).get("content", "")
            if choices else ""
        )

        return {
            'user_input': user_request.user_input,
            'llm_response': llm_response,
        }
