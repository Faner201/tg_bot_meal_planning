"""create scanned_barcodes table"""

from __future__ import annotations

# ruff: noqa: I001
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251218_create_scanned_barcodes"
down_revision: str | None = "20251217_create_food_entries"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "scanned_barcodes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("barcode", sa.String(), nullable=False, index=True),
        sa.Column("photo_path", sa.String(), nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    op.create_index(
        "ix_scanned_barcodes_user_at",
        "scanned_barcodes",
        ["user_id", "scanned_at"],
    )
    op.create_index(
        "ix_scanned_barcodes_barcode",
        "scanned_barcodes",
        ["barcode"],
    )


def downgrade() -> None:
    op.drop_index("ix_scanned_barcodes_barcode", table_name="scanned_barcodes")
    op.drop_index("ix_scanned_barcodes_user_at", table_name="scanned_barcodes")
    op.drop_table("scanned_barcodes")


