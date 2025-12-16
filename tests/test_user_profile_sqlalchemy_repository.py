from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tg_bot_meal_planning.domain.user_profile import Gender, Goal, MacroTargets, UserProfile
from tg_bot_meal_planning.infrastructure.db.base import Base
from tg_bot_meal_planning.infrastructure.repositories.sqlalchemy_user_profile import SqlAlchemyUserProfileRepository

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _make_repo(tmp_path: Path) -> tuple[SqlAlchemyUserProfileRepository, Callable[[], Session]]:
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    return SqlAlchemyUserProfileRepository(factory), factory


def test_get_returns_none_when_absent(tmp_path: Path) -> None:
    repo, _ = _make_repo(tmp_path)

    assert repo.get("missing") is None


def test_save_and_get_roundtrip(tmp_path: Path) -> None:
    repo, _ = _make_repo(tmp_path)
    profile = UserProfile(
        id="u1",
        height_cm=175,
        weight_kg=70,
        gender=Gender.MALE,
        goal=Goal.MAINTAIN_WEIGHT,
        macro_targets=MacroTargets(protein_g=120, fat_g=60, carbs_g=210),
    )

    repo.save(profile)
    loaded = repo.get("u1")

    assert loaded == profile


def test_save_updates_existing(tmp_path: Path) -> None:
    repo, _ = _make_repo(tmp_path)
    initial = UserProfile(
        id="u1",
        height_cm=175,
        weight_kg=70,
        gender=Gender.MALE,
        goal=Goal.MAINTAIN_WEIGHT,
    )
    repo.save(initial)

    updated = initial.update(weight_kg=68, goal=Goal.LOSE_WEIGHT, macro_targets=MacroTargets(130, 50, 180))
    repo.save(updated)

    loaded = repo.get("u1")

    assert loaded == updated



