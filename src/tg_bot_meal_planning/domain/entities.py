from __future__ import annotations

from dataclasses import dataclass
from typing import Self, TypeVar

EntityId = TypeVar("EntityId")


@dataclass(frozen=True)
class Entity[EntityId]:
    """Базовая неизменяемая сущность с идентификатором."""

    id: EntityId

    def __post_init__(self: Self) -> None:
        if self.id is None:
            msg = "Идентификатор сущности обязателен"
            raise ValueError(msg)
