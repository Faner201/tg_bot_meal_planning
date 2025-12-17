from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from tg_bot_meal_planning.domain.entities import Entity
from tg_bot_meal_planning.domain.errors import ValidationError
from tg_bot_meal_planning.domain.value_objects import ValueObject


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class Goal(StrEnum):
    LOSE_WEIGHT = "lose_weight"
    MAINTAIN_WEIGHT = "maintain_weight"
    GAIN_WEIGHT = "gain_weight"


@dataclass(frozen=True)
class MacroTargets(ValueObject):
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
            _ensure_non_negative(value, field_name)


@dataclass(frozen=True)
class UserProfile(Entity[str]):
    """Данные профиля пользователя для расчётов рациона."""

    height_cm: float
    weight_kg: float
    gender: Gender
    goal: Goal
    macro_targets: MacroTargets | None = None

    def __post_init__(self: Self) -> None:
        super().__post_init__()
        _ensure_positive(self.height_cm, "height_cm")
        _ensure_positive(self.weight_kg, "weight_kg")
        if self.macro_targets is not None:
            self.macro_targets.validate()

    def update(
        self: Self,
        *,
        height_cm: float | None = None,
        weight_kg: float | None = None,
        gender: Gender | None = None,
        goal: Goal | None = None,
        macro_targets: MacroTargets | None = None,
    ) -> UserProfile:
        """Создать обновлённую копию профиля."""

        return UserProfile(
            id=self.id,
            height_cm=height_cm if height_cm is not None else self.height_cm,
            weight_kg=weight_kg if weight_kg is not None else self.weight_kg,
            gender=gender if gender is not None else self.gender,
            goal=goal if goal is not None else self.goal,
            macro_targets=macro_targets if macro_targets is not None else self.macro_targets,
        )


def _ensure_positive(value: float, field_name: str) -> None:
    if value <= 0:
        msg = f"{field_name} должно быть положительным числом"
        raise ValidationError(msg)


def _ensure_non_negative(value: float, field_name: str) -> None:
    if value < 0:
        msg = f"{field_name} не может быть отрицательным"
        raise ValidationError(msg)



