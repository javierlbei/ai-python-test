"""HTTP client for dispatching notifications to the notification provider."""

from circuitbreaker import CircuitBreaker, CircuitBreakerError
from httpx import AsyncClient, Request
from tenacity import RetryError

from client import GenericClient
from constants import HTTPMethod
from notifications.exceptions import(
    NotificationClientCircuitBreakerException,
    NotificationClientRetryException,
)


class NotificationClient(GenericClient):
    """Specializes ``GenericClient`` for notification delivery."""

    def __init__(
        self,
        http_client: AsyncClient,
        circuit_breaker: CircuitBreaker,
        max_retries: int = 3,
    ):
        """Creates a NotificationClient from the supplied dependencies.

        Args:
            http_client (AsyncClient): Pre-configured async HTTP client used
                for communicating with the notification provider.
            circuit_breaker (CircuitBreaker): Circuit breaker instance that
                guards notification provider calls.
            max_retries (int): Maximum number of delivery attempts before
                raising an exception.
        """

        super().__init__(
            http_client=http_client,
            circuit_breaker=circuit_breaker,
            max_retries=max_retries,
        )

    async def send_notification(self, payload: dict):
        """Sends a notification payload to the provider.

        Builds an HTTP POST request targeting the notification endpoint and
        delegates transport and retry logic to the parent ``GenericClient``.

        Args:
            payload (dict): Notification body containing ``to``, ``type``,
                and ``message`` fields.

        Returns:
            httpx.Response: Response from the notification provider.

        Raises:
            NotificationClientException: If delivery fails after all retries
                or the circuit breaker is open.
        """

        try:
            return await super().request(
                method=HTTPMethod.POST,
                endpoint="/v1/notify",
                json=payload
            )
        except RetryError as exc:
            raise NotificationClientRetryException(
                "Failed to send notification after maximum retries"
            ) from exc
        except CircuitBreakerError as exc:
            raise NotificationClientCircuitBreakerException(
                "Circuit breaker is open, skipping notification"
            ) from exc
