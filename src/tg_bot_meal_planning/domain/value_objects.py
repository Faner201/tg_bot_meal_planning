from __future__ import annotations

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class ValueObject:
    """Абстракция для неизменяемых value object'ов."""

    def validate(self: Self) -> None:
        """Хук для валидации конкретных объектов."""
        return
