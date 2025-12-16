from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, Self

if TYPE_CHECKING:
    from tg_bot_meal_planning.domain.user_profile import UserProfile


class UserProfileRepository(Protocol):
    """Контракт хранилища профилей пользователей."""

    def get(self: Self, user_id: str) -> UserProfile | None: ...

    def save(self: Self, profile: UserProfile) -> None: ...



