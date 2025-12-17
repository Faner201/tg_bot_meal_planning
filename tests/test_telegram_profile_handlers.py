from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tg_bot_meal_planning.application.user_profile import (
    GetUserProfile,
    RegisterUserProfile,
    RegisterUserProfileInput,
    UpdateUserProfile,
)
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, MacroTargets
from tg_bot_meal_planning.interface.telegram.handlers import (
    GetProfileHandler,
    ProfileRequest,
    UpdateWeightHandler,
    UpdateWeightRequest,
)

if TYPE_CHECKING:
    from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_user_profile import (
        SqlAlchemyUserProfileRepository,
    )


def _register_profile(repository: SqlAlchemyUserProfileRepository) -> None:
    register = RegisterUserProfile(repository)
    register.execute(
        RegisterUserProfileInput(
            user_id="user-1",
            height_cm=180,
            weight_kg=80,
            gender=Gender.MALE,
            goal=Goal.GAIN_WEIGHT,
            macro_targets=MacroTargets(protein_g=120, fat_g=60, carbs_g=200),
        )
    )


def test_get_profile_handler_formats_profile_text(
    user_profile_repo: SqlAlchemyUserProfileRepository,
) -> None:
    _register_profile(user_profile_repo)
    handler = GetProfileHandler(GetUserProfile(user_profile_repo))

    response = handler.handle(ProfileRequest(user_id="user-1"))

    assert response.profile.id == "user-1"
    assert "Рост: 180" in response.text
    assert "Вес: 80.0 кг" in response.text
    assert "Пол: male" in response.text
    assert "БЖУ: 120/60/200 г" in response.text


def test_update_weight_handler_updates_repository(
    user_profile_repo: SqlAlchemyUserProfileRepository,
) -> None:
    _register_profile(user_profile_repo)
    handler = UpdateWeightHandler(UpdateUserProfile(user_profile_repo))

    response = handler.handle(
        UpdateWeightRequest(user_id="user-1", weight_kg=72.5, goal=Goal.MAINTAIN_WEIGHT)
    )

    stored = user_profile_repo.get("user-1")

    assert stored is not None
    assert stored.weight_kg == pytest.approx(72.5)
    assert stored.goal is Goal.MAINTAIN_WEIGHT
    assert "Вес обновлён: 72.5 кг" in response.text
    assert "Текущая цель: maintain_weight" in response.text
