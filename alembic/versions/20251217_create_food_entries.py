"""create food_entries table"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251217_create_food_entries"
down_revision: str | None = "20251216_create_user_profiles"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "food_entries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("portion_grams", sa.Float(), nullable=False),
        sa.Column("protein_per_100g", sa.Float(), nullable=False),
        sa.Column("fat_per_100g", sa.Float(), nullable=False),
        sa.Column("carbs_per_100g", sa.Float(), nullable=False),
        sa.Column("taken_at_utc", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    op.create_index(
        "ix_food_entries_user_period",
        "food_entries",
        ["user_id", "taken_at_utc"],
    )


def downgrade() -> None:
    op.drop_index("ix_food_entries_user_period", table_name="food_entries")
    op.drop_table("food_entries")



