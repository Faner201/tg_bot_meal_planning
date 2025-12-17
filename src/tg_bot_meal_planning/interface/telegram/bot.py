from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.application.user_profile import (
    GetUserProfile,
    RegisterUserProfile,
    RegisterUserProfileInput,
    UpdateUserProfile,
    UpdateUserProfileInput,
)
from tg_bot_meal_planning.domain.user_profile import Gender, Goal
from tg_bot_meal_planning.interface.telegram.handlers import _format_macro_targets, _format_profile

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import Message


@dataclass(frozen=True)
class BotDependencies:
    """Набор use-case для Telegram-бота."""

    register_profile: RegisterUserProfile
    update_profile: UpdateUserProfile
    get_profile: GetUserProfile


def build_router(deps: BotDependencies) -> Router:
    """Создать и настроить aiogram Router."""

    router = Router()

    router.message.register(_wrap(deps, handle_start), Command("start"))
    router.message.register(_wrap(deps, handle_profile), Command("profile"))
    router.message.register(_wrap(deps, handle_set_profile), Command("set_profile"))
    router.message.register(_wrap(deps, handle_weight), Command("weight"))

    return router


def _wrap(
    deps: BotDependencies,
    handler: Callable[[Message, BotDependencies], Awaitable[None]],
) -> Callable[[Message], Awaitable[None]]:
    async def _inner(message: Message) -> None:  # pragma: no cover - обёртка
        await handler(message, deps)

    return _inner


async def handle_start(message: Message, deps: BotDependencies) -> None:
    """Ответить приветствием и подсказать команды."""

    text = (
        "Привет! Я помогу вести профиль и считать калории.\n"
        "Команды:\n"
        "- /set_profile <рост> <вес> <gender> <goal>\n"
        "- /profile — посмотреть текущий профиль\n"
        "- /weight <вес> [goal] — обновить вес и цель (опционально)"
    )
    await message.answer(text)


async def handle_profile(message: Message, deps: BotDependencies) -> None:
    """Показать текущий профиль пользователя."""

    user_id = _user_id(message)
    try:
        profile = deps.get_profile.execute(user_id)
    except UseCaseError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    await message.answer(_format_profile(profile))


async def handle_set_profile(message: Message, deps: BotDependencies) -> None:
    """Создать или обновить профиль из аргументов команды."""

    text = message.text or ""
    tokens = text.split()
    if len(tokens) < 5:
        await message.answer("Использование: /set_profile <рост> <вес> <gender> <goal>")
        return

    _, height_raw, weight_raw, gender_raw, goal_raw = tokens[:5]
    try:
        height = float(height_raw)
        weight = float(weight_raw)
        gender = _parse_gender(gender_raw)
        goal = _parse_goal(goal_raw)
    except ValueError as exc:
        await message.answer(f"Ошибка ввода: {exc}")
        return

    user_id = _user_id(message)

    try:
        existing = deps.get_profile.execute(user_id)
    except UseCaseError:
        existing = None

    if existing is None:
        deps.register_profile.execute(
            RegisterUserProfileInput(
                user_id=user_id,
                height_cm=height,
                weight_kg=weight,
                gender=gender,
                goal=goal,
                macro_targets=None,
            )
        )
        await message.answer("Профиль создан.")
    else:
        updated = deps.update_profile.execute(
            UpdateUserProfileInput(
                user_id=user_id,
                height_cm=height,
                weight_kg=weight,
                gender=gender,
                goal=goal,
                macro_targets=existing.macro_targets,
            )
        )
        await message.answer(f"Профиль обновлён.\n{_format_profile(updated)}")


async def handle_weight(message: Message, deps: BotDependencies) -> None:
    """Обновить вес (и при необходимости цель)."""

    text = message.text or ""
    tokens = text.split()
    if len(tokens) < 2:
        await message.answer("Использование: /weight <вес> [goal]")
        return

    _, weight_raw, *rest = tokens
    try:
        weight = float(weight_raw)
    except ValueError:
        await message.answer("Вес должен быть числом.")
        return

    goal = None
    if rest:
        try:
            goal = _parse_goal(rest[0])
        except ValueError as exc:
            await message.answer(f"Ошибка ввода цели: {exc}")
            return

    user_id = _user_id(message)
    try:
        updated = deps.update_profile.execute(
            UpdateUserProfileInput(user_id=user_id, weight_kg=weight, goal=goal)
        )
    except UseCaseError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    text_lines = [
        f"Вес обновлён: {updated.weight_kg:.1f} кг",
        f"Текущая цель: {updated.goal.value}",
        f"БЖУ: {_format_macro_targets(updated.macro_targets)}",
    ]
    await message.answer("\n".join(text_lines))


def _parse_gender(raw: str) -> Gender:
    try:
        return Gender(raw.lower())
    except ValueError as exc:
        raise ValueError("gender должен быть male или female") from exc


def _parse_goal(raw: str) -> Goal:
    try:
        return Goal(raw.lower())
    except ValueError as exc:
        raise ValueError("goal должен быть lose_weight/maintain_weight/gain_weight") from exc


def _user_id(message: Message) -> str:
    return str(message.from_user.id if message.from_user else message.chat.id)
