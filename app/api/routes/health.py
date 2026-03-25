from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health/live", response_model=HealthResponse, summary="Liveness probe")
async def live_healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse, summary="Readiness probe")
async def ready_healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")
