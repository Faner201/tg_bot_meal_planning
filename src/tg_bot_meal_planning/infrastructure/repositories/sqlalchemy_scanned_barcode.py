from __future__ import annotations

from typing import TYPE_CHECKING

from tg_bot_meal_planning.application.repositories import ScannedBarcodeRepository
from tg_bot_meal_planning.infrastructure.db.models import ScannedBarcodeModel

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

    from tg_bot_meal_planning.domain.barcode_scan import ScannedBarcode


class SqlAlchemyScannedBarcodeRepository(ScannedBarcodeRepository):
    """Сохранение фактов сканирования штрихкодов в БД."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def save(self, scan: ScannedBarcode) -> None:
        with self._session_factory() as session:
            session.merge(self._to_model(scan))
            session.commit()

    @staticmethod
    def _to_model(scan: ScannedBarcode) -> ScannedBarcodeModel:
        return ScannedBarcodeModel(
            id=scan.id,
            user_id=scan.user_id,
            barcode=str(scan.barcode),
            photo_path=scan.photo_path,
            scanned_at=scan.scanned_at,
        )


