from datetime import UTC, datetime
from statistics import pstdev

from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AlertRuleOverride, CryptoPriceSnapshot, IngestionRunStatus, WatchlistAsset
from app.schemas.market import (
    AlertRuleOverrideResponse,
    AssetAlertThresholdsResponse,
    AssetHistoryAnalyticsResponse,
    AssetHistoryResponse,
    MarketAlertResponse,
    MarketSnapshotResponse,
    MarketSummaryResponse,
)


class MarketService:
    def __init__(self, db_session: Session) -> None:
        self._db_session = db_session
        self._settings = get_settings()

    def _latest_snapshot_subquery(self):
        return (
            select(
                CryptoPriceSnapshot.asset_id.label("asset_id"),
                func.max(CryptoPriceSnapshot.snapshot_at).label("latest_snapshot_at"),
            )
            .group_by(CryptoPriceSnapshot.asset_id)
            .subquery()
        )

    def _latest_snapshots_statement(self) -> Select[tuple[CryptoPriceSnapshot]]:
        latest = self._latest_snapshot_subquery()
        return (
            select(CryptoPriceSnapshot)
            .join(
                latest,
                (CryptoPriceSnapshot.asset_id == latest.c.asset_id)
                & (CryptoPriceSnapshot.snapshot_at == latest.c.latest_snapshot_at),
            )
            .order_by(CryptoPriceSnapshot.market_cap_usd.desc().nullslast())
        )

    def get_latest_snapshots(self, limit: int = 20) -> list[MarketSnapshotResponse]:
        rows = self._db_session.scalars(self._latest_snapshots_statement().limit(limit)).all()
        return [MarketSnapshotResponse.model_validate(row) for row in rows]

    def get_market_summary(self) -> MarketSummaryResponse:
        latest_rows = self._latest_snapshots_statement().subquery()
        summary = self._db_session.execute(
            select(
                func.count().label("tracked_assets"),
                func.max(latest_rows.c.snapshot_at).label("latest_snapshot_at"),
                func.sum(latest_rows.c.market_cap_usd).label("total_market_cap_usd"),
                func.sum(latest_rows.c.total_volume_usd).label("total_volume_usd"),
            )
        ).one()

        return MarketSummaryResponse(
            tracked_assets=summary.tracked_assets or 0,
            latest_snapshot_at=summary.latest_snapshot_at,
            total_market_cap_usd=summary.total_market_cap_usd,
            total_volume_usd=summary.total_volume_usd,
        )

    def get_watchlist_asset_ids(self) -> list[str]:
        rows = self._db_session.scalars(
            select(WatchlistAsset.asset_id).order_by(WatchlistAsset.added_at.asc(), WatchlistAsset.asset_id.asc())
        ).all()
        return list(rows)

    def replace_watchlist_asset_ids(self, asset_ids: list[str]) -> list[str]:
        normalized_asset_ids = list(dict.fromkeys(asset_ids))
        self._db_session.query(WatchlistAsset).delete()
        if normalized_asset_ids:
            self._db_session.add_all([WatchlistAsset(asset_id=asset_id) for asset_id in normalized_asset_ids])
        self._db_session.commit()
        return normalized_asset_ids

    def get_asset_alert_thresholds(self, asset_id: str) -> AssetAlertThresholdsResponse:
        defaults = self._settings.get_asset_alert_thresholds("__defaults__")
        env_asset_thresholds = self._settings.asset_alert_rules.get(asset_id, {})
        db_override = self._db_session.get(AlertRuleOverride, asset_id)

        default_response = AlertRuleOverrideResponse(
            asset_id=asset_id,
            price_move_pct=defaults["price_move_pct"],
            price_move_high_pct=defaults["price_move_high_pct"],
            volatility_pct=defaults["volatility_pct"],
            volume_spike_ratio=defaults["volume_spike_ratio"],
            volume_spike_high_ratio=defaults["volume_spike_high_ratio"],
        )
        override_response = AlertRuleOverrideResponse(
            asset_id=asset_id,
            price_move_pct=float(db_override.price_move_pct) if db_override and db_override.price_move_pct is not None else env_asset_thresholds.get("price_move_pct"),
            price_move_high_pct=float(db_override.price_move_high_pct) if db_override and db_override.price_move_high_pct is not None else env_asset_thresholds.get("price_move_high_pct"),
            volatility_pct=float(db_override.volatility_pct) if db_override and db_override.volatility_pct is not None else env_asset_thresholds.get("volatility_pct"),
            volume_spike_ratio=float(db_override.volume_spike_ratio) if db_override and db_override.volume_spike_ratio is not None else env_asset_thresholds.get("volume_spike_ratio"),
            volume_spike_high_ratio=float(db_override.volume_spike_high_ratio) if db_override and db_override.volume_spike_high_ratio is not None else env_asset_thresholds.get("volume_spike_high_ratio"),
        )
        effective_thresholds = self._get_alert_thresholds(asset_id=asset_id)
        effective_response = AlertRuleOverrideResponse(
            asset_id=asset_id,
            price_move_pct=effective_thresholds["price_move_pct"],
            price_move_high_pct=effective_thresholds["price_move_high_pct"],
            volatility_pct=effective_thresholds["volatility_pct"],
            volume_spike_ratio=effective_thresholds["volume_spike_ratio"],
            volume_spike_high_ratio=effective_thresholds["volume_spike_high_ratio"],
        )
        return AssetAlertThresholdsResponse(
            asset_id=asset_id,
            defaults=default_response,
            overrides=override_response,
            effective=effective_response,
        )

    def update_asset_alert_thresholds(self, asset_id: str, payload: dict[str, float | None]) -> AssetAlertThresholdsResponse:
        cleaned_payload = {
            "price_move_pct": payload.get("price_move_pct"),
            "price_move_high_pct": payload.get("price_move_high_pct"),
            "volatility_pct": payload.get("volatility_pct"),
            "volume_spike_ratio": payload.get("volume_spike_ratio"),
            "volume_spike_high_ratio": payload.get("volume_spike_high_ratio"),
        }
        if all(value is None for value in cleaned_payload.values()):
            override = self._db_session.get(AlertRuleOverride, asset_id)
            if override is not None:
                self._db_session.delete(override)
                self._db_session.commit()
            return self.get_asset_alert_thresholds(asset_id)

        override = self._db_session.get(AlertRuleOverride, asset_id)
        if override is None:
            override = AlertRuleOverride(asset_id=asset_id)
            self._db_session.add(override)

        override.price_move_pct = cleaned_payload["price_move_pct"]
        override.price_move_high_pct = cleaned_payload["price_move_high_pct"]
        override.volatility_pct = cleaned_payload["volatility_pct"]
        override.volume_spike_ratio = cleaned_payload["volume_spike_ratio"]
        override.volume_spike_high_ratio = cleaned_payload["volume_spike_high_ratio"]
        self._db_session.commit()
        return self.get_asset_alert_thresholds(asset_id)

    def get_asset_history(
        self,
        asset_id: str,
        limit: int = 100,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> AssetHistoryResponse:
        rows = self._get_asset_rows(
            asset_id=asset_id,
            limit=limit,
            start_at=start_at,
            end_at=end_at,
        )
        return self._build_asset_history_response(asset_id=asset_id, rows=rows)

    def _build_history_analytics(
        self,
        rows: list[CryptoPriceSnapshot],
    ) -> AssetHistoryAnalyticsResponse | None:
        if not rows:
            return None

        ordered_rows = list(reversed(rows))
        prices = [float(row.current_price_usd) for row in ordered_rows]
        latest_price = prices[-1]
        first_price = prices[0]
        window_change_usd = latest_price - first_price
        window_change_pct = 0.0 if first_price == 0 else (window_change_usd / first_price) * 100

        returns = []
        for previous_price, current_price in zip(prices, prices[1:], strict=False):
            if previous_price == 0:
                continue
            returns.append(((current_price - previous_price) / previous_price) * 100)

        def moving_average(window: int) -> float | None:
            if len(prices) < window:
                return None
            window_prices = prices[-window:]
            return sum(window_prices) / len(window_prices)

        return AssetHistoryAnalyticsResponse(
            latest_price_usd=latest_price,
            window_change_usd=window_change_usd,
            window_change_pct=window_change_pct,
            moving_average_5=moving_average(5),
            moving_average_10=moving_average(10),
            rolling_volatility_pct=pstdev(returns) if len(returns) >= 2 else None,
            highest_price_usd=max(prices),
            lowest_price_usd=min(prices),
        )

    def _build_asset_history_response(
        self,
        asset_id: str,
        rows: list[CryptoPriceSnapshot],
    ) -> AssetHistoryResponse:
        snapshots = [MarketSnapshotResponse.model_validate(row) for row in rows]
        latest_row = rows[0] if rows else None
        analytics = self._build_history_analytics(rows)

        return AssetHistoryResponse(
            asset_id=asset_id,
            symbol=latest_row.symbol if latest_row else None,
            name=latest_row.name if latest_row else None,
            points=len(snapshots),
            analytics=analytics,
            snapshots=snapshots,
        )

    def _get_asset_rows(
        self,
        asset_id: str,
        limit: int,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[CryptoPriceSnapshot]:
        statement = select(CryptoPriceSnapshot).where(CryptoPriceSnapshot.asset_id == asset_id)

        if start_at is not None:
            statement = statement.where(CryptoPriceSnapshot.snapshot_at >= start_at)
        if end_at is not None:
            statement = statement.where(CryptoPriceSnapshot.snapshot_at <= end_at)

        return self._db_session.scalars(
            statement.order_by(desc(CryptoPriceSnapshot.snapshot_at)).limit(limit)
        ).all()

    def get_market_alerts(self, asset_id: str | None = None) -> list[MarketAlertResponse]:
        alerts: list[MarketAlertResponse] = []
        now = datetime.now(UTC)
        latest_rows = self._db_session.scalars(self._latest_snapshots_statement()).all()
        if asset_id is not None:
            latest_rows = [row for row in latest_rows if row.asset_id == asset_id]

        for row in latest_rows:
            thresholds = self._get_alert_thresholds(row.asset_id)
            change_24h = float(row.price_change_percentage_24h or 0)
            if abs(change_24h) >= thresholds["price_move_pct"]:
                severity = "high" if abs(change_24h) >= thresholds["price_move_high_pct"] else "medium"
                direction = "up" if change_24h >= 0 else "down"
                alerts.append(
                    MarketAlertResponse(
                        severity=severity,
                        category="price_move",
                        title=f"{row.symbol} 24h move",
                        message=f"{row.name} is {direction} {abs(change_24h):.2f}% in the last 24 hours.",
                        observed_value=abs(change_24h),
                        threshold_value=thresholds["price_move_pct"],
                        high_threshold_value=thresholds["price_move_high_pct"],
                        unit="%",
                        severity_reason=(
                            f"Observed 24h move {abs(change_24h):.2f}% exceeded the high threshold."
                            if severity == "high"
                            else f"Observed 24h move {abs(change_24h):.2f}% exceeded the warning threshold."
                        ),
                        asset_id=row.asset_id,
                        detected_at=now,
                    )
                )

            history_rows = self._get_asset_rows(asset_id=row.asset_id, limit=20)
            history = self._build_asset_history_response(asset_id=row.asset_id, rows=history_rows)
            volatility = history.analytics.rolling_volatility_pct if history.analytics else None
            if volatility is not None and volatility >= thresholds["volatility_pct"]:
                alerts.append(
                    MarketAlertResponse(
                        severity="medium",
                        category="volatility",
                        title=f"{row.symbol} rolling volatility",
                        message=f"{row.name} shows elevated volatility at {volatility:.2f}% across the recent window.",
                        observed_value=volatility,
                        threshold_value=thresholds["volatility_pct"],
                        unit="%",
                        severity_reason=f"Observed rolling volatility {volatility:.2f}% exceeded the configured threshold.",
                        asset_id=row.asset_id,
                        detected_at=now,
                    )
                )

            volume_spike_alert = self._build_volume_spike_alert(
                row=row,
                history_rows=history_rows,
                thresholds=thresholds,
                detected_at=now,
            )
            if volume_spike_alert is not None:
                alerts.append(volume_spike_alert)

        pipeline_status = self._db_session.get(IngestionRunStatus, "coingecko")
        if pipeline_status is not None:
            if pipeline_status.status != "success":
                alerts.append(
                    MarketAlertResponse(
                        severity="high",
                        category="pipeline",
                        title="Ingestion failure",
                        message=f"Latest CoinGecko ingestion cycle failed. {pipeline_status.last_error or 'No error message captured.'}",
                        severity_reason="The latest ingestion cycle finished with status failed.",
                        asset_id=None,
                        detected_at=now,
                    )
                )
            elif pipeline_status.last_duration_seconds is not None and float(pipeline_status.last_duration_seconds) > 10:
                alerts.append(
                    MarketAlertResponse(
                        severity="low",
                        category="pipeline",
                        title="Slow ingestion cycle",
                        message=f"Latest CoinGecko ingestion cycle took {float(pipeline_status.last_duration_seconds):.2f}s.",
                        observed_value=float(pipeline_status.last_duration_seconds),
                        threshold_value=10.0,
                        unit="s",
                        severity_reason="Cycle duration exceeded the slow-cycle threshold.",
                        asset_id=None,
                        detected_at=now,
                    )
                )

            lag_alert = self._build_feed_lag_alert(
                pipeline_status=pipeline_status,
                detected_at=now,
            )
            if lag_alert is not None:
                alerts.append(lag_alert)

        if not alerts:
            alerts.append(
                MarketAlertResponse(
                    severity="low",
                    category="system",
                    title="No active alerts",
                    message="No market or pipeline conditions currently exceed alert thresholds.",
                    severity_reason="All observed values are within configured thresholds.",
                    asset_id=None,
                    detected_at=now,
                )
            )

        severity_order = {"high": 0, "medium": 1, "low": 2}
        alerts.sort(key=lambda alert: severity_order.get(alert.severity, 99))
        return alerts

    def _get_alert_thresholds(self, asset_id: str) -> dict[str, float]:
        thresholds = self._settings.get_asset_alert_thresholds(asset_id)
        db_override = self._db_session.get(AlertRuleOverride, asset_id)
        if db_override is None:
            return thresholds

        if db_override.price_move_pct is not None:
            thresholds["price_move_pct"] = float(db_override.price_move_pct)
        if db_override.price_move_high_pct is not None:
            thresholds["price_move_high_pct"] = float(db_override.price_move_high_pct)
        if db_override.volatility_pct is not None:
            thresholds["volatility_pct"] = float(db_override.volatility_pct)
        if db_override.volume_spike_ratio is not None:
            thresholds["volume_spike_ratio"] = float(db_override.volume_spike_ratio)
        if db_override.volume_spike_high_ratio is not None:
            thresholds["volume_spike_high_ratio"] = float(db_override.volume_spike_high_ratio)
        return thresholds

    def _build_volume_spike_alert(
        self,
        row: CryptoPriceSnapshot,
        history_rows: list[CryptoPriceSnapshot],
        thresholds: dict[str, float],
        detected_at: datetime,
    ) -> MarketAlertResponse | None:
        if len(history_rows) < 4:
            return None

        ordered_rows = list(reversed(history_rows))
        latest_volume = float(ordered_rows[-1].total_volume_usd or 0)
        previous_volumes = [float(snapshot.total_volume_usd or 0) for snapshot in ordered_rows[:-1]]
        if latest_volume <= 0 or not previous_volumes:
            return None

        baseline_volume = sum(previous_volumes) / len(previous_volumes)
        if baseline_volume <= 0:
            return None

        volume_ratio = latest_volume / baseline_volume
        if volume_ratio < thresholds["volume_spike_ratio"]:
            return None

        severity = "high" if volume_ratio >= thresholds["volume_spike_high_ratio"] else "medium"
        return MarketAlertResponse(
            severity=severity,
            category="volume_spike",
            title=f"{row.symbol} volume spike",
            message=(
                f"{row.name} volume is {volume_ratio:.2f}x above its recent baseline "
                f"across the latest snapshot window."
            ),
            observed_value=volume_ratio,
            threshold_value=thresholds["volume_spike_ratio"],
            high_threshold_value=thresholds["volume_spike_high_ratio"],
            unit="x",
            severity_reason=(
                f"Observed volume ratio {volume_ratio:.2f}x exceeded the high threshold."
                if severity == "high"
                else f"Observed volume ratio {volume_ratio:.2f}x exceeded the warning threshold."
            ),
            asset_id=row.asset_id,
            detected_at=detected_at,
        )

    def _build_feed_lag_alert(
        self,
        pipeline_status: IngestionRunStatus,
        detected_at: datetime,
    ) -> MarketAlertResponse | None:
        if pipeline_status.last_success_at is None:
            return None

        last_success_at = pipeline_status.last_success_at
        if last_success_at.tzinfo is None:
            last_success_at = last_success_at.replace(tzinfo=UTC)

        lag_seconds = (detected_at - last_success_at).total_seconds()
        warning_threshold = self._settings.ingestion_interval_seconds * self._settings.alert_feed_lag_warn_multiplier
        if lag_seconds <= warning_threshold:
            return None

        high_threshold = self._settings.ingestion_interval_seconds * self._settings.alert_feed_lag_high_multiplier
        severity = "high" if lag_seconds > high_threshold else "medium"
        lag_minutes = lag_seconds / 60
        return MarketAlertResponse(
            severity=severity,
            category="feed_lag",
            title="Feed lag detected",
            message=(
                f"Live feed is behind schedule. Last successful CoinGecko update was "
                f"{lag_minutes:.1f} minutes ago."
            ),
            observed_value=lag_seconds,
            threshold_value=warning_threshold,
            high_threshold_value=high_threshold,
            unit="s",
            severity_reason=(
                f"Feed lag reached {lag_seconds:.0f}s and exceeded the high threshold."
                if severity == "high"
                else f"Feed lag reached {lag_seconds:.0f}s and exceeded the warning threshold."
            ),
            asset_id=None,
            detected_at=detected_at,
        )
