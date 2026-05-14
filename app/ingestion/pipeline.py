import asyncio
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import CryptoPriceSnapshot, IngestionRunStatus
from app.ingestion.coingecko_client import CoinGeckoClient

logger = logging.getLogger(__name__)
settings = get_settings()


def _to_decimal(value: float | int | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


class CryptoIngestionPipeline:
    def __init__(self, db_session: Session) -> None:
        self._db_session = db_session
        self._client = CoinGeckoClient()

    async def ingest_once(self) -> int:
        cycle_started_at = time.perf_counter()
        attempt_started_at = datetime.now(timezone.utc)
        logger.info("Starting market ingestion cycle for assets: %s", ",".join(settings.asset_id_list))
        payload = await self._client.fetch_markets(settings.asset_id_list)
        rows = [
            {
                "asset_id": item["id"],
                "symbol": str(item["symbol"]).upper(),
                "name": item["name"],
                "current_price_usd": _to_decimal(item.get("current_price")),
                "market_cap_usd": _to_decimal(item.get("market_cap")),
                "total_volume_usd": _to_decimal(item.get("total_volume")),
                "price_change_percentage_24h": _to_decimal(item.get("price_change_percentage_24h")),
                "snapshot_at": item["snapshot_at"],
                "source": "coingecko",
            }
            for item in payload
        ]

        if not rows:
            logger.warning("No rows returned from CoinGecko")
            self._record_run_status(
                status="success",
                last_attempt_at=attempt_started_at,
                last_success_at=attempt_started_at,
                last_error=None,
                last_duration_seconds=time.perf_counter() - cycle_started_at,
                rows_fetched=0,
                rows_inserted=0,
            )
            return 0

        statement = insert(CryptoPriceSnapshot).values(rows)
        statement = statement.on_conflict_do_nothing(
            index_elements=["asset_id", "snapshot_at"],
        )
        statement = statement.returning(CryptoPriceSnapshot.id)
        result = self._db_session.execute(statement)
        self._db_session.commit()

        inserted = len(result.scalars().all())
        cycle_duration = time.perf_counter() - cycle_started_at
        self._record_run_status(
            status="success",
            last_attempt_at=attempt_started_at,
            last_success_at=attempt_started_at,
            last_error=None,
            last_duration_seconds=cycle_duration,
            rows_fetched=len(rows),
            rows_inserted=inserted,
        )
        logger.info(
            "Persisted %s market snapshots out of %s fetched in %.2fs",
            inserted,
            len(rows),
            cycle_duration,
        )
        return inserted

    async def run_forever(self) -> None:
        while True:
            try:
                await self.ingest_once()
            except Exception as exc:
                self._db_session.rollback()
                self._record_run_status(
                    status="failed",
                    last_attempt_at=datetime.now(timezone.utc),
                    last_success_at=None,
                    last_error=str(exc)[:500],
                    last_duration_seconds=None,
                    rows_fetched=None,
                    rows_inserted=None,
                )
                logger.exception("Market ingestion cycle failed")
            await asyncio.sleep(settings.ingestion_interval_seconds)

    def _record_run_status(
        self,
        *,
        status: str,
        last_attempt_at: datetime,
        last_success_at: datetime | None,
        last_error: str | None,
        last_duration_seconds: float | None,
        rows_fetched: int | None,
        rows_inserted: int | None,
    ) -> None:
        current_status = self._db_session.get(IngestionRunStatus, "coingecko")
        if current_status is None:
            current_status = IngestionRunStatus(source="coingecko", status=status)
            self._db_session.add(current_status)

        current_status.status = status
        current_status.last_attempt_at = last_attempt_at
        if last_success_at is not None:
            current_status.last_success_at = last_success_at
        current_status.last_error = last_error
        current_status.last_duration_seconds = Decimal(str(last_duration_seconds)) if last_duration_seconds is not None else None
        current_status.rows_fetched = rows_fetched
        current_status.rows_inserted = rows_inserted
        self._db_session.commit()
