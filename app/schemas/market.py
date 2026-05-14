from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MarketSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    symbol: str
    name: str
    current_price_usd: Decimal
    market_cap_usd: Decimal | None
    total_volume_usd: Decimal | None
    price_change_percentage_24h: Decimal | None
    snapshot_at: datetime


class MarketSummaryResponse(BaseModel):
    tracked_assets: int
    latest_snapshot_at: datetime | None
    total_market_cap_usd: Decimal | None
    total_volume_usd: Decimal | None


class AssetHistoryAnalyticsResponse(BaseModel):
    latest_price_usd: float | None
    window_change_usd: float | None
    window_change_pct: float | None
    moving_average_5: float | None
    moving_average_10: float | None
    rolling_volatility_pct: float | None
    highest_price_usd: float | None
    lowest_price_usd: float | None


class AssetHistoryResponse(BaseModel):
    asset_id: str
    symbol: str | None
    name: str | None
    points: int
    analytics: AssetHistoryAnalyticsResponse | None
    snapshots: list[MarketSnapshotResponse]


class IngestionStatusResponse(BaseModel):
    source: str
    status: str
    last_attempt_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    last_duration_seconds: float | None
    rows_fetched: int | None
    rows_inserted: int | None


class HealthResponse(BaseModel):
    status: str
    database: str
    pipeline: IngestionStatusResponse | None


class MarketAlertResponse(BaseModel):
    severity: str
    category: str
    title: str
    message: str
    observed_value: float | None = None
    threshold_value: float | None = None
    high_threshold_value: float | None = None
    unit: str | None = None
    severity_reason: str | None = None
    asset_id: str | None = None
    detected_at: datetime


class WatchlistResponse(BaseModel):
    asset_ids: list[str]


class WatchlistUpdateRequest(BaseModel):
    asset_ids: list[str]


class AlertRuleOverrideResponse(BaseModel):
    asset_id: str
    price_move_pct: float | None
    price_move_high_pct: float | None
    volatility_pct: float | None
    volume_spike_ratio: float | None
    volume_spike_high_ratio: float | None


class AlertRuleOverrideUpdateRequest(BaseModel):
    price_move_pct: float | None = None
    price_move_high_pct: float | None = None
    volatility_pct: float | None = None
    volume_spike_ratio: float | None = None
    volume_spike_high_ratio: float | None = None


class AssetAlertThresholdsResponse(BaseModel):
    asset_id: str
    defaults: AlertRuleOverrideResponse
    overrides: AlertRuleOverrideResponse
    effective: AlertRuleOverrideResponse
