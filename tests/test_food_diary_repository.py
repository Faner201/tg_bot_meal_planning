from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from tg_bot_meal_planning.domain.food_entry import FoodEntry, MacroNutrients

if TYPE_CHECKING:
    from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_food_diary import (
        SqlAlchemyFoodDiaryRepository,
    )


def test_sqlalchemy_food_diary_repository_persists_and_lists(
    food_diary_repo: SqlAlchemyFoodDiaryRepository,
) -> None:
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    end = datetime(2025, 1, 2, 0, 0, tzinfo=UTC)
    entry = FoodEntry(
        id="e1",
        user_id="u1",
        title="Курица",
        portion_grams=200,
        macros_per_100g=MacroNutrients(protein_g=25, fat_g=3, carbs_g=0),
        taken_at_utc=start.replace(hour=12),
    )

    food_diary_repo.add(entry)

    result = food_diary_repo.list_entries("u1", start, end)

    assert len(result) == 1
    loaded = result[0]
    assert loaded.id == entry.id
    assert loaded.user_id == entry.user_id
    assert loaded.taken_at_utc == entry.taken_at_utc
    assert loaded.actual_macros.protein_g == entry.actual_macros.protein_g

