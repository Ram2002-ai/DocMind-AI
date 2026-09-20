"""FastAPI application main entry point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import os
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.db.session import engine
from app.db.base import Base
import app.models  # noqa: F401 - register SQLAlchemy mappers before create_all
from app.api.routes import health, threads

logger = get_logger(__name__)

# Setup logging
setup_logging()

# Create database tables
Base.metadata.create_all(bind=engine)

# Lightweight migration for existing SQLite databases
if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import inspect, text

    with engine.connect() as conn:
        inspector = inspect(conn)
        if "documents" in inspector.get_table_names():
            columns = {col["name"] for col in inspector.get_columns("documents")}
            if "conversation_id" not in columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN conversation_id INTEGER"))
                conn.commit()
                logger.info("Added documents.conversation_id column")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # Vite auto-increments its dev port (5173, 5174, 5175, ...) whenever the
    # previous one is still in use, so pin CORS to "any localhost port" in
    # addition to the explicit allow-list above rather than hardcoding one.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(health.router, tags=["Health"])
app.include_router(threads.router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DocuMind AI API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )
