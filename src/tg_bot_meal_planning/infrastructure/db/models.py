from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from tg_bot_meal_planning.infrastructure.db.base import Base


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    gender: Mapped[str] = mapped_column(String, nullable=False)
    goal: Mapped[str] = mapped_column(String, nullable=False)
    macro_protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    macro_fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    macro_carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)


class FoodEntryModel(Base):
    __tablename__ = "food_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    portion_grams: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    taken_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScannedBarcodeModel(Base):
    __tablename__ = "scanned_barcodes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    barcode: Mapped[str] = mapped_column(String, nullable=False, index=True)
    photo_path: Mapped[str] = mapped_column(String, nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


