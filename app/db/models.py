from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CryptoPriceSnapshot(Base):
    """
    Immutable market snapshots provide a simple historical foundation.
    At larger scale, this table would likely be partitioned by date and asset.
    """

    __tablename__ = "crypto_price_snapshots"
    __table_args__ = (
        UniqueConstraint("asset_id", "snapshot_at", name="uq_crypto_price_snapshots_asset_time"),
        Index("ix_crypto_price_snapshots_asset_snapshot", "asset_id", "snapshot_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    current_price_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    market_cap_usd: Mapped[Decimal | None] = mapped_column(Numeric(24, 2), nullable=True)
    total_volume_usd: Mapped[Decimal | None] = mapped_column(Numeric(24, 2), nullable=True)
    price_change_percentage_24h: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="coingecko")
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IngestionRunStatus(Base):
    """
    One row per source keeps operational status easy to query from the API and dashboard.
    At larger scale this would likely be complemented by an append-only run log table.
    """

    __tablename__ = "ingestion_run_status"

    source: Mapped[str] = mapped_column(String(50), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    rows_fetched: Mapped[int | None] = mapped_column(nullable=True)
    rows_inserted: Mapped[int | None] = mapped_column(nullable=True)


class WatchlistAsset(Base):
    """
    Simple persistent watchlist for the local MVP.
    Without authentication, a single shared list keeps the workflow clear.
    """

    __tablename__ = "watchlist_assets"

    asset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AlertRuleOverride(Base):
    """
    Per-asset alert overrides keep local product settings editable from the UI.
    Global defaults still live in environment configuration.
    """

    __tablename__ = "alert_rule_overrides"

    asset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    price_move_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    price_move_high_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    volatility_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    volume_spike_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    volume_spike_high_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
