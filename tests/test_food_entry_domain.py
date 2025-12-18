from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from tg_bot_meal_planning.domain.errors import ValidationError
from tg_bot_meal_planning.domain.food_entry import (
    AggregateInput,
    FoodDiaryAggregator,
    FoodEntry,
    MacroNutrients,
)


def test_food_entry_scales_macros_by_portion() -> None:
    entry = FoodEntry(
        id="e1",
        user_id="u1",
        title="Овсянка",
        portion_grams=150,
        macros_per_100g=MacroNutrients(protein_g=10, fat_g=5, carbs_g=20),
        taken_at_utc=datetime(2025, 1, 1, 8, 0, tzinfo=UTC),
    )

    macros = entry.actual_macros

    assert macros.protein_g == pytest.approx(15.0)
    assert macros.fat_g == pytest.approx(7.5)
    assert macros.carbs_g == pytest.approx(30.0)
    assert macros.calories_kcal == pytest.approx((15 * 4) + (7.5 * 9) + (30 * 4))


def test_aggregator_sums_entries_in_period() -> None:
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    end = datetime(2025, 1, 2, 0, 0, tzinfo=UTC)
    entries = [
        FoodEntry(
            id="e1",
            user_id="u1",
            title="Омлет",
            portion_grams=120,
            macros_per_100g=MacroNutrients(protein_g=12, fat_g=10, carbs_g=2),
            taken_at_utc=start + timedelta(hours=8),
        ),
        FoodEntry(
            id="e2",
            user_id="u1",
            title="Рис",
            portion_grams=200,
            macros_per_100g=MacroNutrients(protein_g=3, fat_g=0.5, carbs_g=28),
            taken_at_utc=start + timedelta(hours=13),
        ),
        # За пределами интервала
        FoodEntry(
            id="e3",
            user_id="u1",
            title="Поздний перекус",
            portion_grams=100,
            macros_per_100g=MacroNutrients(protein_g=5, fat_g=3, carbs_g=15),
            taken_at_utc=end,
        ),
    ]

    aggregator = FoodDiaryAggregator()
    totals = aggregator.execute(AggregateInput(entries=entries, start_utc=start, end_utc=end))

    expected = entries[0].actual_macros.add(entries[1].actual_macros)
    assert totals.protein_g == pytest.approx(expected.protein_g)
    assert totals.fat_g == pytest.approx(expected.fat_g)
    assert totals.carbs_g == pytest.approx(expected.carbs_g)


def test_food_entry_requires_positive_values_and_utc() -> None:
    with pytest.raises(ValidationError):
        FoodEntry(
            id="e1",
            user_id="u1",
            title="",
            portion_grams=100,
            macros_per_100g=MacroNutrients(protein_g=1, fat_g=1, carbs_g=1),
            taken_at_utc=datetime(2025, 1, 1, 8, 0, tzinfo=UTC),
        )

    with pytest.raises(ValidationError):
        MacroNutrients(protein_g=-1, fat_g=1, carbs_g=1)

    with pytest.raises(ValidationError):
        FoodEntry(
            id="e2",
            user_id="u1",
            title="Батончик",
            portion_grams=0,
            macros_per_100g=MacroNutrients(protein_g=1, fat_g=1, carbs_g=1),
            taken_at_utc=datetime(2025, 1, 1, 8, 0),
        )

    with pytest.raises(ValidationError):
        FoodEntry(
            id="e3",
            user_id="u1",
            title="Батончик",
            portion_grams=50,
            macros_per_100g=MacroNutrients(protein_g=1, fat_g=1, carbs_g=1),
            taken_at_utc=datetime(2025, 1, 1, 8, 0, tzinfo=UTC).astimezone(timezone(timedelta(hours=3))),
        )

