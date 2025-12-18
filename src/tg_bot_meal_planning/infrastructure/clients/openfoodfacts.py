from __future__ import annotations

import re
from typing import Any

import httpx

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.application.product_lookup import BarcodeLookupResult
from tg_bot_meal_planning.application.use_case import SyncUseCase
from tg_bot_meal_planning.domain.food_entry import MacroNutrients
from tg_bot_meal_planning.domain.product import Barcode, Product, ProductSource


class OpenFoodFactsLookup(SyncUseCase[Barcode, BarcodeLookupResult]):
    """Поиск товара по штрихкоду через OpenFoodFacts API."""

    def __init__(
        self,
        base_url: str = "https://world.openfoodfacts.org",
        timeout: float = 5.0,
        user_agent: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._user_agent = user_agent or "tg-bot-meal-planning/0.1"

    def execute(self, data: Barcode) -> BarcodeLookupResult:
        url = f"{self._base_url}/api/v2/product/{data}.json"
        try:
            response = httpx.get(url, timeout=self._timeout, headers={"User-Agent": self._user_agent})
        except httpx.HTTPError as exc:
            msg = f"Не удалось обратиться к OpenFoodFacts: {exc}"
            raise UseCaseError(msg) from exc
        except Exception as exc:  # noqa: BLE001 - защищаем от любых сетевых сбоев
            msg = f"Сбой при обращении к OpenFoodFacts: {exc}"
            raise UseCaseError(msg) from exc

        if response.status_code == 404:
            return BarcodeLookupResult(product=None, needs_manual_input=True, reason="товар не найден")

        try:
            payload = response.json()
        except ValueError as exc:
            raise UseCaseError("Некорректный ответ OpenFoodFacts: не JSON") from exc

        if payload.get("status") == 0:
            return BarcodeLookupResult(product=None, needs_manual_input=True, reason="товар не найден")

        product_data = payload.get("product") or {}
        name = _normalize_name(product_data, fallback=str(data))
        macros = _extract_macros(product_data.get("nutriments") or {})
        if macros is None:
            return BarcodeLookupResult(product=None, needs_manual_input=True, reason="нет данных о БЖУ")

        portion = _parse_portion(
            serving_quantity=product_data.get("serving_quantity"),
            serving_size=product_data.get("serving_size"),
        )

        product = Product(
            id=str(data),
            barcode=data,
            name=name,
            macros_per_100g=macros,
            portion_grams=portion,
            source=ProductSource.EXTERNAL,
        )
        return BarcodeLookupResult(product=product, needs_manual_input=False)


def _normalize_name(product_data: dict[str, Any], fallback: str) -> str:
    for key in ("product_name", "generic_name", "product_name_en", "product_name_ru"):
        value = product_data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"Штрихкод {fallback}"


def _extract_macros(nutriments: dict[str, Any]) -> MacroNutrients | None:
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    protein = _to_float(nutriments.get("proteins_100g"))
    fat = _to_float(nutriments.get("fat_100g"))
    carbs = _to_float(nutriments.get("carbohydrates_100g"))

    if protein is None or fat is None or carbs is None:
        return None

    return MacroNutrients(protein_g=protein, fat_g=fat, carbs_g=carbs)


def _parse_portion(serving_quantity: Any, serving_size: Any) -> float:
    """Вернуть размер порции в граммах, по умолчанию 100 г."""

    if serving_quantity is not None:
        try:
            portion = float(serving_quantity)
            if portion > 0:
                return portion
        except (TypeError, ValueError):
            pass

    if isinstance(serving_size, str):
        match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*g", serving_size.lower())
        if match:
            try:
                portion = float(match.group(1).replace(",", "."))
                if portion > 0:
                    return portion
            except ValueError:
                pass

    return 100.0


