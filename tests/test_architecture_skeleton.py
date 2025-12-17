from typing import Self

from tg_bot_meal_planning.application.use_case import SyncUseCase, UseCase
from tg_bot_meal_planning.domain.entities import Entity
from tg_bot_meal_planning.infrastructure.repositories.in_memory import InMemoryRepository
from tg_bot_meal_planning.interface.telegram.handlers import UseCaseHandler


def test_entity_requires_id() -> None:
    entity = Entity(id="abc")

    assert entity.id == "abc"


def test_in_memory_repository_can_store_and_get() -> None:
    repo: InMemoryRepository[str, Entity[str]] = InMemoryRepository()
    entity = Entity(id="xyz")

    repo.save(entity_id=entity.id, entity=entity)

    assert repo.get(entity_id="xyz") == entity


def test_use_case_handler_delegates_to_use_case() -> None:
    class EchoUseCase(SyncUseCase[str, str], UseCase[str, str]):
        def execute(self: Self, data: str) -> str:  # type: ignore[override]
            return f"echo:{data}"

    handler = UseCaseHandler(use_case=EchoUseCase())

    assert handler.handle("ping") == "echo:ping"
