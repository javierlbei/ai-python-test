"""Client for generating structured content from user prompts."""

import logging

from fastapi import status
from httpx import AsyncClient, HTTPError

from prompts.config import PromptClientConfig
from prompts.exceptions import PromptClientException
from prompts.utils import generate_payload
from requests.models import UserRequest

class PromptClient:
    """Calls the prompt provider to transform user input into JSON-like text.

    Attributes:
        _client (AsyncClient): HTTP client used to call the provider API.
        _system_prompt (str): System instruction forwarded to the provider.
        _max_retries (int): Maximum number of provider call attempts.
        _logger (logging.Logger): Logger instance for observability.
    """

    def __init__(
        self,
        client_settings: PromptClientConfig
    ):
        """Initializes a prompt client using configuration values.

        Args:
            client_settings (PromptClientConfig): Client base URL,
                authentication header, system prompt, and retry limit.
        """

        self._client = AsyncClient(
            base_url=client_settings.BASE_URL,
            headers=client_settings.AUTH_HEADER,
        )
        self._system_prompt = client_settings.SYSTEM_PROMPT
        self._max_retries = client_settings.MAX_RETRIES
        self._logger = logging.getLogger('uvicorn.error')

    async def close(self):
        """Closes the underlying HTTP client and releases network resources."""

        await self._client.aclose()

    async def generate_json(
        self,
        request: UserRequest
    ):
        """Generates model output for a request.

        Sends the request input to the prompt provider and retries failed calls
        until either a successful response is received or the retry budget is
        exhausted.

        Args:
            request (UserRequest): Request containing the user input and ID.

        Returns:
            dict[str, str]: A dictionary with `user_input` and `llm_response`.

        Raises:
            PromptClientException: If no successful response is received after
                all retry attempts.
        """
        self._logger.info('Generating JSON for request with ID: %s', request.id)

        for _ in range(self._max_retries):
            try:
                response = await self._client.post(
                    "/v1/ai/extract",
                    json=generate_payload(self._system_prompt, request.user_input),
                )
            except HTTPError:
                self._logger.warning(
                    'Prompt provider transport error for request with ID: %s',
                    request.id,
                    exc_info=True,
                )
                continue

            if response.status_code == status.HTTP_200_OK:
                generated_response = (
                    response.json()
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )

                self._logger.info('JSON generated for request with ID: %s', request.id)

                return {'user_input': request.user_input, 'llm_response': generated_response}

            self._logger.warning(
                'Prompt provider returned status %s for request with ID: %s',
                response.status_code,
                request.id,
            )

        self._logger.info(
            'Failed to generate JSON for request with ID: %s after %s retries',
            request.id,
            self._max_retries,
        )

        raise PromptClientException()
