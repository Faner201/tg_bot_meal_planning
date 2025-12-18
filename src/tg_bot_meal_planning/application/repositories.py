from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime

    from tg_bot_meal_planning.domain.barcode_scan import ScannedBarcode
    from tg_bot_meal_planning.domain.food_entry import FoodEntry
    from tg_bot_meal_planning.domain.user_profile import UserProfile


class FoodDiaryRepository(Protocol):
    """Интерфейс репозитория записей дневника питания."""

    def add(self, entry: FoodEntry) -> None:
        ...

    def list_entries(
        self,
        user_id: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> list[FoodEntry]:
        ...


class UserProfileRepository(Protocol):
    """Интерфейс репозитория профилей пользователей."""

    def get(self, user_id: str) -> UserProfile | None:
        ...

    def save(self, profile: UserProfile) -> None:
        ...


class ScannedBarcodeRepository(Protocol):
    """Интерфейс репозитория сохранённых штрихкодов и фото."""

    def save(self, scan: ScannedBarcode) -> None:
        ...


