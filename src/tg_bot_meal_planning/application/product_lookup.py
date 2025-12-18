from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tg_bot_meal_planning.domain.product import Product


@dataclass(frozen=True)
class BarcodeLookupResult:
    """Результат поиска товара по штрихкоду."""

    product: Product | None
    needs_manual_input: bool
    reason: str | None = None


