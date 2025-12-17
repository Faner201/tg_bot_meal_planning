class DomainError(Exception):
    """Базовая ошибка доменного слоя."""


class ValidationError(DomainError):
    """Ошибка бизнес-валидации."""



