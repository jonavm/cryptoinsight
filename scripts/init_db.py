import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import wait_for_database

configure_logging(get_settings().log_level)
logger = logging.getLogger(__name__)


def main() -> None:
    wait_for_database()
    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations applied successfully")


if __name__ == "__main__":
    main()
