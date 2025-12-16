from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tg_bot_meal_planning.application.user_profile import (
    GetUserProfile,
    RegisterUserProfile,
    UpdateUserProfile,
)
from tg_bot_meal_planning.infrastructure.db import models as _models  # noqa: F401
from tg_bot_meal_planning.infrastructure.db.base import Base
from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_user_profile import (
    SqlAlchemyUserProfileRepository,
)
from tg_bot_meal_planning.interface.telegram.bot import BotDependencies, build_router


def _build_session_factory(database_path: str) -> sessionmaker:
    """Создать фабрику сессий SQLAlchemy и подготовить схему.

    Пытаемся использовать путь из env. Если файловая система недоступна (напр. read-only
    при локальном запуске с путём вида /app/...), откатываемся на локальный var/sqlite.
    """

    db_path = Path(database_path)
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        fallback = Path("var/sqlite/app.db")
        fallback.parent.mkdir(parents=True, exist_ok=True)
        db_path = fallback

    engine = create_engine(f"sqlite:///{db_path}", echo=False, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _init_dependencies(database_path: str) -> BotDependencies:
    session_factory = _build_session_factory(database_path)
    repository = SqlAlchemyUserProfileRepository(session_factory=session_factory)

    return BotDependencies(
        register_profile=RegisterUserProfile(repository),
        update_profile=UpdateUserProfile(repository),
        get_profile=GetUserProfile(repository),
    )


async def main() -> None:
    """Точка входа: инициализирует зависимости и запускает polling aiogram."""

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    # Для локального запуска по умолчанию кладём SQLite рядом с проектом.
    database_path = os.environ.get("DATABASE_PATH", "var/sqlite/app.db")

    deps = _init_dependencies(database_path)

    dp = Dispatcher()
    dp.include_router(build_router(deps))

    bot = Bot(token=token)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(main())

