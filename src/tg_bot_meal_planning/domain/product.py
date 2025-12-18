from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Self

from tg_bot_meal_planning.domain.entities import Entity

if TYPE_CHECKING:
    from tg_bot_meal_planning.domain.food_entry import MacroNutrients


class ProductSource(str, Enum):
    MANUAL = "manual"
    EXTERNAL = "external"


class Barcode(str):
    def __new__(cls, value: str) -> Barcode:
        normalized = value.strip()
        if not normalized:
            raise ValueError("barcode не может быть пустым")
        if not normalized.isdigit():
            raise ValueError("barcode должен содержать только цифры")
        return str.__new__(cls, normalized)


@dataclass(frozen=True)
class Product(Entity[str]):
    barcode: Barcode
    name: str
    macros_per_100g: MacroNutrients
    portion_grams: float
    source: ProductSource

    def __post_init__(self: Self) -> None:
        super().__post_init__()
        if self.portion_grams <= 0:
            msg = "portion_grams должен быть положительным значением"
            raise ValueError(msg)


