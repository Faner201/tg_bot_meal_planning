from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tg_bot_meal_planning.application.barcode_scanning import (
    DecodeBarcodeImage,
    SaveBarcodePhoto,
    SaveScannedBarcode,
)
from tg_bot_meal_planning.application.calorie import CalculateCalories
from tg_bot_meal_planning.application.food_diary import AddFoodEntry, AggregateFoodEntries, ListFoodEntries
from tg_bot_meal_planning.application.meal_suggestions import SuggestDailyPlan
from tg_bot_meal_planning.application.user_profile import (
    GetUserProfile,
    RegisterUserProfile,
    UpdateUserProfile,
)
from tg_bot_meal_planning.infrastructure.clients.openfoodfacts import OpenFoodFactsLookup
from tg_bot_meal_planning.infrastructure.db.base import Base
from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_food_diary import SqlAlchemyFoodDiaryRepository
from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_scanned_barcode import (
    SqlAlchemyScannedBarcodeRepository,
)
from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_user_profile import (
    SqlAlchemyUserProfileRepository,
)
from tg_bot_meal_planning.infrastructure.storage.local_photo_storage import LocalPhotoStorage
from tg_bot_meal_planning.interface.telegram.bot import BotDependencies, build_router

if TYPE_CHECKING:
    from tg_bot_meal_planning.domain.product import Product


def _create_session_factory(db_path: str) -> sessionmaker[Session]:
    """Создаёт фабрику сессий и мигрирует базу, если нужно."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False, class_=Session)


class _MemoryProductSaver:
    """Простейшее in-memory сохранение продуктов."""

    def __init__(self) -> None:
        self._storage: dict[str, Product] = {}

    def execute(self, data: Product) -> Product:
        self._storage[data.id] = data
        return data


def _build_dependencies(session_factory: sessionmaker[Session], photo_storage_dir: str) -> BotDependencies:
    profile_repo = SqlAlchemyUserProfileRepository(session_factory)
    diary_repo = SqlAlchemyFoodDiaryRepository(session_factory)
    scanned_repo = SqlAlchemyScannedBarcodeRepository(session_factory)
    photo_storage = LocalPhotoStorage(photo_storage_dir)
    return BotDependencies(
        register_profile=RegisterUserProfile(profile_repo),
        update_profile=UpdateUserProfile(profile_repo),
        get_profile=GetUserProfile(profile_repo),
        calculate_calories=CalculateCalories(profile_repo),
        suggest_daily_plan=SuggestDailyPlan(),
        aggregate_food_diary=AggregateFoodEntries(diary_repo),
        add_food_entry=AddFoodEntry(diary_repo),
        list_food_entries=ListFoodEntries(diary_repo),
        lookup_product=OpenFoodFactsLookup(),
        save_manual_product=_MemoryProductSaver(),
        decode_barcode_image=DecodeBarcodeImage(),
        save_barcode_photo=SaveBarcodePhoto(photo_storage),
        save_scanned_barcode=SaveScannedBarcode(scanned_repo),
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
    photo_storage_dir = os.getenv("PHOTO_STORAGE_DIR", "var/photos")
    session_factory = _create_session_factory(db_path)

    deps = _build_dependencies(session_factory, photo_storage_dir)
    router = build_router(deps)

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)
    await _register_bot_commands(bot)

    logging.info("Запускаем бота (db=%s)", db_path)
    await dp.start_polling(bot)


async def _register_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Справка и список команд"),
        BotCommand(command="set_profile", description="Заполнить профиль (рост, вес, пол, цель)"),
        BotCommand(command="profile", description="Показать текущий профиль"),
        BotCommand(command="weight", description="Обновить вес и, при желании, цель"),
        BotCommand(command="add_food_entry", description="Добавить приём пищи"),
        BotCommand(command="list_food_entries", description="Список приёмов за период"),
        BotCommand(command="calories", description="Рассчитать суточную норму калорий"),
        BotCommand(command="suggest_plan", description="Рекомендации БЖУ и деление по приёмам"),
        BotCommand(command="barcode", description="Поиск продукта по штрихкоду"),
        BotCommand(command="add_product", description="Сохранить продукт вручную"),
        BotCommand(command="summary_day", description="Итоги БЖУ за день"),
        BotCommand(command="summary_week", description="Итоги БЖУ за неделю"),
        BotCommand(command="summary_month", description="Итоги БЖУ за месяц"),
    ]
    await bot.set_my_commands(commands)


if __name__ == "__main__":
    asyncio.run(main())


