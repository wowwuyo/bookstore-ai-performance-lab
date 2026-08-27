"""System endpoints."""

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
