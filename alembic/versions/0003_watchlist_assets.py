"""add watchlist assets

Revision ID: 0003_watchlist_assets
Revises: 0002_ingestion_run_status
Create Date: 2026-05-14 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_watchlist_assets"
down_revision = "0002_ingestion_run_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_assets",
        sa.Column("asset_id", sa.String(length=100), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("asset_id"),
    )


def downgrade() -> None:
    op.drop_table("watchlist_assets")
