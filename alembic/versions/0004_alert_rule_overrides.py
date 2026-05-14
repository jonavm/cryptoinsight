"""add alert rule overrides

Revision ID: 0004_alert_rule_overrides
Revises: 0003_watchlist_assets
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_alert_rule_overrides"
down_revision = "0003_watchlist_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_rule_overrides",
        sa.Column("asset_id", sa.String(length=100), nullable=False),
        sa.Column("price_move_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("price_move_high_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("volatility_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("volume_spike_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("volume_spike_high_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("asset_id"),
    )


def downgrade() -> None:
    op.drop_table("alert_rule_overrides")
