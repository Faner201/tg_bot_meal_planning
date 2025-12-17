from tg_bot_meal_planning.domain.errors import DomainError


class UseCaseError(DomainError):
    """Базовая ошибка сценария использования."""
