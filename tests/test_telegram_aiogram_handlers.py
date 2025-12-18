from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

import pytest
from aiogram.types import Chat, User

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, UserProfile
from tg_bot_meal_planning.interface.telegram.bot import (
    BotDependencies,
    build_router,
    handle_add_product,
    handle_barcode,
    handle_profile,
    handle_set_profile,
    handle_start,
    handle_weight,
)

if TYPE_CHECKING:
    from aiogram.types import Message

    from tg_bot_meal_planning.application.user_profile import (
        GetUserProfile,
        RegisterUserProfile,
        UpdateUserProfile,
    )
    from tg_bot_meal_planning.domain.product import Product


@dataclass
class DummyUseCase:
    return_value: Any = None
    raises: Exception | None = None
    last_input: Any = field(default=None, init=False)

    def execute(self, data: Any) -> Any:
        self.last_input = data
        if self.raises:
            raise self.raises
        return self.return_value


class DummyMessage:
    def __init__(self, text: str, user_id: int = 1) -> None:
        self.text = text
        self.from_user = User(id=user_id, is_bot=False, first_name="Test")
        self.chat = Chat(id=user_id, type="private")
        self.answers: list[str] = []

    async def answer(self, text: str) -> None:
        self.answers.append(text)


@pytest.fixture
def sample_profile() -> UserProfile:
    return UserProfile(
        id="1",
        height_cm=180,
        weight_kg=80,
        gender=Gender.MALE,
        goal=Goal.MAINTAIN_WEIGHT,
    )


@pytest.fixture
def sample_product() -> Product:
    from tg_bot_meal_planning.domain.food_entry import MacroNutrients
    from tg_bot_meal_planning.domain.product import Barcode, Product, ProductSource

    return Product(
        id="4601234567890",
        barcode=Barcode("4601234567890"),
        name="Творог",
        macros_per_100g=MacroNutrients(protein_g=18, fat_g=5, carbs_g=3),
        portion_grams=200,
        source=ProductSource.EXTERNAL,
    )


def _deps(
    get_uc: DummyUseCase,
    register_uc: DummyUseCase,
    update_uc: DummyUseCase,
    lookup_uc: DummyUseCase | None = None,
    save_product_uc: DummyUseCase | None = None,
) -> BotDependencies:
    return BotDependencies(
        register_profile=cast("RegisterUserProfile", register_uc),
        update_profile=cast("UpdateUserProfile", update_uc),
        get_profile=cast("GetUserProfile", get_uc),
        lookup_product=cast("Any", lookup_uc or DummyUseCase()),
        save_manual_product=cast("Any", save_product_uc or DummyUseCase()),
    )


@pytest.mark.asyncio
async def test_handle_start_sends_help() -> None:
    message = DummyMessage("/start")
    deps = _deps(DummyUseCase(), DummyUseCase(), DummyUseCase())

    await handle_start(cast("Message", message), deps)

    assert any("set_profile" in text for text in message.answers)


@pytest.mark.asyncio
async def test_handle_profile_returns_profile(sample_profile: UserProfile) -> None:
    message = DummyMessage("/profile")
    get_uc = DummyUseCase(return_value=sample_profile)
    deps = _deps(get_uc, DummyUseCase(), DummyUseCase())

    await handle_profile(cast("Message", message), deps)

    assert "Рост" in message.answers[0]
    assert "80.0 кг" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_profile_handles_error() -> None:
    message = DummyMessage("/profile")
    get_uc = DummyUseCase(raises=UseCaseError("not found"))
    deps = _deps(get_uc, DummyUseCase(), DummyUseCase())

    await handle_profile(cast("Message", message), deps)

    assert "Ошибка" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_set_profile_creates_when_absent() -> None:
    message = DummyMessage("/set_profile 180 75 male gain_weight")
    get_uc = DummyUseCase(raises=UseCaseError("missing"))
    register_uc = DummyUseCase()
    deps = _deps(get_uc, register_uc, DummyUseCase())

    await handle_set_profile(cast("Message", message), deps)

    assert register_uc.last_input.user_id == "1"
    assert "Профиль создан" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_set_profile_updates_when_exists(sample_profile: UserProfile) -> None:
    message = DummyMessage("/set_profile 181 76 female lose_weight")
    get_uc = DummyUseCase(return_value=sample_profile)
    update_uc = DummyUseCase(return_value=sample_profile)
    deps = _deps(get_uc, DummyUseCase(), update_uc)

    await handle_set_profile(cast("Message", message), deps)

    assert update_uc.last_input.weight_kg == 76
    assert "Профиль обновлён" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_weight_updates_weight(sample_profile: UserProfile) -> None:
    message = DummyMessage("/weight 72.5 maintain_weight")
    update_uc = DummyUseCase(return_value=sample_profile.update(weight_kg=72.5))
    deps = _deps(DummyUseCase(return_value=sample_profile), DummyUseCase(), update_uc)

    await handle_weight(cast("Message", message), deps)

    assert update_uc.last_input.weight_kg == 72.5
    assert "Вес обновлён" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_weight_validates_number(sample_profile: UserProfile) -> None:
    message = DummyMessage("/weight not_a_number")
    deps = _deps(DummyUseCase(return_value=sample_profile), DummyUseCase(), DummyUseCase())

    await handle_weight(cast("Message", message), deps)

    assert "Вес должен быть числом" in message.answers[0]


def test_build_router_registers_commands(sample_profile: UserProfile) -> None:
    deps = _deps(DummyUseCase(), DummyUseCase(), DummyUseCase(return_value=sample_profile))

    router = build_router(deps)

    commands: set[str] = set()
    for handler in router.message.handlers:
        for cmd in handler.flags.get("commands", []):
            raw_names = getattr(cmd, "commands", [])
            names = [raw_names] if isinstance(raw_names, str) else list(raw_names)
            commands.update(names)
    assert {"start", "profile", "set_profile", "weight", "barcode", "add_product"}.issubset(commands)


@pytest.mark.asyncio
async def test_handle_barcode_returns_product(sample_product: Product) -> None:
    message = DummyMessage("/barcode 4601234567890")
    lookup_uc = DummyUseCase(return_value=type("Result", (), {"product": sample_product, "needs_manual_input": False}))
    deps = _deps(DummyUseCase(), DummyUseCase(), DummyUseCase(), lookup_uc=lookup_uc)

    await handle_barcode(cast("Message", message), deps)

    assert "Товар" in message.answers[0]
    assert sample_product.name in message.answers[0]


@pytest.mark.asyncio
async def test_handle_barcode_requests_manual_input() -> None:
    message = DummyMessage("/barcode 000")
    result = type("Result", (), {"product": None, "needs_manual_input": True, "reason": "not_found"})
    deps = _deps(
        DummyUseCase(),
        DummyUseCase(),
        DummyUseCase(),
        lookup_uc=DummyUseCase(return_value=result),
    )

    await handle_barcode(cast("Message", message), deps)

    assert "Товар не найден" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_add_product_saves_product(sample_product: Product) -> None:
    text = "/add_product 4601234567890 200 18 5 3 Творог Домашний"
    message = DummyMessage(text)
    save_uc = DummyUseCase(return_value=sample_product)
    deps = _deps(DummyUseCase(), DummyUseCase(), DummyUseCase(), save_product_uc=save_uc)

    await handle_add_product(cast("Message", message), deps)

    assert save_uc.last_input.barcode == "4601234567890"
    assert "Сохранил продукт" in message.answers[0]

