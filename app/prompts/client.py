"""Client for generating structured content from user prompts."""

from circuitbreaker import CircuitBreaker, CircuitBreakerError
from httpx import AsyncClient, Request
from tenacity import RetryError

from constants import HTTPMethod
from client import GenericClient
from prompts.exceptions import(
    PromptClientCircuitBreakerException,
    PromptClientRetryException,
)
from prompts.utils import generate_payload
from requests.models import UserRequest


class PromptClient(GenericClient):
    """Specializes ``GenericClient`` for LLM prompt extraction."""

    def __init__(
        self,
        http_client: AsyncClient,
        circuit_breaker: CircuitBreaker,
        system_prompt: str,
        max_retries: int = 3,
    ):
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

        super().__init__(
            http_client=http_client,
            circuit_breaker=circuit_breaker,
            max_retries=max_retries,
        )
        self._system_prompt = system_prompt

    async def generate_json(self, user_request: UserRequest):
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
            PromptClientException: If the request fails after all retries
                or the circuit breaker is open.
        """

        try:
            response = await super().request(
                method=HTTPMethod.POST,
                endpoint="/v1/ai/extract",
                json=generate_payload(self._system_prompt, user_request.user_input)
            )

            llm_response = (
                response.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

            client_response = {
                'user_input': user_request.user_input,
                'llm_response': llm_response
            }

            return client_response
        except RetryError as exc:
            raise PromptClientRetryException(
                "Failed to generate JSON after maximum retries"
            ) from exc
        except CircuitBreakerError as exc:
            raise PromptClientCircuitBreakerException(
                "Circuit breaker is open, skipping JSON generation"
            ) from exc
