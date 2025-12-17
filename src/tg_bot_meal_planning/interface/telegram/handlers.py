from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, Self, TypeVar

if TYPE_CHECKING:
    from tg_bot_meal_planning.application.use_case import UseCase

Update = TypeVar("Update", contravariant=True)
Response = TypeVar("Response", covariant=True)


class Handler(Protocol[Update, Response]):
    """Контракт хендлера входящего обновления."""

    def handle(self: Self, update: Update) -> Response:
        """Обработать входящее событие."""
        ...


class UseCaseHandler[Update, Response]:
    """
    Простой адаптер: связывает Telegram-обновления с application use-case.
    """

    def __init__(self: Self, use_case: UseCase[Update, Response]) -> None:
        self._use_case = use_case

    def handle(self: Self, update: Update) -> Response:
        return self._use_case.execute(update)
