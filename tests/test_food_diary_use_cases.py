from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

import pytest

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.application.food_diary import (
    AddFoodEntry,
    AddFoodEntryInput,
    AggregateFoodEntries,
    AggregateFoodEntriesInput,
    ListFoodEntries,
    ListFoodEntriesInput,
)
from tg_bot_meal_planning.application.repositories import FoodDiaryRepository
from tg_bot_meal_planning.domain.food_entry import FoodEntry, MacroNutrients


@dataclass
class FakeFoodDiaryRepo(FoodDiaryRepository):
    entries: list[FoodEntry]

    def __post_init__(self) -> None:
        self.saved: list[FoodEntry] = []
        self.last_range: tuple[str, datetime, datetime] | None = None

    def add(self, entry: FoodEntry) -> None:
        self.saved.append(entry)
        self.entries.append(entry)

    def list_entries(self, user_id: str, start_utc: datetime, end_utc: datetime) -> list[FoodEntry]:
        self.last_range = (user_id, start_utc, end_utc)
        return [
            entry
            for entry in self.entries
            if entry.user_id == user_id and start_utc <= entry.taken_at_utc < end_utc
        ]


def test_add_food_entry_saves_entry() -> None:
    repo = FakeFoodDiaryRepo(entries=[])
    use_case = AddFoodEntry(repository=repo)
    taken_at = datetime(2025, 1, 1, 9, 30, tzinfo=timezone(timedelta(hours=3)))

    entry = use_case.execute(
        AddFoodEntryInput(
            user_id="u1",
            title="Овсянка",
            portion_grams=120,
            protein_per_100g=10,
            fat_per_100g=5,
            carbs_per_100g=20,
            taken_at=taken_at,
        )
    )

    assert entry.taken_at_utc.tzinfo == UTC
    assert repo.saved[0] is entry
    assert entry.id


def test_aggregate_food_entries_converts_timezone_and_sums() -> None:
    tz = timezone(timedelta(hours=3))
    entries = [
        FoodEntry(
            id="e1",
            user_id="u1",
            title="Приём 1",
            portion_grams=100,
            macros_per_100g=MacroNutrients(protein_g=10, fat_g=5, carbs_g=15),
            taken_at_utc=datetime(2024, 12, 31, 22, 0, tzinfo=UTC),
        ),
        FoodEntry(
            id="e2",
            user_id="u1",
            title="Приём 2",
            portion_grams=150,
            macros_per_100g=MacroNutrients(protein_g=8, fat_g=7, carbs_g=30),
            taken_at_utc=datetime(2025, 1, 1, 20, 0, tzinfo=UTC),
        ),
        # Вне интервала по TZ
        FoodEntry(
            id="e3",
            user_id="u1",
            title="Поздний перекус",
            portion_grams=50,
            macros_per_100g=MacroNutrients(protein_g=5, fat_g=5, carbs_g=10),
            taken_at_utc=datetime(2025, 1, 1, 21, 30, tzinfo=UTC),
        ),
    ]
    repo = FakeFoodDiaryRepo(entries=entries.copy())
    use_case = AggregateFoodEntries(repository=repo)

    start_local = datetime(2025, 1, 1, 0, 0, tzinfo=tz)
    end_local = datetime(2025, 1, 2, 0, 0, tzinfo=tz)

    totals = use_case.execute(
        AggregateFoodEntriesInput(
            user_id="u1",
            start=start_local,
            end=end_local,
        )
    )

    # UTC границы
    assert repo.last_range is not None
    start_utc_expected = start_local.astimezone(UTC)
    end_utc_expected = end_local.astimezone(UTC)
    assert repo.last_range[1] == start_utc_expected
    assert repo.last_range[2] == end_utc_expected

    included = entries[0].actual_macros.add(entries[1].actual_macros)
    assert totals.protein_g == pytest.approx(included.protein_g)
    assert totals.fat_g == pytest.approx(included.fat_g)
    assert totals.carbs_g == pytest.approx(included.carbs_g)


def test_list_food_entries_requires_utc() -> None:
    repo = FakeFoodDiaryRepo(entries=[])
    use_case = ListFoodEntries(repository=repo)

    with pytest.raises(UseCaseError):
        use_case.execute(
            ListFoodEntriesInput(
                user_id="u1",
                start_utc=datetime(2025, 1, 1, 0, 0),
                end_utc=datetime(2025, 1, 2, 0, 0, tzinfo=UTC),
            )
        )

    with pytest.raises(UseCaseError):
        use_case.execute(
            ListFoodEntriesInput(
                user_id="u1",
                start_utc=datetime(2025, 1, 2, 0, 0, tzinfo=UTC),
                end_utc=datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
            )
        )

