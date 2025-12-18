from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING, Any, Protocol
from uuid import uuid4

from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.application.use_case import SyncUseCase
from tg_bot_meal_planning.domain.barcode_scan import ScannedBarcode
from tg_bot_meal_planning.domain.product import Barcode

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from tg_bot_meal_planning.application.repositories import ScannedBarcodeRepository
    from tg_bot_meal_planning.infrastructure.storage.local_photo_storage import LocalPhotoStorage


@dataclass(frozen=True)
class SaveBarcodePhotoInput:
    user_id: str
    barcode: Barcode
    content: bytes
    content_type: str | None = None
    file_name: str | None = None


class SaveBarcodePhoto(SyncUseCase[SaveBarcodePhotoInput, str]):
    """Сохранить фото штрихкода и вернуть относительный путь."""

    def __init__(self, storage: LocalPhotoStorage) -> None:
        self._storage = storage

    def execute(self, data: SaveBarcodePhotoInput) -> str:
        try:
            return self._storage.save(
                user_id=data.user_id,
                barcode=data.barcode,
                content=data.content,
                content_type=data.content_type,
                file_name=data.file_name,
            )
        except Exception as exc:  # noqa: BLE001 - конвертируем любые ошибки в UseCaseError
            msg = f"Не удалось сохранить фото: {exc}"
            raise UseCaseError(msg) from exc


@dataclass(frozen=True)
class SaveScannedBarcodeInput:
    user_id: str
    barcode: Barcode
    photo_path: str
    scanned_at: datetime | None = None


class SaveScannedBarcode(SyncUseCase[SaveScannedBarcodeInput, ScannedBarcode]):
    """Сохранить факт сканирования штрихкода."""

    def __init__(self, repository: ScannedBarcodeRepository) -> None:
        self._repository = repository

    def execute(self, data: SaveScannedBarcodeInput) -> ScannedBarcode:
        scanned_at = data.scanned_at or datetime.now(UTC)
        scan = ScannedBarcode(
            id=str(uuid4()),
            user_id=data.user_id,
            barcode=data.barcode,
            photo_path=data.photo_path,
            scanned_at=scanned_at,
        )
        self._repository.save(scan)
        return scan


class DecodeBarcodeImage(SyncUseCase[bytes, Barcode]):
    """Распознать штрихкод из байтов изображения."""

    _DEFAULT_TYPES = {"EAN13", "EAN8", "UPCA", "UPCE"}

    def __init__(self, *, allowed_types: Iterable[str] | None = None) -> None:
        self._allowed_types = set(allowed_types) if allowed_types is not None else self._DEFAULT_TYPES

    def execute(self, data: bytes) -> Barcode:
        if not data:
            msg = "Пустое изображение"
            raise UseCaseError(msg)

        try:
            from PIL import Image
        except Exception as exc:  # noqa: BLE001 - конвертируем импортные ошибки
            msg = "Pillow не установлена или повреждена"
            raise UseCaseError(msg) from exc

        decoder = _load_decoder()

        try:
            image = Image.open(BytesIO(data))
        except Exception as exc:  # noqa: BLE001 - любые ошибки чтения изображения
            msg = "Не удалось прочитать изображение"
            raise UseCaseError(msg) from exc

        decoded: list[_DecodedItem] = decoder(image)
        if not decoded:
            raise UseCaseError("Штрихкод не найден на фото")

        for item in decoded:
            if self._allowed_types and item.type not in self._allowed_types:
                continue
            raw_value = item.data.decode("utf-8", errors="ignore")
            digits = re.sub(r"\\D", "", raw_value)
            if not digits:
                continue
            try:
                return Barcode(digits)
            except ValueError:
                continue

        raise UseCaseError("Не удалось распознать штрихкод")


def _load_decoder() -> Callable[[object], list[_DecodedItem]]:
    global decode_barcode  # type: ignore[global-variable-not-assigned]

    if decode_barcode is not None:  # type: ignore[truthy-bool]
        return decode_barcode  # type: ignore[misc]

    try:
        from pyzbar.pyzbar import decode as decode_barcode  # type: ignore
        globals()["decode_barcode"] = decode_barcode
    except Exception as exc:  # noqa: BLE001 - любые проблемы с libzbar
        msg = "pyzbar/libzbar недоступен, установите системную библиотеку zbar"
        raise UseCaseError(msg) from exc
    return decode_barcode  # type: ignore[misc]


# Глобальная ссылка, чтобы упростить мок в тестах и кешировать декодер.
decode_barcode: Callable[[Any], list[_DecodedItem]] | None = None


class _DecodedItem(Protocol):
    type: str
    data: bytes


