from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from tg_bot_meal_planning.application.repositories import FoodDiaryRepository
from tg_bot_meal_planning.domain.food_entry import FoodEntry, MacroNutrients
from tg_bot_meal_planning.infrastructure.db.models import FoodEntryModel

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session


class SqlAlchemyFoodDiaryRepository(FoodDiaryRepository):
    """Репозиторий дневника питания на SQLAlchemy/SQLite."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def add(self, entry: FoodEntry) -> None:
        with self._session_factory() as session:
            session.merge(self._to_model(entry))
            session.commit()

    def list_entries(self, user_id: str, start_utc: datetime, end_utc: datetime) -> list[FoodEntry]:
        with self._session_factory() as session:
            stmt = (
                select(FoodEntryModel)
                .where(
                    FoodEntryModel.user_id == user_id,
                    FoodEntryModel.taken_at_utc >= start_utc,
                    FoodEntryModel.taken_at_utc < end_utc,
                )
                .order_by(FoodEntryModel.taken_at_utc)
            )
            models = session.scalars(stmt).all()
            return [self._to_domain(model) for model in models]

    @staticmethod
    def _to_model(entry: FoodEntry) -> FoodEntryModel:
        return FoodEntryModel(
            id=entry.id,
            user_id=entry.user_id,
            title=entry.title,
            portion_grams=entry.portion_grams,
            protein_per_100g=entry.macros_per_100g.protein_g,
            fat_per_100g=entry.macros_per_100g.fat_g,
            carbs_per_100g=entry.macros_per_100g.carbs_g,
            taken_at_utc=entry.taken_at_utc.astimezone(UTC),
        )

    @staticmethod
    def _to_domain(model: FoodEntryModel) -> FoodEntry:
        macros = MacroNutrients(
            protein_g=model.protein_per_100g,
            fat_g=model.fat_per_100g,
            carbs_g=model.carbs_per_100g,
        )
        taken_at = model.taken_at_utc
        if taken_at.tzinfo is None or taken_at.tzinfo.utcoffset(taken_at) is None:
            taken_at = taken_at.replace(tzinfo=UTC)
        else:
            taken_at = taken_at.astimezone(UTC)
        return FoodEntry(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            portion_grams=model.portion_grams,
            macros_per_100g=macros,
            taken_at_utc=taken_at,
        )

