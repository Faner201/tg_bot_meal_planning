from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tg_bot_meal_planning.application.user_profile import (
    GetUserProfile,
    RegisterUserProfile,
    UpdateUserProfile,
)
from tg_bot_meal_planning.infrastructure.db.base import Base
from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_user_profile import (
    SqlAlchemyUserProfileRepository,
)
from tg_bot_meal_planning.interface.telegram.bot import (
    BarcodeLookupResult,
    BotDependencies,
    build_router,
)

if TYPE_CHECKING:
    from tg_bot_meal_planning.domain.product import Barcode, Product


def _create_session_factory(db_path: str) -> sessionmaker[Session]:
    """Создаёт фабрику сессий и мигрирует базу, если нужно."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False, class_=Session)


class _AlwaysManualLookup:
    """Временный заглушечный поиск по штрихкоду."""

    def execute(self, data: Barcode) -> BarcodeLookupResult:
        return BarcodeLookupResult(
            product=None,
            needs_manual_input=True,
            reason="поиск по штрихкоду ещё не реализован",
        )


class _MemoryProductSaver:
    """Простейшее in-memory сохранение продуктов."""

    def __init__(self) -> None:
        self._storage: dict[str, Product] = {}

    def execute(self, data: Product) -> Product:
        self._storage[data.id] = data
        return data


def _build_dependencies(session_factory: sessionmaker[Session]) -> BotDependencies:
    profile_repo = SqlAlchemyUserProfileRepository(session_factory)
    return BotDependencies(
        register_profile=RegisterUserProfile(profile_repo),
        update_profile=UpdateUserProfile(profile_repo),
        get_profile=GetUserProfile(profile_repo),
        lookup_product=_AlwaysManualLookup(),
        save_manual_product=_MemoryProductSaver(),
    )


async def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан")

    db_path = os.getenv("DATABASE_PATH", "/app/var/sqlite/app.db")
    session_factory = _create_session_factory(db_path)

    deps = _build_dependencies(session_factory)
    router = build_router(deps)

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)

    logging.info("Запускаем бота (db=%s)", db_path)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
