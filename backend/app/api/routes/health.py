"""Health check endpoints"""
from fastapi import APIRouter
from app.schemas import HealthResponse
from app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check application health"""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        database="connected",
        vector_db="faiss (in-memory per thread)",
    )


@router.get("/api/v1/health", response_model=HealthResponse)
async def api_health_check():
    """Check API health"""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        database="connected",
        vector_db="faiss (in-memory per thread)",
    )
