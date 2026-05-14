from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.db.models import IngestionRunStatus
from app.schemas.market import HealthResponse, IngestionStatusResponse

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck(db: Session = Depends(get_db_session)) -> HealthResponse:
    db.execute(text("SELECT 1"))
    pipeline_row = db.get(IngestionRunStatus, "coingecko")
    pipeline = None
    if pipeline_row is not None:
        pipeline = IngestionStatusResponse(
            source=pipeline_row.source,
            status=pipeline_row.status,
            last_attempt_at=pipeline_row.last_attempt_at,
            last_success_at=pipeline_row.last_success_at,
            last_error=pipeline_row.last_error,
            last_duration_seconds=float(pipeline_row.last_duration_seconds) if pipeline_row.last_duration_seconds is not None else None,
            rows_fetched=pipeline_row.rows_fetched,
            rows_inserted=pipeline_row.rows_inserted,
        )
    return HealthResponse(status="ok", database="reachable", pipeline=pipeline)
