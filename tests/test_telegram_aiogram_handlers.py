from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import pytest
from aiogram.types import Chat, ReplyKeyboardRemove, User

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.domain.product import Barcode
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, UserProfile
from tg_bot_meal_planning.interface.telegram.bot import (
    BotDependencies,
    build_router,
    handle_add_food_entry,
    handle_add_product,
    handle_barcode,
    handle_barcode_photo,
    handle_calories,
    handle_list_food_entries,
    handle_profile,
    handle_set_profile,
    handle_start,
    handle_suggest_plan,
    handle_summary_day,
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
        self.markups: list[Any] = []

    async def answer(self, text: str, **kwargs: Any) -> None:
        self.answers.append(text)
        if "reply_markup" in kwargs:
            self.markups.append(kwargs["reply_markup"])


class _DummyFile:
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path


class _DummyBot:
    def __init__(self, content: bytes) -> None:
        self._content = content

    async def get_file(self, file_id: str) -> _DummyFile:
        return _DummyFile(file_id)

    async def download_file(self, file_path: str, destination: Any) -> None:
        destination.write(self._content)


class _DummyPhoto:
    def __init__(self, file_id: str, mime_type: str | None = None) -> None:
        self.file_id = file_id
        self.file_unique_id = f"{file_id}_u"
        self.mime_type = mime_type


class DummyPhotoMessage(DummyMessage):
    def __init__(self, content: bytes, user_id: int = 1, mime_type: str = "image/jpeg") -> None:
        super().__init__("", user_id=user_id)
        self.photo = [_DummyPhoto("file_id", mime_type)]
        self.document = None
        self.bot = _DummyBot(content)


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
    calories_uc: DummyUseCase | None = None,
    suggest_uc: DummyUseCase | None = None,
    aggregate_uc: DummyUseCase | None = None,
    add_food_entry_uc: DummyUseCase | None = None,
    list_food_entries_uc: DummyUseCase | None = None,
    decode_uc: DummyUseCase | None = None,
    save_photo_uc: DummyUseCase | None = None,
    save_scan_uc: DummyUseCase | None = None,
) -> BotDependencies:
    return BotDependencies(
        register_profile=cast("RegisterUserProfile", register_uc),
        update_profile=cast("UpdateUserProfile", update_uc),
        get_profile=cast("GetUserProfile", get_uc),
        calculate_calories=cast("Any", calories_uc or DummyUseCase()),
        suggest_daily_plan=cast("Any", suggest_uc or DummyUseCase()),
        aggregate_food_diary=cast("Any", aggregate_uc or DummyUseCase()),
        add_food_entry=cast("Any", add_food_entry_uc or DummyUseCase()),
        list_food_entries=cast("Any", list_food_entries_uc or DummyUseCase()),
        lookup_product=cast("Any", lookup_uc or DummyUseCase()),
        save_manual_product=cast("Any", save_product_uc or DummyUseCase()),
        decode_barcode_image=cast("Any", decode_uc or DummyUseCase()),
        save_barcode_photo=cast("Any", save_photo_uc or DummyUseCase(return_value="var/photos/test.jpg")),
        save_scanned_barcode=cast("Any", save_scan_uc or DummyUseCase()),
    )


@pytest.mark.asyncio
async def test_handle_start_sends_help() -> None:
    message = DummyMessage("/start")
    deps = _deps(DummyUseCase(), DummyUseCase(), DummyUseCase())

    await handle_start(cast("Message", message), deps)

    assert any("бот для планирования питания" in text.lower() for text in message.answers)
    assert isinstance(message.markups[0], ReplyKeyboardRemove)


@pytest.mark.asyncio
async def test_handle_add_food_entry_saves_entry() -> None:
    from tg_bot_meal_planning.domain.food_entry import FoodEntry, MacroNutrients

    entry = FoodEntry(
        id="1",
        user_id="1",
        title="Омлет",
        portion_grams=150,
        macros_per_100g=MacroNutrients(10, 5, 20),
        taken_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
    )
    uc = DummyUseCase(return_value=entry)
    message = DummyMessage("/add_food_entry 150 10 5 20 Омлет")
    deps = _deps(DummyUseCase(), DummyUseCase(), DummyUseCase(), add_food_entry_uc=uc)

    await handle_add_food_entry(cast("Message", message), deps)

    assert uc.last_input.portion_grams == 150
    assert "Запись добавлена" in message.answers[0]
    assert "Омлет" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_list_food_entries_returns_entries() -> None:
    from tg_bot_meal_planning.domain.food_entry import FoodEntry, MacroNutrients

    entries = [
        FoodEntry(
            id="1",
            user_id="1",
            title="Овсянка",
            portion_grams=100,
            macros_per_100g=MacroNutrients(5, 3, 20),
            taken_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        ),
        FoodEntry(
            id="2",
            user_id="1",
            title="Курица",
            portion_grams=200,
            macros_per_100g=MacroNutrients(30, 5, 0),
            taken_at_utc=datetime(2024, 1, 1, 12, tzinfo=UTC),
        ),
    ]
    uc = DummyUseCase(return_value=entries)
    message = DummyMessage("/list_food_entries week")
    deps = _deps(DummyUseCase(), DummyUseCase(), DummyUseCase(), list_food_entries_uc=uc)

    await handle_list_food_entries(cast("Message", message), deps)

    assert "Записи питания" in message.answers[0]
    assert "Овсянка" in message.answers[0]
    assert "Курица" in message.answers[0]
    assert "Итого" in message.answers[0]


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

    assert "Профиль не найден" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_set_profile_creates_when_absent() -> None:
    message = DummyMessage("/set_profile 180 75 мужской набор")
    get_uc = DummyUseCase(raises=UseCaseError("missing"))
    register_uc = DummyUseCase()
    deps = _deps(get_uc, register_uc, DummyUseCase())

    await handle_set_profile(cast("Message", message), deps)

    assert register_uc.last_input.user_id == "1"
    assert register_uc.last_input.gender is Gender.MALE
    assert "Профиль создан" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_set_profile_updates_when_exists(sample_profile: UserProfile) -> None:
    message = DummyMessage("/set_profile 181 76 женский похудение")
    get_uc = DummyUseCase(return_value=sample_profile)
    update_uc = DummyUseCase(return_value=sample_profile)
    deps = _deps(get_uc, DummyUseCase(), update_uc)

    await handle_set_profile(cast("Message", message), deps)

    assert update_uc.last_input.weight_kg == 76
    assert "Профиль обновлён" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_set_profile_rejects_unknown_gender() -> None:
    message = DummyMessage("/set_profile 180 75 другой набор")
    get_uc = DummyUseCase(raises=UseCaseError("missing"))
    deps = _deps(get_uc, DummyUseCase(), DummyUseCase())

    await handle_set_profile(cast("Message", message), deps)

    assert "Ошибка ввода: пол должен быть" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_weight_updates_weight(sample_profile: UserProfile) -> None:
    message = DummyMessage("/weight 72.5 поддержание")
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


@pytest.mark.asyncio
async def test_handle_weight_requires_profile() -> None:
    message = DummyMessage("/weight 70")
    get_uc = DummyUseCase(raises=UseCaseError("missing"))
    deps = _deps(get_uc, DummyUseCase(), DummyUseCase())

    await handle_weight(cast("Message", message), deps)

    assert "Профиль не найден" in message.answers[0]


def test_build_router_registers_commands(sample_profile: UserProfile) -> None:
    deps = _deps(DummyUseCase(), DummyUseCase(), DummyUseCase(return_value=sample_profile))

    router = build_router(deps)

    commands: set[str] = set()
    for handler in router.message.handlers:
        for cmd in handler.flags.get("commands", []):
            raw_names = getattr(cmd, "commands", [])
            names = [raw_names] if isinstance(raw_names, str) else list(raw_names)
            commands.update(names)
    assert {
        "start",
        "profile",
        "set_profile",
        "weight",
        "add_food_entry",
        "list_food_entries",
        "barcode",
        "add_product",
        "calories",
        "suggest_plan",
        "summary_day",
        "summary_week",
        "summary_month",
    }.issubset(commands)


@pytest.mark.asyncio
async def test_handle_barcode_returns_product(sample_product: Product, sample_profile: UserProfile) -> None:
    message = DummyMessage("/barcode 4601234567890")
    lookup_uc = DummyUseCase(return_value=type("Result", (), {"product": sample_product, "needs_manual_input": False}))
    deps = _deps(DummyUseCase(return_value=sample_profile), DummyUseCase(), DummyUseCase(), lookup_uc=lookup_uc)

    await handle_barcode(cast("Message", message), deps)

    assert "Товар" in message.answers[0]
    assert sample_product.name in message.answers[0]


@pytest.mark.asyncio
async def test_handle_barcode_requests_manual_input(sample_profile: UserProfile) -> None:
    message = DummyMessage("/barcode 000")
    result = type("Result", (), {"product": None, "needs_manual_input": True, "reason": "not_found"})
    deps = _deps(
        DummyUseCase(return_value=sample_profile),
        DummyUseCase(),
        DummyUseCase(),
        lookup_uc=DummyUseCase(return_value=result),
    )

    await handle_barcode(cast("Message", message), deps)

    assert "Товар не найден" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_barcode_photo_processes_image(
    sample_product: Product, sample_profile: UserProfile
) -> None:
    message = DummyPhotoMessage(b"image-bytes")
    decode_uc = DummyUseCase(return_value=Barcode("4601234567890"))
    save_photo_uc = DummyUseCase(return_value="var/photos/1/4601234567890.jpg")
    save_scan_uc = DummyUseCase()
    lookup_uc = DummyUseCase(return_value=type("Result", (), {"product": sample_product, "needs_manual_input": False}))
    deps = _deps(
        DummyUseCase(return_value=sample_profile),
        DummyUseCase(),
        DummyUseCase(),
        lookup_uc=lookup_uc,
        decode_uc=decode_uc,
        save_photo_uc=save_photo_uc,
        save_scan_uc=save_scan_uc,
    )

    await handle_barcode_photo(cast("Message", message), deps)

    assert "Товар" in message.answers[0]
    assert "Фото сохранено" in message.answers[0]
    assert save_photo_uc.last_input.user_id == "1"
    assert save_scan_uc.last_input.barcode == Barcode("4601234567890")


@pytest.mark.asyncio
async def test_handle_barcode_photo_reports_decode_error(sample_profile: UserProfile) -> None:
    message = DummyPhotoMessage(b"image-bytes")
    decode_uc = DummyUseCase(raises=UseCaseError("not_found"))
    deps = _deps(
        DummyUseCase(return_value=sample_profile),
        DummyUseCase(),
        DummyUseCase(),
        decode_uc=decode_uc,
    )

    await handle_barcode_photo(cast("Message", message), deps)

    assert "Не удалось распознать штрихкод" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_add_product_saves_product(sample_product: Product, sample_profile: UserProfile) -> None:
    text = "/add_product 4601234567890 200 18 5 3 Творог Домашний"
    message = DummyMessage(text)
    save_uc = DummyUseCase(return_value=sample_product)
    deps = _deps(
        DummyUseCase(return_value=sample_profile),
        DummyUseCase(),
        DummyUseCase(),
        save_product_uc=save_uc,
    )

    await handle_add_product(cast("Message", message), deps)

    assert save_uc.last_input.barcode == "4601234567890"
    assert "Сохранил продукт" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_calories_returns_values(sample_profile: UserProfile) -> None:
    message = DummyMessage("/calories 30")
    get_uc = DummyUseCase(return_value=sample_profile)
    result = type(
        "CalorieResult",
        (),
        {"basal_metabolic_rate": 1600.0, "maintenance_calories": 1800, "goal_calories": 1700, "goal": sample_profile.goal},
    )
    calories_uc = DummyUseCase(return_value=result)
    deps = _deps(get_uc, DummyUseCase(), DummyUseCase(), calories_uc=calories_uc)

    await handle_calories(cast("Message", message), deps)

    assert "Расчёт калорий" in message.answers[0]
    assert "1700" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_suggest_plan_returns_meals(sample_profile: UserProfile) -> None:
    message = DummyMessage("/suggest_plan 30 2000")
    get_uc = DummyUseCase(return_value=sample_profile)
    from tg_bot_meal_planning.domain.food_entry import MacroNutrients

    meals = [
        type("Meal", (), {"name": "breakfast", "macros": MacroNutrients(10, 5, 20), "calories_kcal": 10.0}),
        type("Meal", (), {"name": "lunch", "macros": MacroNutrients(15, 6, 25), "calories_kcal": 20.0}),
    ]
    result = type(
        "PlanResult",
        (),
        {"target_calories": 1900, "target_macros": MacroNutrients(100, 60, 200), "meals": meals},
    )
    suggest_uc = DummyUseCase(return_value=result)
    deps = _deps(get_uc, DummyUseCase(), DummyUseCase(), suggest_uc=suggest_uc)

    await handle_suggest_plan(cast("Message", message), deps)

    assert "Рекомендации" in message.answers[0]
    assert "1900" in message.answers[0]
    assert "breakfast" in message.answers[0]


@pytest.mark.asyncio
async def test_handle_summary_day_returns_aggregate(sample_profile: UserProfile) -> None:
    message = DummyMessage("/summary_day")
    get_uc = DummyUseCase(return_value=sample_profile)
    from tg_bot_meal_planning.domain.food_entry import MacroNutrients

    aggregate_uc = DummyUseCase(return_value=MacroNutrients(30, 20, 50))
    deps = _deps(get_uc, DummyUseCase(), DummyUseCase(), aggregate_uc=aggregate_uc)

    await handle_summary_day(cast("Message", message), deps)

    assert "Агрегация за день" in message.answers[0]
    assert "БЖУ" in message.answers[0]

