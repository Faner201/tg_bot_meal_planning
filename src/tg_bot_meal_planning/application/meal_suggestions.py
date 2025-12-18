from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.application.use_case import SyncUseCase
from tg_bot_meal_planning.domain.calorie_calculator import (
    CalorieCalculationInput,
    MifflinStJeorCalculator,
)
from tg_bot_meal_planning.domain.errors import ValidationError
from tg_bot_meal_planning.domain.food_entry import MacroNutrients
from tg_bot_meal_planning.domain.user_profile import Goal, UserProfile

DEFAULT_MEAL_SHARES: dict[str, float] = {
    "breakfast": 0.25,
    "lunch": 0.35,
    "dinner": 0.30,
    "snacks": 0.10,
}


@dataclass(frozen=True)
class MealSuggestionConfig:
    """Конфигурация расчёта и распределения макросов."""

    protein_g_per_kg: float = 1.8
    fat_g_per_kg: float = 0.9
    goal_multipliers: dict[Goal, float] = field(
        default_factory=lambda: {
            Goal.LOSE_WEIGHT: 0.9,
            Goal.MAINTAIN_WEIGHT: 1.0,
            Goal.GAIN_WEIGHT: 1.1,
        }
    )
    meal_shares: dict[str, float] = field(default_factory=lambda: DEFAULT_MEAL_SHARES)
    min_calories: int = 1200
    min_protein_g_per_kg: float = 1.2
    min_fat_g_per_kg: float = 0.6
    shares_tolerance: float = 0.02

    def validate(self: Self) -> None:
        for field_name, value in (
            ("protein_g_per_kg", self.protein_g_per_kg),
            ("fat_g_per_kg", self.fat_g_per_kg),
            ("min_calories", self.min_calories),
            ("min_protein_g_per_kg", self.min_protein_g_per_kg),
            ("min_fat_g_per_kg", self.min_fat_g_per_kg),
        ):
            if value <= 0:
                msg = f"{field_name} должно быть положительным"
                raise UseCaseError(msg)

        for goal in Goal:
            factor = self.goal_multipliers.get(goal)
            if factor is None or factor <= 0:
                msg = f"Не задан положительный множитель для цели {goal.value}"
                raise UseCaseError(msg)

        if not self.meal_shares:
            msg = "Доли приёмов пищи должны быть заданы"
            raise UseCaseError(msg)

        total_share = sum(self.meal_shares.values())
        if abs(total_share - 1.0) > self.shares_tolerance:
            msg = "Сумма долей приёмов пищи должна быть близка к 1.0"
            raise UseCaseError(msg)

        for name, share in self.meal_shares.items():
            if share <= 0:
                msg = f"Доля приёма '{name}' должна быть положительной"
                raise UseCaseError(msg)


@dataclass(frozen=True)
class MealPortion:
    """Рекомендация для одного приёма пищи."""

    name: str
    share: float
    macros: MacroNutrients

    @property
    def calories_kcal(self: Self) -> float:
        return self.macros.calories_kcal


@dataclass(frozen=True)
class MealSuggestionResult:
    """Результат расчёта дневного плана."""

    target_calories: int
    target_macros: MacroNutrients
    meals: list[MealPortion]


@dataclass(frozen=True)
class SuggestDailyPlanInput:
    """Входные данные для расчёта рациона."""

    profile: UserProfile
    calories: int | None = None
    age_years: int | None = None


class SuggestDailyPlan(SyncUseCase[SuggestDailyPlanInput, MealSuggestionResult]):
    """Рассчитать целевые БЖУ и разбиение по приёмам пищи."""

    def __init__(
        self: Self,
        *,
        calculator: MifflinStJeorCalculator | None = None,
        config: MealSuggestionConfig | None = None,
    ) -> None:
        self._calculator = calculator or MifflinStJeorCalculator()
        self._config = config or MealSuggestionConfig()
        self._config.validate()

    def execute(self: Self, data: SuggestDailyPlanInput) -> MealSuggestionResult:
        profile = data.profile
        calories = self._resolve_calories(profile, data)
        self._ensure_minimums(profile, calories)

        targets = self._calculate_targets(profile, calories)
        meals = self._distribute_meals(targets)
        return MealSuggestionResult(
            target_calories=calories,
            target_macros=targets,
            meals=meals,
        )

    def _resolve_calories(self: Self, profile: UserProfile, data: SuggestDailyPlanInput) -> int:
        if data.calories is not None:
            if data.calories <= 0:
                msg = "calories должно быть положительным"
                raise UseCaseError(msg)
            factor = self._config.goal_multipliers[profile.goal]
            return round(data.calories * factor)

        if data.age_years is None:
            msg = "age_years обязателен, если calories не передан"
            raise UseCaseError(msg)

        try:
            calculation_input = CalorieCalculationInput(
                height_cm=profile.height_cm,
                weight_kg=profile.weight_kg,
                age_years=data.age_years,
                gender=profile.gender,
                goal=profile.goal,
            )
            result = self._calculator.execute(calculation_input)
            return result.goal_calories
        except ValidationError as exc:
            raise UseCaseError(str(exc)) from exc

    def _ensure_minimums(self: Self, profile: UserProfile, calories: int) -> None:
        if calories < self._config.min_calories:
            msg = "calories ниже допустимого минимума"
            raise UseCaseError(msg)

        protein_g = profile.weight_kg * self._config.protein_g_per_kg
        fat_g = profile.weight_kg * self._config.fat_g_per_kg

        min_protein = profile.weight_kg * self._config.min_protein_g_per_kg
        min_fat = profile.weight_kg * self._config.min_fat_g_per_kg

        if protein_g < min_protein:
            msg = "protein_g_per_kg ниже безопасного минимума"
            raise UseCaseError(msg)
        if fat_g < min_fat:
            msg = "fat_g_per_kg ниже безопасного минимума"
            raise UseCaseError(msg)

    def _calculate_targets(self: Self, profile: UserProfile, calories: int) -> MacroNutrients:
        protein_g = profile.weight_kg * self._config.protein_g_per_kg
        fat_g = profile.weight_kg * self._config.fat_g_per_kg

        protein_cal = protein_g * 4
        fat_cal = fat_g * 9
        remaining_calories = calories - (protein_cal + fat_cal)
        if remaining_calories < 0:
            msg = "Недостаточно калорий для распределения углеводов"
            raise UseCaseError(msg)

        carbs_g = remaining_calories / 4
        return MacroNutrients(
            protein_g=protein_g,
            fat_g=fat_g,
            carbs_g=carbs_g,
        )

    def _distribute_meals(self: Self, targets: MacroNutrients) -> list[MealPortion]:
        meals: list[MealPortion] = []
        for name, share in self._config.meal_shares.items():
            meal_macros = MacroNutrients(
                protein_g=targets.protein_g * share,
                fat_g=targets.fat_g * share,
                carbs_g=targets.carbs_g * share,
            )
            meals.append(MealPortion(name=name, share=share, macros=meal_macros))
        return meals


