"""Tests for app/repository.py — in-memory generic repository."""

from dataclasses import dataclass
from unittest.mock import patch

import pytest

from exceptions import GenericRepositorySaveError
from repository import GenericRepository


@dataclass
class _FakeEntity:
    name: str
    id: str | None = None


class TestGenericRepository:

    @pytest.fixture
    def repo(self):
        return GenericRepository[_FakeEntity]()

    async def test_save_assigns_id(self, repo):
        entity = _FakeEntity(name="test")
        entity_id = await repo.save(entity)

        assert entity_id is not None
        assert entity.id == entity_id

    async def test_save_preserves_existing_id(self, repo):
        entity = _FakeEntity(name="test", id="existing-id")
        entity_id = await repo.save(entity)

        assert entity_id == "existing-id"

    async def test_save_update_existing(self, repo):
        entity = _FakeEntity(name="original")
        entity_id = await repo.save(entity)

        entity.name = "updated"
        await repo.save(entity)

        result = await repo.get(entity_id)
        assert result.name == "updated"

    async def test_get_returns_saved_entity(self, repo):
        entity = _FakeEntity(name="test")
        entity_id = await repo.save(entity)

        result = await repo.get(entity_id)
        assert result is entity

    async def test_get_returns_none_for_missing(self, repo):
        result = await repo.get("nonexistent")
        assert result is None

    async def test_generate_id_raises_on_exhaustion(self):
        repo = GenericRepository[_FakeEntity](max_attempts=1)
        entity1 = _FakeEntity(name="first")
        await repo.save(entity1)

        with patch("repository.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = entity1.id
            entity2 = _FakeEntity(name="second")
            with pytest.raises(GenericRepositorySaveError):
                await repo.save(entity2)
