from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.schemas.market import (
    AlertRuleOverrideUpdateRequest,
    AssetAlertThresholdsResponse,
    AssetHistoryResponse,
    MarketAlertResponse,
    MarketSnapshotResponse,
    MarketSummaryResponse,
    WatchlistResponse,
    WatchlistUpdateRequest,
)
from app.services.market_service import MarketService

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/latest", response_model=list[MarketSnapshotResponse])
def get_latest_market_snapshots(
    limit: int = 20,
    db: Session = Depends(get_db_session),
) -> list[MarketSnapshotResponse]:
    service = MarketService(db)
    return service.get_latest_snapshots(limit=limit)


@router.get("/summary", response_model=MarketSummaryResponse)
def get_market_summary(db: Session = Depends(get_db_session)) -> MarketSummaryResponse:
    service = MarketService(db)
    return service.get_market_summary()


@router.get("/watchlist", response_model=WatchlistResponse)
def get_watchlist(db: Session = Depends(get_db_session)) -> WatchlistResponse:
    service = MarketService(db)
    return WatchlistResponse(asset_ids=service.get_watchlist_asset_ids())


@router.put("/watchlist", response_model=WatchlistResponse)
def update_watchlist(
    payload: WatchlistUpdateRequest,
    db: Session = Depends(get_db_session),
) -> WatchlistResponse:
    service = MarketService(db)
    return WatchlistResponse(asset_ids=service.replace_watchlist_asset_ids(payload.asset_ids))


@router.get("/alert-rules/{asset_id}", response_model=AssetAlertThresholdsResponse)
def get_asset_alert_rules(
    asset_id: str,
    db: Session = Depends(get_db_session),
) -> AssetAlertThresholdsResponse:
    service = MarketService(db)
    return service.get_asset_alert_thresholds(asset_id)


@router.put("/alert-rules/{asset_id}", response_model=AssetAlertThresholdsResponse)
def update_asset_alert_rules(
    asset_id: str,
    payload: AlertRuleOverrideUpdateRequest,
    db: Session = Depends(get_db_session),
) -> AssetAlertThresholdsResponse:
    service = MarketService(db)
    return service.update_asset_alert_thresholds(asset_id, payload.model_dump())


@router.get("/alerts", response_model=list[MarketAlertResponse])
def get_market_alerts(
    asset_id: str | None = None,
    db: Session = Depends(get_db_session),
) -> list[MarketAlertResponse]:
    service = MarketService(db)
    return service.get_market_alerts(asset_id=asset_id)


@router.get("/history/{asset_id}", response_model=AssetHistoryResponse)
def get_asset_history(
    asset_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    db: Session = Depends(get_db_session),
) -> AssetHistoryResponse:
    if start_at is not None and end_at is not None and start_at > end_at:
        raise HTTPException(status_code=400, detail="start_at must be earlier than or equal to end_at")

    service = MarketService(db)
    return service.get_asset_history(
        asset_id=asset_id,
        limit=limit,
        start_at=start_at,
        end_at=end_at,
    )
