from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, Self, TypeVar

from tg_bot_meal_planning.application.user_profile import (
    GetUserProfile,
    UpdateUserProfile,
    UpdateUserProfileInput,
)
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, UserProfile

if TYPE_CHECKING:
    from tg_bot_meal_planning.application.use_case import UseCase
    from tg_bot_meal_planning.domain.food_entry import MacroNutrients
    from tg_bot_meal_planning.domain.user_profile import MacroTargets

Update = TypeVar("Update", contravariant=True)
Response = TypeVar("Response", covariant=True)


class Handler(Protocol[Update, Response]):
    """Контракт хендлера входящего обновления."""

    def handle(self: Self, update: Update) -> Response:
        """Обработать входящее событие."""
        ...


class UseCaseHandler[Update, Response]:
    """
    Простой адаптер: связывает Telegram-обновления с application use-case.
    """

    def __init__(self: Self, use_case: UseCase[Update, Response]) -> None:
        self._use_case = use_case

    def handle(self: Self, update: Update) -> Response:
        return self._use_case.execute(update)


@dataclass(frozen=True)
class ProfileRequest:
    """Запрос на получение профиля Telegram-пользователя."""

    user_id: str


@dataclass(frozen=True)
class ProfileResponse:
    """Ответ с текстом и моделью профиля."""

    profile: UserProfile
    text: str


class GetProfileHandler(Handler[ProfileRequest, ProfileResponse]):
    """Возвращает отформатированный профиль пользователя."""

    def __init__(self: Self, use_case: GetUserProfile) -> None:
        self._use_case = use_case

    def handle(self: Self, update: ProfileRequest) -> ProfileResponse:
        profile = self._use_case.execute(update.user_id)
        return ProfileResponse(profile=profile, text=_format_profile(profile))


@dataclass(frozen=True)
class UpdateWeightRequest:
    """Запрос на обновление веса и (опционально) цели."""

    user_id: str
    weight_kg: float
    goal: Goal | None = None


@dataclass(frozen=True)
class UpdateWeightResponse:
    """Ответ после изменения веса."""

    profile: UserProfile
    text: str


class UpdateWeightHandler(Handler[UpdateWeightRequest, UpdateWeightResponse]):
    """Меняет вес пользователя через use-case и возвращает ответ для бота."""

    def __init__(self: Self, use_case: UpdateUserProfile) -> None:
        self._use_case = use_case

    def handle(self: Self, update: UpdateWeightRequest) -> UpdateWeightResponse:
        profile = self._use_case.execute(
            UpdateUserProfileInput(
                user_id=update.user_id,
                weight_kg=update.weight_kg,
                goal=update.goal,
            )
        )
        text_lines = [
            f"Вес обновлён: {profile.weight_kg:.1f} кг",
            f"Текущая цель: {_goal_label(profile.goal)}",
            f"БЖУ: {_format_macro_targets(profile.macro_targets)}",
        ]
        return UpdateWeightResponse(profile=profile, text="\n".join(text_lines))


def _format_profile(profile: UserProfile) -> str:
    macro_targets = _format_macro_targets(profile.macro_targets)
    return (
        "Профиль пользователя:\n"
        f"- Рост: {profile.height_cm:.0f} см\n"
        f"- Вес: {profile.weight_kg:.1f} кг\n"
        f"- Пол: {_gender_label(profile.gender)}\n"
        f"- Цель: {_goal_label(profile.goal)}\n"
        f"- БЖУ: {macro_targets}"
    )


def _format_macro_targets(macro_targets: MacroTargets | MacroNutrients | None) -> str:
    if macro_targets is None:
        return "не задано"
    return (
        f"{macro_targets.protein_g:.0f}/"
        f"{macro_targets.fat_g:.0f}/"
        f"{macro_targets.carbs_g:.0f} г"
    )


def _goal_label(goal: Goal) -> str:
    return {
        Goal.LOSE_WEIGHT: "похудение",
        Goal.MAINTAIN_WEIGHT: "поддержание",
        Goal.GAIN_WEIGHT: "набор",
    }[goal]


def _gender_label(gender: Gender) -> str:
    return {
        Gender.MALE: "мужской",
        Gender.FEMALE: "женский",
    }[gender]


