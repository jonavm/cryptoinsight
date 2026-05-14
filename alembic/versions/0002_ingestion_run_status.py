"""add ingestion run status

Revision ID: 0002_ingestion_run_status
Revises: 0001_crypto_prices
Create Date: 2026-05-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_ingestion_run_status"
down_revision = "0001_crypto_prices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_run_status",
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("last_duration_seconds", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("rows_fetched", sa.Integer(), nullable=True),
        sa.Column("rows_inserted", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("source"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_run_status")
