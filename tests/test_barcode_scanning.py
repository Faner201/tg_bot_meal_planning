from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import pytest
from PIL import Image

from tg_bot_meal_planning.application.barcode_scanning import (
    DecodeBarcodeImage,
    SaveBarcodePhoto,
    SaveBarcodePhotoInput,
    SaveScannedBarcode,
    SaveScannedBarcodeInput,
)
from tg_bot_meal_planning.application.errors import UseCaseError
from tg_bot_meal_planning.domain.product import Barcode
from tg_bot_meal_planning.infrastructure.storage.local_photo_storage import LocalPhotoStorage

if TYPE_CHECKING:
    from pathlib import Path


def _png_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (4, 4), color="white").save(buf, format="PNG")
    return buf.getvalue()


def test_decode_barcode_image_returns_barcode(monkeypatch: pytest.MonkeyPatch) -> None:
    image_bytes = _png_bytes()

    class _Decoded:
        def __init__(self) -> None:
            self.data = b"4601234567890"
            self.type = "EAN13"

    monkeypatch.setattr("tg_bot_meal_planning.application.barcode_scanning.decode_barcode", lambda image: [_Decoded()])

    decoder = DecodeBarcodeImage()
    result = decoder.execute(image_bytes)

    assert result == Barcode("4601234567890")


def test_decode_barcode_image_raises_if_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    image_bytes = _png_bytes()
    monkeypatch.setattr("tg_bot_meal_planning.application.barcode_scanning.decode_barcode", lambda image: [])

    decoder = DecodeBarcodeImage()

    with pytest.raises(UseCaseError):
        decoder.execute(image_bytes)


def test_save_barcode_photo_persists_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    storage = LocalPhotoStorage("photos")
    saver = SaveBarcodePhoto(storage)

    relative_path = saver.execute(
        SaveBarcodePhotoInput(
            user_id="user-1",
            barcode=Barcode("4601234567890"),
            content=b"binary-content",
            content_type="image/jpeg",
            file_name=None,
        )
    )

    assert relative_path.startswith("photos/")
    assert (tmp_path / relative_path).exists()


def test_save_scanned_barcode_stores_entity() -> None:
    repo_calls: list[object] = []

    class _Repo:
        def save(self, scan: object) -> None:
            repo_calls.append(scan)

    saver = SaveScannedBarcode(_Repo())
    result = saver.execute(
        SaveScannedBarcodeInput(
            user_id="user-1",
            barcode=Barcode("4601234567890"),
            photo_path="photos/user-1/pic.jpg",
        )
    )

    assert repo_calls
    assert repo_calls[0] == result
    assert result.photo_path == "photos/user-1/pic.jpg"


