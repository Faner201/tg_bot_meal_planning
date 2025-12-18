from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from tg_bot_meal_planning.domain.entities import Entity
from tg_bot_meal_planning.domain.errors import ValidationError

if TYPE_CHECKING:
    from tg_bot_meal_planning.domain.product import Barcode


@dataclass(frozen=True)
class ScannedBarcode(Entity[str]):
    """Фотография штрихкода, привязанная к пользователю."""

    user_id: str
    barcode: Barcode
    photo_path: str
    scanned_at: datetime

    def __post_init__(self: Self) -> None:
        super().__post_init__()
        if not self.user_id.strip():
            msg = "user_id обязателен"
            raise ValidationError(msg)
        if not self.photo_path.strip():
            msg = "photo_path не может быть пустым"
            raise ValidationError(msg)
        if self.scanned_at.tzinfo is None or self.scanned_at.tzinfo.utcoffset(self.scanned_at) is None:
            msg = "scanned_at должен быть aware datetime в UTC"
            raise ValidationError(msg)
        if self.scanned_at.tzinfo != UTC:
            msg = "scanned_at обязан быть в UTC"
            raise ValidationError(msg)


