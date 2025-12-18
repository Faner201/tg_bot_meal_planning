from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import TYPE_CHECKING, Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove

from tg_bot_meal_planning.application.barcode_scanning import (
    SaveBarcodePhotoInput,
    SaveScannedBarcodeInput,
)
from tg_bot_meal_planning.application.calorie import CalculateCaloriesInput, CalorieCalculationResult
from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.application.food_diary import (
    AddFoodEntryInput,
    AggregateFoodEntriesInput,
    ListFoodEntriesInput,
)
from tg_bot_meal_planning.application.meal_suggestions import MealSuggestionResult, SuggestDailyPlanInput
from tg_bot_meal_planning.application.user_profile import (
    GetUserProfile,
    RegisterUserProfile,
    RegisterUserProfileInput,
    UpdateUserProfile,
    UpdateUserProfileInput,
)
from tg_bot_meal_planning.domain.food_entry import FoodEntry, MacroNutrients
from tg_bot_meal_planning.domain.product import Barcode, Product, ProductSource
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, UserProfile
from tg_bot_meal_planning.interface.telegram.handlers import _format_macro_targets, _format_profile

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import Message

    from tg_bot_meal_planning.application.product_lookup import BarcodeLookupResult
    from tg_bot_meal_planning.application.use_case import UseCase
    from tg_bot_meal_planning.domain.barcode_scan import ScannedBarcode
    from tg_bot_meal_planning.domain.food_entry import FoodEntry


@dataclass(frozen=True)
class BotDependencies:
    """Набор use-case для Telegram-бота."""

    register_profile: RegisterUserProfile
    update_profile: UpdateUserProfile
    get_profile: GetUserProfile
    calculate_calories: UseCase[CalculateCaloriesInput, CalorieCalculationResult]
    suggest_daily_plan: UseCase[SuggestDailyPlanInput, MealSuggestionResult]
    aggregate_food_diary: UseCase[AggregateFoodEntriesInput, MacroNutrients]
    add_food_entry: UseCase[AddFoodEntryInput, FoodEntry]
    list_food_entries: UseCase[ListFoodEntriesInput, list[FoodEntry]]
    lookup_product: UseCase[Barcode, BarcodeLookupResult]
    save_manual_product: UseCase[Product, Product]
    decode_barcode_image: UseCase[bytes, Barcode]
    save_barcode_photo: UseCase[SaveBarcodePhotoInput, str]
    save_scanned_barcode: UseCase[SaveScannedBarcodeInput, ScannedBarcode]


def build_router(deps: BotDependencies) -> Router:
    """Создать и настроить aiogram Router."""

    router = Router()

    router.message.register(_wrap(deps, handle_start), Command("start"))
    router.message.register(_wrap(deps, handle_profile), Command("profile"))
    router.message.register(_wrap(deps, handle_set_profile), Command("set_profile"))
    router.message.register(_wrap(deps, handle_weight), Command("weight"))
    router.message.register(_wrap(deps, handle_add_food_entry), Command("add_food_entry"))
    router.message.register(_wrap(deps, handle_list_food_entries), Command("list_food_entries"))
    router.message.register(_wrap(deps, handle_barcode), Command("barcode"))
    router.message.register(_wrap(deps, handle_barcode_photo), F.photo)
    router.message.register(
        _wrap(deps, handle_barcode_photo),
        F.document.mime_type.in_(("image/jpeg", "image/png")),
    )
    router.message.register(_wrap(deps, handle_add_product), Command("add_product"))
    router.message.register(_wrap(deps, handle_calories), Command("calories"))
    router.message.register(_wrap(deps, handle_suggest_plan), Command("suggest_plan"))
    router.message.register(_wrap(deps, handle_summary_day), Command("summary_day"))
    router.message.register(_wrap(deps, handle_summary_week), Command("summary_week"))
    router.message.register(_wrap(deps, handle_summary_month), Command("summary_month"))
    # Поддержка кнопок без слеша
    return router


def _wrap(
    deps: BotDependencies,
    handler: Callable[[Message, BotDependencies], Awaitable[None]],
) -> Callable[[Message], Awaitable[None]]:
    async def _inner(message: Message) -> None:  # pragma: no cover - обёртка
        await handler(message, deps)

    return _inner


async def handle_start(message: Message, deps: BotDependencies) -> None:
    """Короткое приветствие без списка команд."""

    text = (
        "Привет! Я бот для планирования питания: помогу вести профиль, считать калории, "
        "агрегировать БЖУ и находить продукты по штрихкоду. "
        "Используйте меню команд в Telegram, чтобы выбрать действие."
    )
    await message.answer(text, reply_markup=ReplyKeyboardRemove())


async def handle_profile(message: Message, deps: BotDependencies) -> None:
    """Показать текущий профиль пользователя."""

    user_id = _user_id(message)
    profile = await _load_profile_or_prompt(message, deps, user_id)
    if profile is None:
        return

    await message.answer(_format_profile(profile))


async def handle_set_profile(message: Message, deps: BotDependencies) -> None:
    """Создать или обновить профиль из аргументов команды."""

    tokens = (message.text or "").split()
    if len(tokens) < 5:
        await message.answer(
            "Использование: /set_profile <рост> <вес> <пол> <цель>\n"
            "Пол: мужской или женский\n"
            f"Цель: {_goal_options_hint()}"
        )
        return

    _, height_raw, weight_raw, gender_raw, goal_raw = tokens[:5]
    try:
        height = float(height_raw)
        weight = float(weight_raw)
        gender = _parse_gender(gender_raw)
        goal = _parse_goal(goal_raw)
    except ValueError as exc:
        await message.answer(f"Ошибка ввода: {exc}")
        return

    user_id = _user_id(message)

    try:
        existing = deps.get_profile.execute(user_id)
    except UseCaseError:
        existing = None

    if existing is None:
        deps.register_profile.execute(
            RegisterUserProfileInput(
                user_id=user_id,
                height_cm=height,
                weight_kg=weight,
                gender=gender,
                goal=goal,
                macro_targets=None,
            )
        )
        await message.answer("Профиль создан.")
    else:
        updated = deps.update_profile.execute(
            UpdateUserProfileInput(
                user_id=user_id,
                height_cm=height,
                weight_kg=weight,
                gender=gender,
                goal=goal,
                macro_targets=existing.macro_targets,
            )
        )
        await message.answer(f"Профиль обновлён.\n{_format_profile(updated)}")


async def handle_add_food_entry(message: Message, deps: BotDependencies) -> None:
    """Добавить запись в дневник питания."""

    tokens = (message.text or "").split()
    if len(tokens) < 6:
        await message.answer(
            "Использование: /add_food_entry <порция г> <белки> <жиры> <углеводы> <название>"
        )
        return

    _, portion_raw, protein_raw, fat_raw, carbs_raw, *title_parts = tokens
    title = " ".join(title_parts).strip()
    if not title:
        await message.answer("Название обязательно.")
        return

    try:
        portion = float(portion_raw)
        macros = MacroNutrients(
            protein_g=float(protein_raw),
            fat_g=float(fat_raw),
            carbs_g=float(carbs_raw),
        )
    except ValueError as exc:
        await message.answer(f"Ошибка ввода: {exc}")
        return

    user_id = _user_id(message)
    now = datetime.now(UTC)
    try:
        entry = deps.add_food_entry.execute(
            AddFoodEntryInput(
                user_id=user_id,
                title=title,
                portion_grams=portion,
                protein_per_100g=macros.protein_g,
                fat_per_100g=macros.fat_g,
                carbs_per_100g=macros.carbs_g,
                taken_at=now,
            )
        )
    except UseCaseError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    actual = entry.actual_macros
    text_lines = [
        "Запись добавлена:",
        f"- {entry.title} ({entry.portion_grams:.0f} г)",
        f"- БЖУ: {_format_macro_targets(actual)}",
        f"- Ккал: {actual.calories_kcal:.0f}",
        f"- Время (UTC): {entry.taken_at_utc.strftime('%Y-%m-%d %H:%M')}",
    ]
    await message.answer("\n".join(text_lines))


async def handle_list_food_entries(message: Message, deps: BotDependencies) -> None:
    """Показать записи за период."""

    tokens = (message.text or "").split()
    period = tokens[1] if len(tokens) > 1 else "day"

    user_id = _user_id(message)
    now = datetime.now(UTC)
    start = _period_start(now, period)
    try:
        entries = deps.list_food_entries.execute(
            ListFoodEntriesInput(user_id=user_id, start_utc=start, end_utc=now)
        )
    except UseCaseError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    if not entries:
        await message.answer("Записей за период нет.")
        return

    total = MacroNutrients.zero()
    lines = ["Записи питания:"]
    for entry in entries:
        actual = entry.actual_macros
        total = total.add(actual)
        lines.append(
            f"- {entry.taken_at_utc.strftime('%Y-%m-%d %H:%M')} {entry.title}: "
            f"{entry.portion_grams:.0f} г, БЖУ {_format_macro_targets(actual)} "
            f"({actual.calories_kcal:.0f} ккал)"
        )
    lines.append(
        f"Итого: БЖУ {_format_macro_targets(total)}, Ккал {total.calories_kcal:.0f}"
    )
    await message.answer("\n".join(lines))


async def handle_weight(message: Message, deps: BotDependencies) -> None:
    """Обновить вес (и при необходимости цель)."""

    tokens = (message.text or "").split()
    if len(tokens) < 2:
        await message.answer(
            "Использование: /weight <вес> [цель: похудение/поддержание/набор]"
        )
        return

    _, weight_raw, *rest = tokens
    try:
        weight = float(weight_raw)
    except ValueError:
        await message.answer("Вес должен быть числом.")
        return

    goal = None
    if rest:
        try:
            goal = _parse_goal(rest[0])
        except ValueError as exc:
            await message.answer(f"Ошибка ввода цели: {exc}")
            return

    user_id = _user_id(message)
    profile = await _load_profile_or_prompt(message, deps, user_id)
    if profile is None:
        return
    try:
        updated = deps.update_profile.execute(
            UpdateUserProfileInput(user_id=user_id, weight_kg=weight, goal=goal)
        )
    except UseCaseError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    text_lines = [
        f"Вес обновлён: {updated.weight_kg:.1f} кг",
        f"Текущая цель: {_goal_label(updated.goal)}",
        f"БЖУ: {_format_macro_targets(updated.macro_targets)}",
    ]
    await message.answer("\n".join(text_lines))


async def handle_barcode(message: Message, deps: BotDependencies) -> None:
    """Найти товар по штрихкоду."""

    tokens = (message.text or "").split()
    if len(tokens) < 2:
        await message.answer(
            "Использование: /barcode <код товара>\n"
            "Или просто отправьте фото штрихкода — я распознаю и сохраню в своей системе."
        )
        return

    try:
        barcode = Barcode(tokens[1])
    except ValueError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    user_id = _user_id(message)
    profile = await _load_profile_or_prompt(message, deps, user_id)
    if profile is None:
        return

    try:
        result = deps.lookup_product.execute(barcode)
    except UseCaseError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    if result.needs_manual_input:
        reason = result.reason or "неизвестна"
        await message.answer(f"Товар не найден: {reason}")
        return

    product = result.product
    if product is None:
        await message.answer("Товар не найден.")
        return

    text_lines = [
        f"Товар: {product.name}",
        f"Штрихкод: {product.barcode}",
        f"БЖУ (на 100 г): {_format_macro_targets(product.macros_per_100g)}",
        f"Порция: {product.portion_grams:.0f} г",
    ]
    await message.answer("\n".join(text_lines))


async def handle_barcode_photo(message: Message, deps: BotDependencies) -> None:
    """Принять фото штрихкода, распознать и сохранить."""

    selected = _select_media(message)
    if selected is None:
        await message.answer("Пришлите фото штрихкода или используйте /barcode <код>.")
        return
    media, content_type, file_name = selected

    content = await _download_media_content(message, media)
    if content is None:
        return

    try:
        barcode = deps.decode_barcode_image.execute(content)
    except UseCaseError as exc:
        await message.answer(f"Не удалось распознать штрихкод: {exc}")
        return

    user_id = _user_id(message)
    profile = await _load_profile_or_prompt(message, deps, user_id)
    if profile is None:
        return

    try:
        photo_path = deps.save_barcode_photo.execute(
            SaveBarcodePhotoInput(
                user_id=user_id,
                barcode=barcode,
                content=content,
                content_type=content_type,
                file_name=file_name,
            )
        )
    except UseCaseError as exc:
        await message.answer(f"Не удалось сохранить фото: {exc}")
        return

    try:
        deps.save_scanned_barcode.execute(
            SaveScannedBarcodeInput(user_id=user_id, barcode=barcode, photo_path=photo_path)
        )
    except UseCaseError as exc:
        await message.answer(f"Ошибка сохранения данных сканирования: {exc}")
        return

    try:
        result = deps.lookup_product.execute(barcode)
    except UseCaseError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    if result.needs_manual_input:
        reason = result.reason or "неизвестна"
        await message.answer(
            f"Товар не найден: {reason}\n"
            f"Штрихкод: {barcode}\n"
            f"Фото сохранено: {photo_path}"
        )
        return

    product = result.product
    if product is None:
        await message.answer("Товар не найден.")
        return

    text_lines = [
        f"Товар: {product.name}",
        f"Штрихкод: {product.barcode}",
        f"БЖУ (на 100 г): {_format_macro_targets(product.macros_per_100g)}",
        f"Порция: {product.portion_grams:.0f} г",
        f"Фото сохранено: {photo_path}",
    ]
    await message.answer("\n".join(text_lines))


def _select_media(message: Message) -> tuple[Any, str, str | None] | None:
    photos = getattr(message, "photo", None)
    if photos:
        return photos[-1], "image/jpeg", None
    document = getattr(message, "document", None)
    if document and (document.mime_type or "").startswith("image/"):
        return document, document.mime_type, document.file_name
    return None


async def _download_media_content(message: Message, media: Any) -> bytes | None:
    try:
        bot = message.bot
        if bot is None:
            await message.answer("Бот недоступен для скачивания файла.")
            return None
        file = await bot.get_file(media.file_id)
        buffer = BytesIO()
        file_path = file.file_path or media.file_id
        await bot.download_file(file_path, buffer)
        return buffer.getvalue()
    except Exception as exc:  # noqa: BLE001 - защищаем от сетевых сбоев
        await message.answer(f"Не удалось скачать фото: {exc}")
        return None


async def handle_add_product(message: Message, deps: BotDependencies) -> None:
    """Сохранить вручную заданный продукт."""

    tokens = (message.text or "").split()
    if len(tokens) < 7:
        await message.answer(
            "Использование: /add_product <штрихкод> <порция_г> <белки_г> <жиры_г> <углеводы_г> <название>"
        )
        return

    _, barcode_raw, portion_raw, protein_raw, fat_raw, carbs_raw, *name_parts = tokens
    if not name_parts:
        await message.answer("Название продукта обязательно.")
        return

    try:
        barcode = Barcode(barcode_raw)
        macros = MacroNutrients(
            protein_g=float(protein_raw),
            fat_g=float(fat_raw),
            carbs_g=float(carbs_raw),
        )
        portion = float(portion_raw)
    except ValueError as exc:
        await message.answer(f"Ошибка ввода: {exc}")
        return

    product = Product(
        id=str(barcode),
        barcode=barcode,
        name=" ".join(name_parts),
        macros_per_100g=macros,
        portion_grams=portion,
        source=ProductSource.MANUAL,
    )

    try:
        saved = deps.save_manual_product.execute(product)
    except UseCaseError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    await message.answer(f"Сохранил продукт {saved.name}")


async def handle_calories(message: Message, deps: BotDependencies) -> None:
    """Рассчитать дневную норму калорий по профилю."""

    tokens = (message.text or "").split()
    if len(tokens) < 2:
        await message.answer("Использование: /calories <возраст>")
        return

    try:
        age = int(tokens[1])
    except ValueError:
        await message.answer("Возраст должен быть целым числом.")
        return

    user_id = _user_id(message)
    profile = await _load_profile_or_prompt(message, deps, user_id)
    if profile is None:
        return

    try:
        result = deps.calculate_calories.execute(
            CalculateCaloriesInput(user_id=user_id, age_years=age)
        )
    except UseCaseError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    text_lines = [
        "Расчёт калорий:",
        f"- BMR: {result.basal_metabolic_rate:.0f} ккал",
        f"- Поддержание: {result.maintenance_calories} ккал",
        f"- Цель ({_goal_label(result.goal)}): {result.goal_calories} ккал",
    ]
    await message.answer("\n".join(text_lines))


async def handle_suggest_plan(message: Message, deps: BotDependencies) -> None:
    """Сформировать план БЖУ по приёмам пищи."""

    tokens = (message.text or "").split()
    if len(tokens) < 2:
        await message.answer("Использование: /suggest_plan <возраст> [ккал]")
        return

    try:
        age = int(tokens[1])
    except ValueError:
        await message.answer("Возраст должен быть целым числом.")
        return

    calories_override = None
    if len(tokens) >= 3:
        try:
            calories_override = int(tokens[2])
        except ValueError:
            await message.answer("Калории должны быть числом, если переданы.")
            return

    user_id = _user_id(message)
    profile = await _load_profile_or_prompt(message, deps, user_id)
    if profile is None:
        return

    try:
        result = deps.suggest_daily_plan.execute(
            SuggestDailyPlanInput(profile=profile, calories=calories_override, age_years=age)
        )
    except UseCaseError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    meals_text = "\n".join(
        f"- {meal.name}: {_format_macro_targets(meal.macros)} ({meal.calories_kcal:.0f} ккал)"
        for meal in result.meals
    )
    text_lines = [
        "Рекомендации на день:",
        f"- Цель: {result.target_calories} ккал",
        f"- БЖУ: {_format_macro_targets(result.target_macros)}",
        "По приёмам пищи:",
        meals_text,
    ]
    await message.answer("\n".join(text_lines))


async def handle_summary_day(message: Message, deps: BotDependencies) -> None:
    await _handle_summary(message, deps, period="day")


async def handle_summary_week(message: Message, deps: BotDependencies) -> None:
    await _handle_summary(message, deps, period="week")


async def handle_summary_month(message: Message, deps: BotDependencies) -> None:
    await _handle_summary(message, deps, period="month")


def _parse_gender(raw: str) -> Gender:
    normalized = raw.strip().lower()
    mapping = {
        "мужской": Gender.MALE,
        "мужчина": Gender.MALE,
        "муж": Gender.MALE,
        "м": Gender.MALE,
        "женский": Gender.FEMALE,
        "женщина": Gender.FEMALE,
        "жен": Gender.FEMALE,
        "ж": Gender.FEMALE,
    }
    if normalized in mapping:
        return mapping[normalized]
    msg = "пол должен быть мужской или женский"
    raise ValueError(msg)


def _parse_goal(raw: str) -> Goal:
    normalized = raw.strip().lower()
    mapping = {
        "похудение": Goal.LOSE_WEIGHT,
        "похудеть": Goal.LOSE_WEIGHT,
        "снижение": Goal.LOSE_WEIGHT,
        "минус": Goal.LOSE_WEIGHT,
        "сброс": Goal.LOSE_WEIGHT,
        "поддержание": Goal.MAINTAIN_WEIGHT,
        "поддерживать": Goal.MAINTAIN_WEIGHT,
        "держать": Goal.MAINTAIN_WEIGHT,
        "стабильно": Goal.MAINTAIN_WEIGHT,
        "набор": Goal.GAIN_WEIGHT,
        "набрать": Goal.GAIN_WEIGHT,
        "рост": Goal.GAIN_WEIGHT,
        "плюс": Goal.GAIN_WEIGHT,
    }
    if normalized in mapping:
        return mapping[normalized]
    raise ValueError(f"цель должна быть одной из: {_goal_options_hint()}")


def _user_id(message: Message) -> str:
    return str(message.from_user.id if message.from_user else message.chat.id)


def _goal_label(goal: Goal) -> str:
    return {
        Goal.LOSE_WEIGHT: "похудение",
        Goal.MAINTAIN_WEIGHT: "поддержание",
        Goal.GAIN_WEIGHT: "набор",
    }[goal]


def _goal_options_hint() -> str:
    return "похудение, поддержание, набор"


async def _load_profile_or_prompt(
    message: Message, deps: BotDependencies, user_id: str
) -> UserProfile | None:
    try:
        return deps.get_profile.execute(user_id)
    except UseCaseError:
        await message.answer(
            "Профиль не найден. Заполните: /set_profile <рост> <вес> <пол> <цель>"
        )
        return None


async def _handle_summary(message: Message, deps: BotDependencies, *, period: str) -> None:
    user_id = _user_id(message)
    profile = await _load_profile_or_prompt(message, deps, user_id)
    if profile is None:
        return

    now = datetime.now(UTC)
    start = _period_start(now, period)
    try:
        aggregate = deps.aggregate_food_diary.execute(
            AggregateFoodEntriesInput(user_id=user_id, start=start, end=now)
        )
    except UseCaseError as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    labels = {"day": "день", "week": "неделю", "month": "месяц"}
    label = labels.get(period, period)
    text_lines = [
        f"Агрегация за {label}:",
        f"- БЖУ: {_format_macro_targets(aggregate)}",
        f"- Ккал: {aggregate.calories_kcal:.0f}",
    ]
    await message.answer("\n".join(text_lines))


def _period_start(now: datetime, period: str) -> datetime:
    if period == "week":
        return (now - timedelta(days=7)).replace(tzinfo=UTC)
    if period == "month":
        return (now - timedelta(days=30)).replace(tzinfo=UTC)
    return (now - timedelta(days=1)).replace(tzinfo=UTC)

