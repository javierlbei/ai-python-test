from typing import Generic, TypeVar
from uuid import uuid4

from exceptions import GenericRepositorySaveError
from utils import get_logger

T = TypeVar('T')


class GenericRepository(Generic[T]):
    """Generic in-memory repository for entity persistence.

    Stores entities in a dictionary keyed by auto-generated UUIDs
    and provides basic save/get operations.

    Attributes:
        _data (dict[str, T]): Mapping of entity IDs to entities.
        _logger (logging.Logger): Logger instance.
        _max_attempts (int): Maximum ID generation attempts.
    """

    def __init__(self, max_attempts: int = 10):
        """Initializes the in-memory request store."""

        self._data: dict[str, T] = {}
        self._logger = get_logger()
        self._max_attempts = max_attempts

    async def _generate_id(self) -> str:
        """Generates a unique entity ID.

        Returns:
            str: Generated UUID in hexadecimal format.

        Raises:
            GenericRepositorySaveError: If a unique ID is not generated
                after the maximum number of attempts.
        """

        attempt_count = 0

        while attempt_count < self._max_attempts:
            generated_id = uuid4().hex

            if generated_id not in self._data:
                return generated_id

            attempt_count += 1

        self._logger.error(
            'Could not generate unique ID after %d attempts',
            self._max_attempts
        )
        raise GenericRepositorySaveError()

    async def save(self, entity: T) -> str:
        """Saves or updates a request in the repository.

        If the request has no ID, a new unique ID is generated and assigned.
        Otherwise, the existing request is updated.

        Args:
            entity (T): Entity to create or update.

        Returns:
            str: ID of the persisted entity.

        Raises:
            GenericRepositorySaveError: If a unique ID cannot be generated
                after the maximum number of attempts.
        """

        if entity.id is None:
            generated_id = await self._generate_id()
            entity.id = generated_id
            self._logger.info(
                'Generated %s ID: %s',
                type(entity).__name__,
                entity.id
            )

        self._data[entity.id] = entity

        self._logger.debug(
            'Saved %s with ID: %s',
            type(entity).__name__,
            entity.id
        )

        return entity.id

    async def get(self, entity_id: str) -> T | None:
        """Retrieves an entity by ID.

        Args:
            entity_id (str): Entity identifier.

        Returns:
            T | None: Stored entity when found, otherwise ``None``.
        """

        entity = self._data.get(entity_id)

        if entity is None:
            self._logger.debug(
                'Entity with ID %s not found',
                entity_id
            )
        else:
            self._logger.debug(
                '%s with ID %s retrieved',
                type(entity).__name__,
                entity_id
            )

        return entity
