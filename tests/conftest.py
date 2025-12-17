from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tg_bot_meal_planning.infrastructure.db.base import Base
from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_food_diary import (
    SqlAlchemyFoodDiaryRepository,
)
from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_user_profile import (
    SqlAlchemyUserProfileRepository,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture
def session_factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    # Импорт моделей для регистрации таблиц в metadata
    import tg_bot_meal_planning.infrastructure.db.models  # noqa: F401

    engine = create_engine(f"sqlite:///{tmp_path}/test.db", future=True)
    Base.metadata.create_all(engine)
    factory: sessionmaker[Session] = sessionmaker(engine, expire_on_commit=False, class_=Session)
    yield factory
    engine.dispose()


@pytest.fixture
def user_profile_repo(session_factory: sessionmaker[Session]) -> SqlAlchemyUserProfileRepository:
    return SqlAlchemyUserProfileRepository(session_factory)


@pytest.fixture
def food_diary_repo(session_factory: sessionmaker[Session]) -> SqlAlchemyFoodDiaryRepository:
    return SqlAlchemyFoodDiaryRepository(session_factory)

