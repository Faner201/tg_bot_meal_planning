from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tg_bot_meal_planning.application.calorie import CalculateCalories, CalculateCaloriesInput
from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, UserProfile

if TYPE_CHECKING:
    from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_user_profile import (
        SqlAlchemyUserProfileRepository,
    )


@pytest.fixture
def repository(user_profile_repo: SqlAlchemyUserProfileRepository) -> SqlAlchemyUserProfileRepository:
    repo = user_profile_repo
    profile = UserProfile(
        id="user-1",
        height_cm=180,
        weight_kg=80,
        gender=Gender.MALE,
        goal=Goal.LOSE_WEIGHT,
    )
    repo.save(profile)
    return repo


def test_calculate_calories_returns_goal_adjusted_value(
    repository: SqlAlchemyUserProfileRepository,
) -> None:
    use_case = CalculateCalories(repository)

    result = use_case.execute(CalculateCaloriesInput(user_id="user-1", age_years=35))

    assert result.goal is Goal.LOSE_WEIGHT
    assert result.goal_calories == 1492
    assert result.maintenance_calories == 1755


def test_calculate_calories_rejects_missing_profile(
    user_profile_repo: SqlAlchemyUserProfileRepository,
) -> None:
    use_case = CalculateCalories(user_profile_repo)

    with pytest.raises(UseCaseError):
        use_case.execute(CalculateCaloriesInput(user_id="missing", age_years=30))


def test_calculate_calories_rejects_invalid_age(repository: SqlAlchemyUserProfileRepository) -> None:
    use_case = CalculateCalories(repository)

    with pytest.raises(UseCaseError):
        use_case.execute(CalculateCaloriesInput(user_id="user-1", age_years=0))


