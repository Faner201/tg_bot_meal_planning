from __future__ import annotations

from typing import Self, TypeVar

TId = TypeVar("TId")
TEntity = TypeVar("TEntity")


class InMemoryRepository[TId, TEntity]:
    """Минимальная in-memory реализация репозитория."""

    def __init__(self: Self) -> None:
        self._items: dict[TId, TEntity] = {}

    def get(self: Self, entity_id: TId) -> TEntity:
        try:
            return self._items[entity_id]
        except KeyError as exc:
            raise KeyError(f"Entity {entity_id!r} not found") from exc

    def save(self: Self, entity_id: TId, entity: TEntity) -> None:
        self._items[entity_id] = entity
