"""Pydantic schemas for active API routes."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    vector_db: str
