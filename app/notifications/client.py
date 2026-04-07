"""HTTP client for dispatching notifications to the notification provider."""

from circuitbreaker import CircuitBreakerError
from httpx import Response
from tenacity import RetryError

from client import GenericClient
from constants import HTTPMethod
from notifications.exceptions import (
    NotificationClientCircuitBreakerError,
    NotificationClientRetryError,
)


class NotificationClient(GenericClient):
    """Specializes ``GenericClient`` for notification delivery."""

    def _wrap_retry_error(self, exc: RetryError) -> Exception:
        return NotificationClientRetryError(
            "Failed to send notification after maximum retries"
        )

    def _wrap_circuit_breaker_error(
        self, exc: CircuitBreakerError,
    ) -> Exception:
        return NotificationClientCircuitBreakerError(
            "Circuit breaker is open, skipping notification"
        )

    async def send_notification(
        self, payload: dict,
    ) -> Response:
        """Sends a notification payload to the provider.

        Builds an HTTP POST request targeting the notification endpoint and
        delegates transport and retry logic to the parent ``GenericClient``.

        Args:
            payload (dict): Notification body containing ``to``, ``type``,
                and ``message`` fields.

        Returns:
            httpx.Response: Response from the notification provider.

        Raises:
            NotificationClientRetryError: If delivery fails after all
                retries.
            NotificationClientCircuitBreakerError: If the circuit breaker
                is open.
        """

        return await super().request(
            method=HTTPMethod.POST,
            endpoint="/v1/notify",
            json=payload,
        )
