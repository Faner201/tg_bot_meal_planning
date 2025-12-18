from __future__ import annotations

from typing import Protocol, Self, TypeVar

TInput = TypeVar("TInput", contravariant=True)
TOutput = TypeVar("TOutput", covariant=True)


class DomainService(Protocol[TInput, TOutput]):
    """Контракт доменного сервиса."""

    def execute(self: Self, data: TInput) -> TOutput: ...






