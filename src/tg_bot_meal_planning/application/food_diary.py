from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.application.use_case import SyncUseCase
from tg_bot_meal_planning.domain.errors import ValidationError
from tg_bot_meal_planning.domain.food_entry import (
    AggregateInput,
    FoodDiaryAggregator,
    FoodEntry,
    MacroNutrients,
)

if TYPE_CHECKING:
    from tg_bot_meal_planning.application.repositories import FoodDiaryRepository


@dataclass(frozen=True)
class AddFoodEntryInput:
    user_id: str
    title: str
    portion_grams: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    taken_at: datetime


@dataclass(frozen=True)
class ListFoodEntriesInput:
    user_id: str
    start_utc: datetime
    end_utc: datetime


@dataclass(frozen=True)
class AggregateFoodEntriesInput:
    user_id: str
    start: datetime
    end: datetime


class AddFoodEntry(SyncUseCase[AddFoodEntryInput, FoodEntry]):
    """Добавить запись в дневник питания."""

    def __init__(self, repository: FoodDiaryRepository) -> None:
        self._repository = repository

    def execute(self, data: AddFoodEntryInput) -> FoodEntry:
        _ensure_datetime_awareness(data.taken_at, "taken_at")
        if not data.user_id.strip():
            msg = "user_id не может быть пустым"
            raise UseCaseError(msg)
        if not data.title.strip():
            msg = "title не может быть пустым"
            raise UseCaseError(msg)

        try:
            macros = MacroNutrients(
                protein_g=data.protein_per_100g,
                fat_g=data.fat_per_100g,
                carbs_g=data.carbs_per_100g,
            )
            entry = FoodEntry(
                id=str(uuid4()),
                user_id=data.user_id,
                title=data.title,
                portion_grams=data.portion_grams,
                macros_per_100g=macros,
                taken_at_utc=data.taken_at.astimezone(UTC),
            )
        except ValidationError as exc:
            raise UseCaseError(str(exc)) from exc

        self._repository.add(entry)
        return entry


class ListFoodEntries(SyncUseCase[ListFoodEntriesInput, list[FoodEntry]]):
    """Получить записи за период (UTC)."""

    def __init__(self, repository: FoodDiaryRepository) -> None:
        self._repository = repository

    def execute(self, data: ListFoodEntriesInput) -> list[FoodEntry]:
        _ensure_datetime_awareness(data.start_utc, "start_utc", must_be_utc=True)
        _ensure_datetime_awareness(data.end_utc, "end_utc", must_be_utc=True)
        if data.start_utc >= data.end_utc:
            msg = "start_utc должен быть раньше end_utc"
            raise UseCaseError(msg)

        return self._repository.list_entries(data.user_id, data.start_utc, data.end_utc)


class AggregateFoodEntries(SyncUseCase[AggregateFoodEntriesInput, MacroNutrients]):
    """Агрегировать макросы за период с учётом TZ."""

    def __init__(
        self,
        repository: FoodDiaryRepository,
        aggregator: FoodDiaryAggregator | None = None,
    ) -> None:
        self._repository = repository
        self._aggregator = aggregator or FoodDiaryAggregator()

    def execute(self, data: AggregateFoodEntriesInput) -> MacroNutrients:
        _ensure_datetime_awareness(data.start, "start")
        _ensure_datetime_awareness(data.end, "end")
        start_utc = data.start.astimezone(UTC)
        end_utc = data.end.astimezone(UTC)
        if start_utc >= end_utc:
            msg = "start должен быть раньше end"
            raise UseCaseError(msg)

        entries = self._repository.list_entries(data.user_id, start_utc, end_utc)
        try:
            aggregate_input = AggregateInput(entries=entries, start_utc=start_utc, end_utc=end_utc)
            return self._aggregator.execute(aggregate_input)
        except ValidationError as exc:
            raise UseCaseError(str(exc)) from exc


def _ensure_datetime_awareness(value: datetime, field_name: str, *, must_be_utc: bool = False) -> None:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        msg = f"{field_name} должен быть aware datetime"
        raise UseCaseError(msg)
    if must_be_utc and value.tzinfo != UTC:
        msg = f"{field_name} обязан быть в UTC"
        raise UseCaseError(msg)

