import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def wait_for_database(max_attempts: int = 20, sleep_seconds: int = 3) -> None:
    """
    A lightweight retry loop is enough for local Compose startup.
    In production, readiness is usually delegated to orchestration and retries in callers.
    """

    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connection established")
            return
        except Exception as exc:  # pragma: no cover - operational retry path
            logger.warning("Database not ready yet (attempt %s/%s): %s", attempt, max_attempts, exc)
            time.sleep(sleep_seconds)

    raise RuntimeError("Database did not become ready within the expected startup window")

