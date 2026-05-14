import asyncio

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.ingestion.pipeline import CryptoIngestionPipeline

configure_logging(get_settings().log_level)


async def main() -> None:
    with SessionLocal() as session:
        pipeline = CryptoIngestionPipeline(session)
        await pipeline.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
