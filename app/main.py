from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.market import router as market_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")

