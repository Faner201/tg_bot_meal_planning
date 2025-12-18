from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from tg_bot_meal_planning.application.use_case import SyncUseCase, UseCase
from tg_bot_meal_planning.domain.entities import Entity
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, UserProfile
from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_user_profile import (
    SqlAlchemyUserProfileRepository,
)
from tg_bot_meal_planning.interface.telegram.handlers import UseCaseHandler


def test_entity_requires_id() -> None:
    entity = Entity(id="abc")

    assert entity.id == "abc"


def test_sqlalchemy_repository_can_store_and_get(session_factory: sessionmaker[Session]) -> None:
    repo = SqlAlchemyUserProfileRepository(session_factory)
    profile = UserProfile(
        id="xyz",
        height_cm=170,
        weight_kg=70,
        gender=Gender.MALE,
        goal=Goal.MAINTAIN_WEIGHT,
    )

    repo.save(profile)

    assert repo.get("xyz") == profile


def test_use_case_handler_delegates_to_use_case() -> None:
    class EchoUseCase(SyncUseCase[str, str], UseCase[str, str]):
        def execute(self: Self, data: str) -> str:  # type: ignore[override]
            return f"echo:{data}"

    handler = UseCaseHandler(use_case=EchoUseCase())

    assert handler.handle("ping") == "echo:ping"


