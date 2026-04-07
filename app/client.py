"""HTTP client for dispatching requests to an external provider."""

from circuitbreaker import CircuitBreaker, CircuitBreakerError
from httpx import AsyncClient, Response, TransportError
from tenacity import retry, RetryError, stop_after_attempt, wait_exponential

from constants import HTTPMethod
from utils import get_logger


class GenericClient:
    """Sends requests to an external provider.

    Wraps an HTTPX async HTTP client and retries failed requests up to a
    configurable maximum before giving up.

    Attributes:
        _http_client (AsyncClient): Underlying async HTTP client
            used for requests.
        _max_retries (int): Maximum number of delivery attempts before raising
            an exception.
        _circuit_breaker (CircuitBreaker): Circuit breaker guarding provider
            calls.
        _logger (logging.Logger): Logger instance for observability.
    """

    def __init__(
        self,
        http_client: AsyncClient,
        circuit_breaker: CircuitBreaker,
        max_retries: int = 3,
    ):
        """Creates a GenericClient from the supplied dependencies.

        Args:
            http_client (AsyncClient): Pre-configured async HTTP client used
                for sending requests to the external provider.
            circuit_breaker (CircuitBreaker): Circuit breaker instance that
                guards provider calls.
            max_retries (int): Maximum number of delivery attempts before
                raising an exception.
        """

        self._http_client = http_client
        self._max_retries = max_retries
        self._logger = get_logger()
        self._circuit_breaker = circuit_breaker
        self._circuit_breaker.expected_exception = RetryError


    async def close(self) -> None:
        """Closes the underlying HTTP client and releases its resources."""

        self._logger.info('Closing HTTP client')
        await self._http_client.aclose()

    async def _process_response(self, response: Response) -> Response:
        """Post-processes a provider response before returning it.

        Subclasses can override this to parse, transform, or validate the
        response. The default implementation returns the response unchanged.

        Args:
            response (Response): Raw response from the provider.

        Returns:
            Response: The processed response.
        """

        return response

    def _wrap_retry_error(self, exc: RetryError) -> Exception:
        """Wraps a ``RetryError`` in a domain-specific exception.

        Subclasses override this to raise their own exception type.
        The default implementation returns the original error.

        Args:
            exc (RetryError): The retry error to wrap.

        Returns:
            Exception: A domain-specific exception, or the original error.
        """

        return exc

    def _wrap_circuit_breaker_error(
        self, exc: CircuitBreakerError,
    ) -> Exception:
        """Wraps a ``CircuitBreakerError`` in a domain-specific exception.

        Subclasses override this to raise their own exception type.
        The default implementation returns the original error.

        Args:
            exc (CircuitBreakerError): The circuit breaker error to wrap.

        Returns:
            Exception: A domain-specific exception, or the original error.
        """

        return exc

    async def _call_provider(
        self,
        method: HTTPMethod,
        endpoint: str,
        **kwargs,
    ) -> Response:
        """Sends a request to the provider with automatic retries.

        Attempts the request up to ``_max_retries`` times. Returns as soon
        as the provider responds with a successful status. After each failed
        attempt, waits using exponential backoff before retrying. Raises an
        exception when all attempts are exhausted without a successful response.

        Args:
            method (HTTPMethod): HTTP method to use for the request.
            endpoint (str): Endpoint to send the request to.
            **kwargs: Arbitrary keyword arguments forwarded to
                ``httpx.AsyncClient.request`` (e.g. ``json``, ``data``,
                ``params``, ``headers``).

        Returns:
            Response: Response object from the provider.

        Raises:
            RetryError: Raised when all retry attempts fail to receive a
                successful response from the provider.
        """

        @retry(
            wait=wait_exponential(multiplier=1, min=1, max=4),
            stop=stop_after_attempt(self._max_retries)
        )
        async def _call():
            try:
                response = await self._http_client.request(
                    method=method,
                    url=endpoint,
                    **kwargs,
                )
                response.raise_for_status()

                return response
            except TransportError:
                raise

        @self._circuit_breaker
        async def _call_with_circuit_breaker():
            return await _call()

        return await _call_with_circuit_breaker()

    async def request(
        self,
        method: HTTPMethod,
        endpoint: str,
        **kwargs,
    ) -> Response:
        """Sends a request to the provider with retries and circuit breaking.

        Args:
            method (HTTPMethod): HTTP method to use for the request.
            endpoint (str): Endpoint to send the request to.
            **kwargs: Arbitrary keyword arguments forwarded to
                ``httpx.AsyncClient.request`` (e.g. ``json``, ``data``,
                ``params``, ``headers``).

        Returns:
            Response: The processed response from the provider.

        Raises:
            RetryError: Raised when all retry attempts fail to receive a
                successful response from the provider.
            CircuitBreakerError: Raised when the circuit breaker is open
                and the request is skipped.
        """

        try:
            response = await self._call_provider(
                method=method,
                endpoint=endpoint,
                **kwargs,
            )
            return await self._process_response(response)
        except RetryError as exc:
            self._logger.error(
                'Failed to send request after %d attempts',
                self._max_retries,
            )
            raise self._wrap_retry_error(exc) from exc
        except CircuitBreakerError as exc:
            self._logger.error(
                'Circuit breaker is open, skipping request'
            )
            raise self._wrap_circuit_breaker_error(exc) from exc
