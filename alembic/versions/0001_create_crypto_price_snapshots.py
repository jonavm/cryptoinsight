"""create crypto price snapshots

Revision ID: 0001_crypto_prices
Revises:
Create Date: 2026-05-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_crypto_prices"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crypto_price_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("current_price_usd", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("market_cap_usd", sa.Numeric(precision=24, scale=2), nullable=True),
        sa.Column("total_volume_usd", sa.Numeric(precision=24, scale=2), nullable=True),
        sa.Column("price_change_percentage_24h", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "snapshot_at", name="uq_crypto_price_snapshots_asset_time"),
    )
    op.create_index(
        "ix_crypto_price_snapshots_asset_snapshot",
        "crypto_price_snapshots",
        ["asset_id", "snapshot_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_crypto_price_snapshots_asset_snapshot", table_name="crypto_price_snapshots")
    op.drop_table("crypto_price_snapshots")
