"""In-memory repository for request persistence."""

import logging
from typing import Dict
from uuid import uuid4

from repositories.exceptions import RequestRepositorySaveException
from requests.models import UserRequest

class RequestRepository:
    """Performs persistence operations for user requests.

    Attributes:
        _data (Dict[str, UserRequest]): In-memory request store keyed by ID.
    """

    def __init__(self):
        """Initializes the in-memory request store."""

        self._data: Dict[str, UserRequest] = {}
        self._logger = logging.getLogger('uvicorn.error')

    async def _generate_id(self) -> str:
        """Generates a unique request ID.

        Returns:
            str: Generated UUID in hexadecimal format.

        Raises:
            RequestRepositorySaveException: If a unique ID is not generated
                after the maximum number of attempts.
        """

        max_retries = 0

        while max_retries < 10:
            generated_id = uuid4().hex

            if generated_id not in self._data:
                return generated_id

            max_retries += 1

        self._logger.error('Could not generate unique request ID after 10 attempts')
        raise RequestRepositorySaveException()

    async def save(self, request: UserRequest) -> str:
        """Saves or updates a request in the repository.

        If the request has no ID, a new unique ID is generated and assigned.
        Otherwise, the existing request is updated.

        Args:
            request (UserRequest): Request to create or update.

        Returns:
            str: ID of the persisted request.
        """

        if request.id is None:
            generated_id = await self._generate_id()
            request.id = generated_id
            self._logger.info('Generated request ID: %s', request.id)

        self._data[request.id] = request
        self._logger.debug('Saved request with ID: %s', request.id)

        return request.id



    async def get_request_by_id(self, request_id: str) -> UserRequest | None:
        """Retrieves a request by ID.

        Args:
            request_id (str): Request identifier.

        Returns:
            UserRequest | None: Stored request when found, otherwise ``None``.
        """

        request = self._data.get(request_id)

        if request is None:
            self._logger.debug('Request with ID %s not found', request_id)
        else:
            self._logger.debug('Request with ID %s retrieved', request_id)

        return request
