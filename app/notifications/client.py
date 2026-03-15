"""HTTP client for dispatching notifications to the notification provider."""

import asyncio
import logging
import random

from fastapi import status
from httpx import AsyncClient, HTTPError

from notifications.config import NotificationClientConfig
from notifications.exceptions import NotificationClientException


class NotificationClient:
    """Sends notifications to an external notification provider.

    Wraps an HTTPX async HTTP client and retries failed requests up to a
    configurable maximum before giving up.

    Attributes:
        _client (AsyncClient): Underlying async HTTP client used for requests.
        _MAX_RETRIES (int): Maximum number of delivery attempts before raising
            an exception.
    """

    def __init__(
        self,
        client_settings: NotificationClientConfig
    ):
        """Creates a NotificationClient from the supplied configuration.

        Args:
            client_settings (NotificationClientConfig): Configuration object
                containing the provider base URL, authentication headers, and
                the maximum number of retries.
        """

        self._client = AsyncClient(
            base_url=client_settings.BASE_URL,
            headers=client_settings.AUTH_HEADER,
        )
        self._max_retries = client_settings.MAX_RETRIES
        self._logger = logging.getLogger('uvicorn.error')

    async def close(self):
        """Closes the underlying HTTP client and releases its resources."""

        self._logger.info('Closing notification client')
        await self._client.aclose()

    async def send_notification(
        self,
        payload: dict
    ):
        """Sends a notification payload to the provider with automatic retries.

        Attempts the POST request up to `_max_retries` times. Returns as soon
        as the provider responds with HTTP 200. After each failed attempt, it
        waits briefly with a small random spread before retrying. Raises an
        exception when all attempts are exhausted without a successful response.

        Args:
            payload (dict): JSON-serialisable notification data to send.

        Raises:
            NotificationClientException: Raised when all retry attempts fail
                to receive an HTTP 200 response from the provider.
        """

        retry_wait_seconds = 0.5
        retry_spread_seconds = 0.3

        for attempt in range(self._max_retries):
            try:
                response = await self._client.post("/v1/notify", json=payload)
            except HTTPError:
                self._logger.warning(
                    'Notification provider transport error, retrying',
                    exc_info=True,
                )
                if attempt < self._max_retries - 1:
                    wait_seconds = retry_wait_seconds + random.uniform(0, retry_spread_seconds)
                    await asyncio.sleep(wait_seconds)
                continue

            if response.status_code == status.HTTP_200_OK:
                self._logger.info('Notification sent successfully')
                return

            self._logger.warning(
                'Notification provider returned status %s',
                response.status_code,
            )

            if attempt < self._max_retries - 1:
                wait_seconds = retry_wait_seconds + random.uniform(0, retry_spread_seconds)
                await asyncio.sleep(wait_seconds)

        self._logger.error('Notification sending failed after %s retries', self._max_retries)
        raise NotificationClientException()
