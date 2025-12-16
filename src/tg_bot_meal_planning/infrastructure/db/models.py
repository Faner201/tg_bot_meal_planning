from __future__ import annotations

from sqlalchemy import Float, String
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



