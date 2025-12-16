from __future__ import annotations

import pytest

from tg_bot_meal_planning.domain.errors import ValidationError
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, MacroTargets, UserProfile


def test_macro_targets_validation() -> None:
    with pytest.raises(ValidationError):
        MacroTargets(protein_g=-1, fat_g=10, carbs_g=20)


def test_create_profile_validates_fields() -> None:
    with pytest.raises(ValidationError):
        UserProfile(
            id="user-1",
            height_cm=0,
            weight_kg=70,
            gender=Gender.MALE,
            goal=Goal.MAINTAIN_WEIGHT,
        )


def test_update_profile_returns_new_instance() -> None:
    profile = UserProfile(
        id="user-1",
        height_cm=180,
        weight_kg=80,
        gender=Gender.MALE,
        goal=Goal.MAINTAIN_WEIGHT,
        macro_targets=MacroTargets(protein_g=130, fat_g=70, carbs_g=220),
    )

    updated = profile.update(weight_kg=78, goal=Goal.LOSE_WEIGHT)

    assert updated.weight_kg == 78
    assert updated.goal is Goal.LOSE_WEIGHT
    assert updated.height_cm == profile.height_cm
    assert updated.macro_targets == profile.macro_targets



