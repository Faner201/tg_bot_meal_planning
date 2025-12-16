"""create user_profiles table"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251216_create_user_profiles"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("gender", sa.String(), nullable=False),
        sa.Column("goal", sa.String(), nullable=False),
        sa.Column("macro_protein_g", sa.Float(), nullable=True),
        sa.Column("macro_fat_g", sa.Float(), nullable=True),
        sa.Column("macro_carbs_g", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("user_profiles")



