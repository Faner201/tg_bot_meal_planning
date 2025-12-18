from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self

from tg_bot_meal_planning.domain.entities import Entity
from tg_bot_meal_planning.domain.errors import ValidationError
from tg_bot_meal_planning.domain.services import DomainService
from tg_bot_meal_planning.domain.value_objects import ValueObject


@dataclass(frozen=True)
class MacroNutrients(ValueObject):
    """Количество макронутриентов в граммах."""

    protein_g: float
    fat_g: float
    carbs_g: float

    def __post_init__(self: Self) -> None:
        self.validate()

    def validate(self: Self) -> None:
        for field_name, value in (
            ("protein_g", self.protein_g),
            ("fat_g", self.fat_g),
            ("carbs_g", self.carbs_g),
        ):
            if value < 0:
                msg = f"{field_name} не может быть отрицательным"
                raise ValidationError(msg)

    @property
    def calories_kcal(self: Self) -> float:
        """Энергетическая ценность по стандартной формуле 4-9-4."""

        return (self.protein_g * 4) + (self.fat_g * 9) + (self.carbs_g * 4)

    def scale_by_portion(self: Self, portion_grams: float) -> MacroNutrients:
        """Пересчитать макросы по размеру порции (г)."""

        if portion_grams <= 0:
            msg = "portion_grams должно быть положительным числом"
            raise ValidationError(msg)

        factor = portion_grams / 100
        return MacroNutrients(
            protein_g=self.protein_g * factor,
            fat_g=self.fat_g * factor,
            carbs_g=self.carbs_g * factor,
        )

    def add(self: Self, other: MacroNutrients) -> MacroNutrients:
        """Просуммировать макросы."""

        return MacroNutrients(
            protein_g=self.protein_g + other.protein_g,
            fat_g=self.fat_g + other.fat_g,
            carbs_g=self.carbs_g + other.carbs_g,
        )

    @classmethod
    def zero(cls: type[MacroNutrients]) -> MacroNutrients:
        return cls(protein_g=0.0, fat_g=0.0, carbs_g=0.0)


@dataclass(frozen=True)
class FoodEntry(Entity[str]):
    """Запись дневника питания."""

    user_id: str
    title: str
    portion_grams: float
    macros_per_100g: MacroNutrients
    taken_at_utc: datetime

    def __post_init__(self: Self) -> None:
        super().__post_init__()
        if not self.title.strip():
            msg = "title не может быть пустым"
            raise ValidationError(msg)
        if self.portion_grams <= 0:
            msg = "portion_grams должно быть положительным числом"
            raise ValidationError(msg)
        self.macros_per_100g.validate()
        self._ensure_utc(self.taken_at_utc)

    @property
    def actual_macros(self: Self) -> MacroNutrients:
        """Фактические макросы с учётом размера порции."""

        return self.macros_per_100g.scale_by_portion(self.portion_grams)

    @staticmethod
    def _ensure_utc(dt: datetime) -> None:
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            msg = "taken_at_utc должен быть aware datetime с таймзоной UTC"
            raise ValidationError(msg)
        if dt.tzinfo != UTC:
            msg = "taken_at_utc обязан быть в UTC"
            raise ValidationError(msg)


@dataclass(frozen=True)
class AggregateInput(ValueObject):
    """Период агрегации и записи дневника."""

    entries: list[FoodEntry]
    start_utc: datetime
    end_utc: datetime

    def __post_init__(self: Self) -> None:
        self.validate()

    def validate(self: Self) -> None:
        for field_name, value in (("start_utc", self.start_utc), ("end_utc", self.end_utc)):
            if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
                msg = f"{field_name} должен быть aware datetime в UTC"
                raise ValidationError(msg)
            if value.tzinfo != UTC:
                msg = f"{field_name} обязан быть в UTC"
                raise ValidationError(msg)
        if self.start_utc >= self.end_utc:
            msg = "start_utc должен быть раньше end_utc"
            raise ValidationError(msg)


class FoodDiaryAggregator(DomainService[AggregateInput, MacroNutrients]):
    """Агрегирует макросы по выбранному периоду."""

    def execute(self: Self, data: AggregateInput) -> MacroNutrients:
        data.validate()

        total = MacroNutrients.zero()
        for entry in data.entries:
            if data.start_utc <= entry.taken_at_utc < data.end_utc:
                total = total.add(entry.actual_macros)
        return total



