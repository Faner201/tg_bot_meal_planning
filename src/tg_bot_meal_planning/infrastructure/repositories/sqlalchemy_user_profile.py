from __future__ import annotations

from typing import TYPE_CHECKING

from tg_bot_meal_planning.application.repositories import UserProfileRepository
from tg_bot_meal_planning.domain.user_profile import Gender, Goal, MacroTargets, UserProfile
from tg_bot_meal_planning.infrastructure.db.models import UserProfileModel

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session


class SqlAlchemyUserProfileRepository(UserProfileRepository):
    """Репозиторий профилей на SQLAlchemy/SQLite."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def get(self, user_id: str) -> UserProfile | None:
        with self._session_factory() as session:
            model = session.get(UserProfileModel, user_id)
            if model is None:
                return None
            return self._to_domain(model)

    def save(self, profile: UserProfile) -> None:
        with self._session_factory() as session:
            existing = session.get(UserProfileModel, profile.id)
            if existing is None:
                session.add(self._to_model(profile))
            else:
                existing.height_cm = profile.height_cm
                existing.weight_kg = profile.weight_kg
                existing.gender = profile.gender.value
                existing.goal = profile.goal.value
                existing.macro_protein_g = profile.macro_targets.protein_g if profile.macro_targets else None
                existing.macro_fat_g = profile.macro_targets.fat_g if profile.macro_targets else None
                existing.macro_carbs_g = profile.macro_targets.carbs_g if profile.macro_targets else None
            session.commit()

    @staticmethod
    def _to_model(profile: UserProfile) -> UserProfileModel:
        return UserProfileModel(
            id=profile.id,
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            gender=profile.gender.value,
            goal=profile.goal.value,
            macro_protein_g=profile.macro_targets.protein_g if profile.macro_targets else None,
            macro_fat_g=profile.macro_targets.fat_g if profile.macro_targets else None,
            macro_carbs_g=profile.macro_targets.carbs_g if profile.macro_targets else None,
        )

    @staticmethod
    def _to_domain(model: UserProfileModel) -> UserProfile:
        has_macros = (
            model.macro_protein_g is not None or model.macro_fat_g is not None or model.macro_carbs_g is not None
        )
        macro_targets = (
            MacroTargets(
                protein_g=model.macro_protein_g or 0.0,
                fat_g=model.macro_fat_g or 0.0,
                carbs_g=model.macro_carbs_g or 0.0,
            )
            if has_macros
            else None
        )
        return UserProfile(
            id=model.id,
            height_cm=model.height_cm,
            weight_kg=model.weight_kg,
            gender=Gender(model.gender),
            goal=Goal(model.goal),
            macro_targets=macro_targets,
        )






