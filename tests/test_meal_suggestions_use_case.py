from __future__ import annotations

import pytest

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.application.meal_suggestions import (
    MealSuggestionConfig,
    SuggestDailyPlan,
    SuggestDailyPlanInput,
)
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, UserProfile


def _profile(goal: Goal = Goal.MAINTAIN_WEIGHT) -> UserProfile:
    return UserProfile(
        id="user-1",
        height_cm=180,
        weight_kg=80,
        gender=Gender.MALE,
        goal=goal,
    )


def test_suggest_daily_plan_with_explicit_calories() -> None:
    profile = _profile(Goal.MAINTAIN_WEIGHT)
    use_case = SuggestDailyPlan()

    result = use_case.execute(SuggestDailyPlanInput(profile=profile, calories=2500))

    assert result.target_calories == 2500
    assert pytest.approx(result.target_macros.protein_g, rel=1e-3) == 144.0
    assert pytest.approx(result.target_macros.fat_g, rel=1e-3) == 72.0
    assert pytest.approx(result.target_macros.carbs_g, rel=1e-3) == 319.0

    total_protein = sum(meal.macros.protein_g for meal in result.meals)
    total_fat = sum(meal.macros.fat_g for meal in result.meals)
    total_carbs = sum(meal.macros.carbs_g for meal in result.meals)

    assert len(result.meals) == 4
    assert abs(sum(meal.share for meal in result.meals) - 1.0) < 0.02
    assert pytest.approx(total_protein, rel=1e-3) == result.target_macros.protein_g
    assert pytest.approx(total_fat, rel=1e-3) == result.target_macros.fat_g
    assert pytest.approx(total_carbs, rel=1e-3) == result.target_macros.carbs_g


def test_suggest_daily_plan_uses_calculator_when_no_calories() -> None:
    profile = _profile(Goal.LOSE_WEIGHT)
    use_case = SuggestDailyPlan()

    result = use_case.execute(SuggestDailyPlanInput(profile=profile, age_years=35))

    assert result.target_calories == 1492
    assert result.target_macros.protein_g > 0
    assert result.target_macros.fat_g > 0
    assert result.target_macros.carbs_g > 0


def test_rejects_too_low_calories() -> None:
    profile = _profile()
    use_case = SuggestDailyPlan()

    with pytest.raises(UseCaseError):
        use_case.execute(SuggestDailyPlanInput(profile=profile, calories=1000))


def test_invalid_meal_shares_are_rejected() -> None:
    config = MealSuggestionConfig(meal_shares={"single": 0.5})

    with pytest.raises(UseCaseError):
        SuggestDailyPlan(config=config)


