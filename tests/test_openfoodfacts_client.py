from __future__ import annotations

import pytest

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.domain.product import Barcode
from tg_bot_meal_planning.infrastructure.clients.openfoodfacts import OpenFoodFactsLookup


class DummyResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        if self._payload is None:
            raise ValueError("no payload")
        return self._payload


@pytest.fixture
def barcode() -> Barcode:
    return Barcode("4601234567890")


def test_lookup_returns_product(monkeypatch: pytest.MonkeyPatch, barcode: Barcode) -> None:
    payload = {
        "status": 1,
        "product": {
            "product_name": "Творог",
            "serving_quantity": 200,
            "nutriments": {
                "proteins_100g": 18,
                "fat_100g": 5,
                "carbohydrates_100g": 3,
            },
        },
    }

    def fake_get(url: str, timeout: float, headers: dict[str, str]) -> DummyResponse:
        return DummyResponse(status_code=200, payload=payload)

    monkeypatch.setattr(
        "tg_bot_meal_planning.infrastructure.clients.openfoodfacts.httpx.get",
        fake_get,
    )

    result = OpenFoodFactsLookup().execute(barcode)

    assert not result.needs_manual_input
    assert result.product is not None
    assert result.product.name == "Творог"
    assert result.product.macros_per_100g.protein_g == 18
    assert result.product.portion_grams == 200


def test_lookup_without_macros_requests_manual_input(
    monkeypatch: pytest.MonkeyPatch,
    barcode: Barcode,
) -> None:
    payload = {"status": 1, "product": {"product_name": "Пустой продукт", "nutriments": {}}}

    def fake_get(url: str, timeout: float, headers: dict[str, str]) -> DummyResponse:
        return DummyResponse(status_code=200, payload=payload)

    monkeypatch.setattr(
        "tg_bot_meal_planning.infrastructure.clients.openfoodfacts.httpx.get",
        fake_get,
    )

    result = OpenFoodFactsLookup().execute(barcode)

    assert result.needs_manual_input
    assert result.reason == "нет данных о БЖУ"


def test_lookup_raises_on_http_error(monkeypatch: pytest.MonkeyPatch, barcode: Barcode) -> None:
    def fake_get(url: str, timeout: float, headers: dict[str, str]) -> DummyResponse:
        raise Exception("boom")

    monkeypatch.setattr(
        "tg_bot_meal_planning.infrastructure.clients.openfoodfacts.httpx.get",
        fake_get,
    )

    lookup = OpenFoodFactsLookup()

    with pytest.raises(UseCaseError):
        lookup.execute(barcode)


