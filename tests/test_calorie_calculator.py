from __future__ import annotations

import pytest

from tg_bot_meal_planning.domain.calorie_calculator import (
    CalorieCalculationInput,
    MifflinStJeorCalculator,
)
from tg_bot_meal_planning.domain.errors import ValidationError
from tg_bot_meal_planning.domain.user_profile import Gender, Goal


def test_mifflin_st_jeor_calculates_bmr_for_male() -> None:
    calculator = MifflinStJeorCalculator()
    data = CalorieCalculationInput(
        height_cm=175,
        weight_kg=70,
        age_years=30,
        gender=Gender.MALE,
        goal=Goal.MAINTAIN_WEIGHT,
    )

    result = calculator.execute(data)

    expected_bmr = (10 * 70) + (6.25 * 175) - (5 * 30) + 5
    assert result.basal_metabolic_rate == pytest.approx(expected_bmr)
    assert result.maintenance_calories == round(expected_bmr)
    assert result.goal_calories == result.maintenance_calories


def test_goal_multipliers_apply_deficit_and_surplus() -> None:
    calculator = MifflinStJeorCalculator(deficit_factor=0.8, surplus_factor=1.15)
    data = CalorieCalculationInput(
        height_cm=165,
        weight_kg=60,
        age_years=28,
        gender=Gender.FEMALE,
        goal=Goal.LOSE_WEIGHT,
    )

    result = calculator.execute(data)

    expected_bmr = (10 * 60) + (6.25 * 165) - (5 * 28) - 161
    maintenance = round(expected_bmr)
    assert result.goal_calories == round(maintenance * 0.8)

    gain_result = calculator.execute(
        CalorieCalculationInput(
            height_cm=165,
            weight_kg=60,
            age_years=28,
            gender=Gender.FEMALE,
            goal=Goal.GAIN_WEIGHT,
        )
    )
    assert gain_result.goal_calories == round(maintenance * 1.15)


def test_calculation_rejects_non_positive_fields() -> None:
    calculator = MifflinStJeorCalculator()

    with pytest.raises(ValidationError):
        calculator.execute(
            CalorieCalculationInput(
                height_cm=0,
                weight_kg=60,
                age_years=25,
                gender=Gender.MALE,
                goal=Goal.MAINTAIN_WEIGHT,
            )
        )

    with pytest.raises(ValidationError):
        calculator.execute(
            CalorieCalculationInput(
                height_cm=170,
                weight_kg=60,
                age_years=0,
                gender=Gender.FEMALE,
                goal=Goal.MAINTAIN_WEIGHT,
            )
        )






