from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path


class LocalPhotoStorage:
    """Сохраняет фото локально и возвращает относительный путь."""

    def __init__(self, base_dir: str | Path = "var/photos") -> None:
        self._base_dir = Path(base_dir)

    def save(
        self,
        *,
        user_id: str,
        barcode: str,
        content: bytes,
        content_type: str | None = None,
        file_name: str | None = None,
    ) -> str:
        if not content:
            msg = "Фото пустое"
            raise ValueError(msg)

        safe_user = self._sanitize(user_id)
        safe_barcode = self._sanitize(barcode) or "unknown"
        extension = self._resolve_extension(content_type, file_name)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        relative_path = self._base_dir / safe_user / f"{safe_barcode}_{timestamp}{extension}"

        full_path = relative_path if relative_path.is_absolute() else Path.cwd() / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

        # Возвращаем относительный путь (как в конфигурации), чтобы можно было хранить в БД.
        return relative_path.as_posix()

    @staticmethod
    def _sanitize(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", value.strip())

    @staticmethod
    def _resolve_extension(content_type: str | None, file_name: str | None) -> str:
        if file_name and "." in file_name:
            return f".{file_name.rsplit('.', 1)[-1]}"
        if content_type == "image/png":
            return ".png"
        if content_type == "image/jpeg":
            return ".jpg"
        return ".jpg"


