"""Business logic for request lifecycle and asynchronous processing."""

from user_requests.models import UserRequest
from user_requests.repository import RequestRepository
from user_requests.schemas import CreateRequestBody
from utils import get_logger


class RequestService:
    """Coordinates persistence, prompt generation, and notification delivery.

    Attributes:
        _requests_repository (RequestRepository): Persistence abstraction.
        _logger (logging.Logger): Service logger.
    """

    def __init__(
        self,
        requests_repository: RequestRepository
    ):
        """Initializes the request service dependencies.

        Args:
            requests_repository (RequestRepository): Persistence abstraction.

        """

        self._requests_repository = requests_repository
        self._logger = get_logger()
        self._logger.info('RequestService initialized')

    async def save_request(self, request: CreateRequestBody) -> str:
        """Persists a new or existing request.

        Accepts either API payload schema objects or already-built domain
        objects and writes them through the repository.

        Args:
            request (CreateRequestBody): Request content to persist.

        Returns:
            str: ID of the saved request.
        """

        request_to_save = UserRequest(user_input=request.user_input)

        return await self._requests_repository.save(request_to_save)

    async def get_request(self, request_id: str) -> UserRequest | None:
        """Retrieves a request by ID.

        Args:
            request_id (str): Request identifier.

        Returns:
            UserRequest | None: Stored request when found, otherwise ``None``.
        """

        return await self._requests_repository.get(request_id)
