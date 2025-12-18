from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.application.use_case import SyncUseCase
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, MacroTargets, UserProfile

if TYPE_CHECKING:
    from tg_bot_meal_planning.application.repositories import UserProfileRepository


@dataclass(frozen=True)
class RegisterUserProfileInput:
    user_id: str
    height_cm: float
    weight_kg: float
    gender: Gender
    goal: Goal
    macro_targets: MacroTargets | None = None


@dataclass(frozen=True)
class UpdateUserProfileInput:
    user_id: str
    height_cm: float | None = None
    weight_kg: float | None = None
    gender: Gender | None = None
    goal: Goal | None = None
    macro_targets: MacroTargets | None = None


class RegisterUserProfile(SyncUseCase[RegisterUserProfileInput, UserProfile]):
    """Создать профиль пользователя."""

    def __init__(self, repository: UserProfileRepository) -> None:
        self._repository = repository

    def execute(self, data: RegisterUserProfileInput) -> UserProfile:
        if self._repository.get(data.user_id) is not None:
            msg = f"Профиль {data.user_id!r} уже существует"
            raise UseCaseError(msg)

        profile = UserProfile(
            id=data.user_id,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            gender=data.gender,
            goal=data.goal,
            macro_targets=data.macro_targets,
        )
        self._repository.save(profile)
        return profile


class UpdateUserProfile(SyncUseCase[UpdateUserProfileInput, UserProfile]):
    """Изменить данные профиля."""

    def __init__(self, repository: UserProfileRepository) -> None:
        self._repository = repository

    def execute(self, data: UpdateUserProfileInput) -> UserProfile:
        existing = self._repository.get(data.user_id)
        if existing is None:
            msg = f"Профиль {data.user_id!r} не найден"
            raise UseCaseError(msg)

        updated = existing.update(
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            gender=data.gender,
            goal=data.goal,
            macro_targets=data.macro_targets,
        )
        self._repository.save(updated)
        return updated


class GetUserProfile(SyncUseCase[str, UserProfile]):
    """Получить профиль пользователя."""

    def __init__(self, repository: UserProfileRepository) -> None:
        self._repository = repository

    def execute(self, data: str) -> UserProfile:
        profile = self._repository.get(data)
        if profile is None:
            msg = f"Профиль {data!r} не найден"
            raise UseCaseError(msg)
        return profile




