from __future__ import annotations

from typing import TYPE_CHECKING

from tg_bot_meal_planning.infrastructure.repositories.in_memory import InMemoryRepository

if TYPE_CHECKING:
    from tg_bot_meal_planning.application.repositories import UserProfileRepository
    from tg_bot_meal_planning.domain.user_profile import UserProfile
else:  # pragma: no cover - используется только для аннотаций

    class UserProfileRepository:  # noqa: D401
        """Stub для рантайма."""

        pass

    class UserProfile:  # noqa: D401
        """Stub для рантайма."""

        id: str


class InMemoryUserProfileRepository(UserProfileRepository):
    """In-memory реализация хранилища профилей."""

    def __init__(self) -> None:
        self._storage: InMemoryRepository[str, UserProfile] = InMemoryRepository()

    def get(self, user_id: str) -> UserProfile | None:
        try:
            return self._storage.get(user_id)
        except KeyError:
            return None

    def save(self, profile: UserProfile) -> None:
        self._storage.save(profile.id, profile)
