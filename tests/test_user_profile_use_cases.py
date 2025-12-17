from __future__ import annotations

import pytest

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.application.user_profile import (
    GetUserProfile,
    RegisterUserProfile,
    RegisterUserProfileInput,
    UpdateUserProfile,
    UpdateUserProfileInput,
)
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, MacroTargets
from tg_bot_meal_planning.infrastructure.repositories.user_profile import InMemoryUserProfileRepository


@pytest.fixture
def repository() -> InMemoryUserProfileRepository:
    return InMemoryUserProfileRepository()


def test_register_creates_profile(repository: InMemoryUserProfileRepository) -> None:
    use_case = RegisterUserProfile(repository)
    profile = use_case.execute(
        RegisterUserProfileInput(
            user_id="user-1",
            height_cm=175,
            weight_kg=72,
            gender=Gender.MALE,
            goal=Goal.MAINTAIN_WEIGHT,
            macro_targets=MacroTargets(protein_g=120, fat_g=60, carbs_g=200),
        )
    )

    stored = repository.get("user-1")
    assert stored == profile


def test_register_rejects_duplicate(repository: InMemoryUserProfileRepository) -> None:
    use_case = RegisterUserProfile(repository)
    use_case.execute(
        RegisterUserProfileInput(
            user_id="user-1",
            height_cm=170,
            weight_kg=70,
            gender=Gender.FEMALE,
            goal=Goal.LOSE_WEIGHT,
        )
    )

    with pytest.raises(UseCaseError):
        use_case.execute(
            RegisterUserProfileInput(
                user_id="user-1",
                height_cm=170,
                weight_kg=70,
                gender=Gender.FEMALE,
                goal=Goal.LOSE_WEIGHT,
            )
        )


def test_update_changes_fields(repository: InMemoryUserProfileRepository) -> None:
    register = RegisterUserProfile(repository)
    register.execute(
        RegisterUserProfileInput(
            user_id="user-1",
            height_cm=170,
            weight_kg=70,
            gender=Gender.FEMALE,
            goal=Goal.LOSE_WEIGHT,
        )
    )
    update = UpdateUserProfile(repository)

    updated = update.execute(
        UpdateUserProfileInput(
            user_id="user-1",
            weight_kg=68,
            goal=Goal.MAINTAIN_WEIGHT,
            macro_targets=MacroTargets(protein_g=110, fat_g=55, carbs_g=180),
        )
    )

    assert updated.weight_kg == 68
    assert updated.goal is Goal.MAINTAIN_WEIGHT
    assert updated.macro_targets == MacroTargets(protein_g=110, fat_g=55, carbs_g=180)


def test_update_missing_profile(repository: InMemoryUserProfileRepository) -> None:
    update = UpdateUserProfile(repository)

    with pytest.raises(UseCaseError):
        update.execute(UpdateUserProfileInput(user_id="unknown", weight_kg=80))


def test_get_profile(repository: InMemoryUserProfileRepository) -> None:
    register = RegisterUserProfile(repository)
    register.execute(
        RegisterUserProfileInput(
            user_id="user-1",
            height_cm=180,
            weight_kg=80,
            gender=Gender.MALE,
            goal=Goal.GAIN_WEIGHT,
        )
    )
    get_profile = GetUserProfile(repository)

    profile = get_profile.execute("user-1")

    assert profile.id == "user-1"
    assert profile.goal is Goal.GAIN_WEIGHT


def test_get_profile_missing(repository: InMemoryUserProfileRepository) -> None:
    get_profile = GetUserProfile(repository)

    with pytest.raises(UseCaseError):
        get_profile.execute("unknown")
