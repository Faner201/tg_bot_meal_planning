from __future__ import annotations

from typing import Protocol, Self, TypeVar

Input = TypeVar("Input", contravariant=True)
Output = TypeVar("Output", covariant=True)


class UseCase(Protocol[Input, Output]):
    """Контракт любого application use-case."""

    def execute(self: Self, data: Input) -> Output:
        """Выполнить бизнес-сценарий."""
        ...


class SyncUseCase[Input, Output]:
    """Базовая синхронная реализация use-case."""

    def execute(self: Self, data: Input) -> Output:  # pragma: no cover - примеры переопределяются
        raise NotImplementedError




