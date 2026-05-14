import json
import logging
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = Field(default="real-time-crypto-data-platform", alias="PROJECT_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    coingecko_base_url: str = Field(default="https://api.coingecko.com/api/v3", alias="COINGECKO_BASE_URL")
    coingecko_vs_currency: str = Field(default="usd", alias="COINGECKO_VS_CURRENCY")
    coingecko_asset_ids: str = Field(default="bitcoin,ethereum,solana", alias="COINGECKO_ASSET_IDS")
    ingestion_interval_seconds: int = Field(default=300, alias="INGESTION_INTERVAL_SECONDS")
    alert_price_move_pct: float = Field(default=3.0, alias="ALERT_PRICE_MOVE_PCT")
    alert_price_move_high_pct: float = Field(default=5.0, alias="ALERT_PRICE_MOVE_HIGH_PCT")
    alert_volatility_pct: float = Field(default=2.0, alias="ALERT_VOLATILITY_PCT")
    alert_volume_spike_ratio: float = Field(default=1.5, alias="ALERT_VOLUME_SPIKE_RATIO")
    alert_volume_spike_high_ratio: float = Field(default=2.5, alias="ALERT_VOLUME_SPIKE_HIGH_RATIO")
    alert_feed_lag_warn_multiplier: float = Field(default=2.0, alias="ALERT_FEED_LAG_WARN_MULTIPLIER")
    alert_feed_lag_high_multiplier: float = Field(default=4.0, alias="ALERT_FEED_LAG_HIGH_MULTIPLIER")
    alert_rules_by_asset_raw: str = Field(default="{}", alias="ALERT_RULES_BY_ASSET")

    api_base_url: str = Field(default="http://api:8000", alias="API_BASE_URL")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def asset_id_list(self) -> list[str]:
        return [asset.strip() for asset in self.coingecko_asset_ids.split(",") if asset.strip()]

    @property
    def asset_alert_rules(self) -> dict[str, dict[str, float]]:
        try:
            parsed = json.loads(self.alert_rules_by_asset_raw)
        except json.JSONDecodeError:
            logger.warning("Failed to parse ALERT_RULES_BY_ASSET. Falling back to default alert thresholds.")
            return {}

        if not isinstance(parsed, dict):
            logger.warning("ALERT_RULES_BY_ASSET must decode to a JSON object. Falling back to default alert thresholds.")
            return {}

        normalized: dict[str, dict[str, float]] = {}
        for asset_id, rules in parsed.items():
            if not isinstance(asset_id, str) or not isinstance(rules, dict):
                continue
            normalized_rules: dict[str, float] = {}
            for key, value in rules.items():
                if isinstance(key, str) and isinstance(value, int | float):
                    normalized_rules[key] = float(value)
            normalized[asset_id] = normalized_rules
        return normalized

    def get_asset_alert_thresholds(self, asset_id: str) -> dict[str, float]:
        thresholds = {
            "price_move_pct": self.alert_price_move_pct,
            "price_move_high_pct": self.alert_price_move_high_pct,
            "volatility_pct": self.alert_volatility_pct,
            "volume_spike_ratio": self.alert_volume_spike_ratio,
            "volume_spike_high_ratio": self.alert_volume_spike_high_ratio,
        }
        thresholds.update(self.asset_alert_rules.get(asset_id, {}))
        return thresholds


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
