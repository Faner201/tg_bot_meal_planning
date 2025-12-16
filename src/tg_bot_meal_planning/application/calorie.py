from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.application.use_case import SyncUseCase
from tg_bot_meal_planning.domain.calorie_calculator import (
    CalorieCalculationInput,
    CalorieCalculationResult,
    MifflinStJeorCalculator,
)
from tg_bot_meal_planning.domain.errors import ValidationError

if TYPE_CHECKING:
    from tg_bot_meal_planning.application.repositories import UserProfileRepository


@dataclass(frozen=True)
class CalculateCaloriesInput:
    user_id: str
    age_years: int


class CalculateCalories(SyncUseCase[CalculateCaloriesInput, CalorieCalculationResult]):
    """Расчёт суточной нормы калорий для пользователя."""

    def __init__(
        self,
        repository: UserProfileRepository,
        calculator: MifflinStJeorCalculator | None = None,
    ) -> None:
        self._repository = repository
        self._calculator = calculator or MifflinStJeorCalculator()

    def execute(self, data: CalculateCaloriesInput) -> CalorieCalculationResult:
        if data.age_years <= 0:
            msg = "age_years должен быть положительным"
            raise UseCaseError(msg)

        profile = self._repository.get(data.user_id)
        if profile is None:
            msg = f"Профиль {data.user_id!r} не найден"
            raise UseCaseError(msg)

        calculation_input = CalorieCalculationInput(
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            age_years=data.age_years,
            gender=profile.gender,
            goal=profile.goal,
        )

        try:
            return self._calculator.execute(calculation_input)
        except ValidationError as exc:
            raise UseCaseError(str(exc)) from exc



