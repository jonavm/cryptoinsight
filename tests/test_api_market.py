from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db_session
from app.db.base import Base
from app.db.models import AlertRuleOverride, CryptoPriceSnapshot, IngestionRunStatus, WatchlistAsset
from app.main import app


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


def _build_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _build_client(session_factory: sessionmaker[Session]) -> TestClient:
    def override_get_db_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session
    client = TestClient(app)
    return client


def test_health_endpoint_returns_ok() -> None:
    session_factory = _build_session_factory()
    session = session_factory()
    session.add(
        IngestionRunStatus(
            source="coingecko",
            status="success",
            rows_fetched=3,
            rows_inserted=3,
        )
    )
    session.commit()
    session.close()
    client = _build_client(session_factory)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["pipeline"]["source"] == "coingecko"


def test_watchlist_endpoints_round_trip() -> None:
    session_factory = _build_session_factory()
    session = session_factory()
    session.add(WatchlistAsset(asset_id="ethereum"))
    session.commit()
    session.close()
    client = _build_client(session_factory)

    get_response = client.get("/api/v1/market/watchlist")

    assert get_response.status_code == 200
    assert get_response.json()["asset_ids"] == ["ethereum"]

    put_response = client.put(
        "/api/v1/market/watchlist",
        json={"asset_ids": ["bitcoin", "solana", "bitcoin"]},
    )

    assert put_response.status_code == 200
    assert put_response.json()["asset_ids"] == ["bitcoin", "solana"]

    refreshed_response = client.get("/api/v1/market/watchlist")
    assert refreshed_response.status_code == 200
    assert refreshed_response.json()["asset_ids"] == ["bitcoin", "solana"]


def test_alert_rule_endpoints_round_trip() -> None:
    session_factory = _build_session_factory()
    session = session_factory()
    session.add(AlertRuleOverride(asset_id="bitcoin", price_move_pct=Decimal("2.5000")))
    session.commit()
    session.close()
    client = _build_client(session_factory)

    get_response = client.get("/api/v1/market/alert-rules/bitcoin")

    assert get_response.status_code == 200
    assert get_response.json()["overrides"]["price_move_pct"] == 2.5

    put_response = client.put(
        "/api/v1/market/alert-rules/bitcoin",
        json={
            "price_move_pct": 1.8,
            "price_move_high_pct": 3.0,
            "volatility_pct": None,
            "volume_spike_ratio": 1.4,
            "volume_spike_high_ratio": None,
        },
    )

    assert put_response.status_code == 200
    assert put_response.json()["effective"]["price_move_pct"] == 1.8
    assert put_response.json()["effective"]["price_move_high_pct"] == 3.0


def test_history_endpoint_filters_by_time_range() -> None:
    session_factory = _build_session_factory()
    session = session_factory()
    base_time = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    session.add_all(
        [
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time, "100000", "2000000", "500000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=5), "101000", "2100000", "550000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=10), "102000", "2200000", "600000"),
        ]
    )
    session.commit()
    session.close()
    client = _build_client(session_factory)

    response = client.get(
        "/api/v1/market/history/bitcoin",
        params={
            "start_at": (base_time + timedelta(minutes=5)).isoformat(),
            "end_at": (base_time + timedelta(minutes=10)).isoformat(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["points"] == 2
    assert payload["analytics"]["latest_price_usd"] == 102000.0
    assert payload["snapshots"][0]["current_price_usd"] == "102000.00000000"
    assert payload["snapshots"][1]["current_price_usd"] == "101000.00000000"


def test_history_endpoint_rejects_invalid_time_window() -> None:
    session_factory = _build_session_factory()
    client = _build_client(session_factory)
    start_at = datetime(2026, 5, 14, 0, 0, tzinfo=UTC)
    end_at = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)

    response = client.get(
        "/api/v1/market/history/bitcoin",
        params={"start_at": start_at.isoformat(), "end_at": end_at.isoformat()},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "start_at must be earlier than or equal to end_at"


def test_alerts_endpoint_returns_pipeline_alert() -> None:
    session_factory = _build_session_factory()
    session = session_factory()
    base_time = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    session.add_all(
        [
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time, "100000", "2000000", "100000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=5), "101000", "2100000", "120000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=10), "102000", "2200000", "90000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=15), "103000", "2300000", "85000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=20), "104000", "2400000", "250000"),
            _build_snapshot("ethereum", "ETH", "Ethereum", base_time, "3000", "1500000", "50000"),
        ]
    )
    session.add(
        IngestionRunStatus(
            source="coingecko",
            status="failed",
            last_error="upstream timeout",
        )
    )
    session.commit()
    session.close()
    client = _build_client(session_factory)

    response = client.get("/api/v1/market/alerts")

    assert response.status_code == 200
    payload = response.json()
    assert any(alert["category"] == "pipeline" for alert in payload)
    assert any(alert["severity"] == "high" for alert in payload)
    assert any(alert["severity_reason"] for alert in payload)


def test_alerts_endpoint_supports_asset_filter() -> None:
    session_factory = _build_session_factory()
    session = session_factory()
    base_time = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    session.add_all(
        [
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time, "100000", "2000000", "100000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=5), "101000", "2100000", "100000"),
            _build_snapshot("bitcoin", "BTC", "Bitcoin", base_time + timedelta(minutes=10), "102000", "2200000", "100000"),
            _build_snapshot("ethereum", "ETH", "Ethereum", base_time, "3000", "1500000", "50000"),
            _build_snapshot("ethereum", "ETH", "Ethereum", base_time + timedelta(minutes=5), "3100", "1600000", "50000"),
            _build_snapshot("ethereum", "ETH", "Ethereum", base_time + timedelta(minutes=10), "3200", "1700000", "50000"),
        ]
    )
    session.add(
        IngestionRunStatus(
            source="coingecko",
            status="success",
            last_success_at=datetime.now(UTC) - timedelta(minutes=20),
        )
    )
    session.commit()
    session.close()
    client = _build_client(session_factory)

    response = client.get("/api/v1/market/alerts", params={"asset_id": "bitcoin"})

    assert response.status_code == 200
    payload = response.json()
    assert any(alert["category"] == "feed_lag" for alert in payload)
    assert all(alert["asset_id"] in (None, "bitcoin") for alert in payload)
    assert all("severity_reason" in alert for alert in payload)
