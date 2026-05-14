from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AlertRuleOverride, CryptoPriceSnapshot, IngestionRunStatus, WatchlistAsset
from app.services.market_service import MarketService


class DummySettings:
    def __init__(self, overrides: dict[str, dict[str, float]] | None = None) -> None:
        self.ingestion_interval_seconds = 300
        self.alert_feed_lag_warn_multiplier = 2.0
        self.alert_feed_lag_high_multiplier = 4.0
        self._overrides = overrides or {}

    def get_asset_alert_thresholds(self, asset_id: str) -> dict[str, float]:
        defaults = {
            "price_move_pct": 3.0,
            "price_move_high_pct": 5.0,
            "volatility_pct": 2.0,
            "volume_spike_ratio": 1.5,
            "volume_spike_high_ratio": 2.5,
        }
        defaults.update(self._overrides.get(asset_id, {}))
        return defaults


def _build_snapshot(
    asset_id: str,
    symbol: str,
    name: str,
    snapshot_at: datetime,
    current_price_usd: str,
    market_cap_usd: str,
    total_volume_usd: str,
) -> CryptoPriceSnapshot:
    return CryptoPriceSnapshot(
        asset_id=asset_id,
        symbol=symbol,
        name=name,
        current_price_usd=Decimal(current_price_usd),
        market_cap_usd=Decimal(market_cap_usd),
        total_volume_usd=Decimal(total_volume_usd),
        price_change_percentage_24h=Decimal("1.2500"),
        snapshot_at=snapshot_at,
        source="coingecko",
    )


def _build_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return testing_session()


def test_get_latest_snapshots_returns_latest_row_per_asset() -> None:
    session = _build_session()
    base_time = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    session.add_all(
        [
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time, "100000", "2000000", "500000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=5), "101000", "2100000", "550000"),
            _build_snapshot("ethereum", "ETH", "Ethereum", base_time, "4000", "1000000", "300000"),
        ]
    )
    session.commit()

    service = MarketService(session)
    rows = service.get_latest_snapshots()

    assert len(rows) == 2
    assert rows[0].asset_id == "bitcoin"
    assert rows[0].current_price_usd == Decimal("101000")
    assert rows[1].asset_id == "ethereum"


def test_get_market_summary_aggregates_latest_snapshots_only() -> None:
    session = _build_session()
    base_time = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    session.add_all(
        [
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time, "100000", "2000000", "500000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=5), "101000", "2100000", "550000"),
            _build_snapshot("ethereum", "ETH", "Ethereum", base_time, "4000", "1000000", "300000"),
        ]
    )
    session.commit()

    service = MarketService(session)
    summary = service.get_market_summary()

    assert summary.tracked_assets == 2
    assert summary.total_market_cap_usd == Decimal("3100000.00")
    assert summary.total_volume_usd == Decimal("850000.00")


def test_get_asset_history_returns_descending_snapshots_with_limit() -> None:
    session = _build_session()
    base_time = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    session.add_all(
        [
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time, "100000", "2000000", "500000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=5), "101000", "2100000", "550000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=10), "102000", "2200000", "600000"),
        ]
    )
    session.commit()

    service = MarketService(session)
    history = service.get_asset_history(asset_id="bitcoin", limit=2)

    assert history.asset_id == "bitcoin"
    assert history.symbol == "BTC"
    assert history.points == 2
    assert [snapshot.current_price_usd for snapshot in history.snapshots] == [
        Decimal("102000"),
        Decimal("101000"),
    ]


def test_get_asset_history_includes_derived_analytics() -> None:
    session = _build_session()
    base_time = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    session.add_all(
        [
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time, "100", "2000000", "500000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=5), "110", "2100000", "550000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=10), "120", "2200000", "600000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=15), "130", "2300000", "650000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=20), "140", "2400000", "700000"),
        ]
    )
    session.commit()

    service = MarketService(session)
    history = service.get_asset_history(asset_id="bitcoin", limit=10)

    assert history.analytics is not None
    assert history.analytics.latest_price_usd == 140.0
    assert history.analytics.window_change_usd == 40.0
    assert history.analytics.window_change_pct == 40.0
    assert history.analytics.moving_average_5 == 120.0
    assert history.analytics.highest_price_usd == 140.0
    assert history.analytics.lowest_price_usd == 100.0


def test_get_market_alerts_includes_market_and_pipeline_signals() -> None:
    session = _build_session()
    base_time = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    session.add_all(
        [
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time, "100", "2000000", "100000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=5), "110", "2100000", "120000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=10), "95", "2200000", "90000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=15), "105", "2300000", "80000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=20), "107", "2400000", "250000"),
        ]
    )
    session.add(
        IngestionRunStatus(
            source="coingecko",
            status="failed",
            last_error="timeout during fetch",
        )
    )
    session.commit()

    service = MarketService(session)
    alerts = service.get_market_alerts()

    assert any(alert.category == "pipeline" for alert in alerts)
    assert any(alert.category in {"price_move", "volatility", "volume_spike"} for alert in alerts)


def test_get_market_alerts_filters_by_asset_and_detects_feed_lag() -> None:
    session = _build_session()
    base_time = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    session.add_all(
        [
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time, "100", "2000000", "100000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=5), "101", "2100000", "100000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=10), "102", "2200000", "100000"),
            _build_snapshot("ethereum", "ETH", "Ethereum", base_time, "50", "1500000", "50000"),
            _build_snapshot("ethereum", "ETH", "Ethereum", base_time + timedelta(minutes=5), "52", "1600000", "50000"),
            _build_snapshot("ethereum", "ETH", "Ethereum", base_time + timedelta(minutes=10), "53", "1700000", "50000"),
        ]
    )
    session.add(
        IngestionRunStatus(
            source="coingecko",
            status="success",
            last_success_at=datetime.now(UTC) - timedelta(minutes=20),
            last_duration_seconds=2.5,
        )
    )
    session.commit()

    service = MarketService(session)
    alerts = service.get_market_alerts(asset_id="bitcoin")

    assert any(alert.category == "feed_lag" for alert in alerts)
    assert all(alert.asset_id in {None, "bitcoin"} for alert in alerts)


def test_get_market_alerts_respects_asset_specific_thresholds() -> None:
    session = _build_session()
    base_time = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    session.add_all(
        [
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time, "100", "2000000", "100000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=5), "101", "2100000", "100000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=10), "102", "2200000", "100000"),
        ]
    )
    session.commit()

    service = MarketService(session)
    service._settings = DummySettings(
        overrides={
            "bitcoin": {
                "price_move_pct": 1.0,
                "price_move_high_pct": 1.2,
            }
        }
    )
    alerts = service.get_market_alerts(asset_id="bitcoin")

    assert any(alert.category == "price_move" for alert in alerts)
    price_move_alert = next(alert for alert in alerts if alert.category == "price_move")
    assert price_move_alert.observed_value is not None
    assert price_move_alert.threshold_value == 1.0
    assert price_move_alert.severity_reason is not None


def test_replace_watchlist_asset_ids_persists_unique_values() -> None:
    session = _build_session()
    session.add(WatchlistAsset(asset_id="ethereum"))
    session.commit()

    service = MarketService(session)
    saved_asset_ids = service.replace_watchlist_asset_ids(["bitcoin", "ethereum", "bitcoin"])

    assert saved_asset_ids == ["bitcoin", "ethereum"]
    assert service.get_watchlist_asset_ids() == ["bitcoin", "ethereum"]


def test_update_asset_alert_thresholds_persists_overrides() -> None:
    session = _build_session()
    service = MarketService(session)

    response = service.update_asset_alert_thresholds(
        "bitcoin",
        {
            "price_move_pct": 2.1,
            "price_move_high_pct": None,
            "volatility_pct": 1.8,
            "volume_spike_ratio": None,
            "volume_spike_high_ratio": 2.2,
        },
    )

    override = session.get(AlertRuleOverride, "bitcoin")
    assert override is not None
    assert float(override.price_move_pct) == 2.1
    assert override.price_move_high_pct is None
    assert response.effective.price_move_pct == 2.1
    assert response.effective.volatility_pct == 1.8
