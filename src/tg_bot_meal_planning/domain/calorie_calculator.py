from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from tg_bot_meal_planning.domain.errors import ValidationError
from tg_bot_meal_planning.domain.services import DomainService
from tg_bot_meal_planning.domain.user_profile import Gender, Goal


@dataclass(frozen=True)
class CalorieCalculationInput:
    height_cm: float
    weight_kg: float
    age_years: int
    gender: Gender
    goal: Goal

    def validate(self: Self) -> None:
        for field_name, value in (
            ("height_cm", self.height_cm),
            ("weight_kg", self.weight_kg),
        ):
            if value <= 0:
                msg = f"{field_name} должно быть положительным числом"
                raise ValidationError(msg)

        if self.age_years <= 0:
            msg = "age_years должен быть положительным целым числом"
            raise ValidationError(msg)


@dataclass(frozen=True)
class CalorieCalculationResult:
    basal_metabolic_rate: float
    maintenance_calories: int
    goal_calories: int
    goal: Goal


class MifflinStJeorCalculator(DomainService[CalorieCalculationInput, CalorieCalculationResult]):
    """Расчёт калорий по формуле Миффлин — Сан Жеор."""

    def __init__(self: Self, *, deficit_factor: float = 0.85, surplus_factor: float = 1.1) -> None:
        if deficit_factor <= 0 or surplus_factor <= 0:
            msg = "Множители целей должны быть положительными"
            raise ValidationError(msg)
        self._deficit_factor = deficit_factor
        self._surplus_factor = surplus_factor

    def execute(self: Self, data: CalorieCalculationInput) -> CalorieCalculationResult:
        data.validate()
        bmr = self._calculate_bmr(data)
        maintenance_calories = round(bmr)
        goal_calories = self._apply_goal(maintenance_calories, data.goal)

        return CalorieCalculationResult(
            basal_metabolic_rate=bmr,
            maintenance_calories=maintenance_calories,
            goal_calories=goal_calories,
            goal=data.goal,
        )

    def _calculate_bmr(self: Self, data: CalorieCalculationInput) -> float:
        base = (10 * data.weight_kg) + (6.25 * data.height_cm) - (5 * data.age_years)
        gender_const = 5 if data.gender is Gender.MALE else -161
        return base + gender_const

    def _apply_goal(self: Self, maintenance_calories: int, goal: Goal) -> int:
        factor = {
            Goal.LOSE_WEIGHT: self._deficit_factor,
            Goal.MAINTAIN_WEIGHT: 1.0,
            Goal.GAIN_WEIGHT: self._surplus_factor,
        }[goal]
        return round(maintenance_calories * factor)



