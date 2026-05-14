import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings

settings = get_settings()


class CoinGeckoClient:
    def __init__(self) -> None:
        self._base_url = settings.coingecko_base_url.rstrip("/")
        self._max_attempts = 3
        self._base_backoff_seconds = 1.5

    async def fetch_markets(self, asset_ids: list[str]) -> list[dict[str, Any]]:
        params = {
            "vs_currency": settings.coingecko_vs_currency,
            "ids": ",".join(asset_ids),
            "order": "market_cap_desc",
            "per_page": len(asset_ids),
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h",
        }

        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(f"{self._base_url}/coins/markets", params=params)
                    response.raise_for_status()
                    payload: list[dict[str, Any]] = response.json()
                break
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt == self._max_attempts:
                    raise
                backoff = self._base_backoff_seconds * attempt
                await asyncio.sleep(backoff)
        else:  # pragma: no cover
            raise RuntimeError("CoinGecko fetch failed without a captured exception") from last_error

        snapshot_time = datetime.now(timezone.utc)
        for item in payload:
            item["snapshot_at"] = snapshot_time

        return payload
