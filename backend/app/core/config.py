"""Application configuration from environment variables."""
from pathlib import Path
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

# Resolve backend/.env by absolute path (this file lives at
# backend/app/core/config.py) so settings load correctly no matter which
# directory uvicorn/python is launched from (backend/, backend/app/, repo root, ...).
_BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
# backend/app/ — the anchor for relative SQLite paths (see resolve_sqlite_path below).
_APP_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "DocuMind AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        """Treat common deployment labels as a disabled debug mode."""
        if isinstance(value, str) and value.lower() in {"release", "production", "prod"}:
            return False
        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        """Accept both JSON lists and the comma-separated .env convention."""
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value
    
    # Server
    API_V1_STR: str = "/api/v1"
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://docmind-ai-1-hd4f.onrender.com",
    ]
    
    # Database
    DATABASE_URL: str = "sqlite:///./documind.db"
    DATABASE_PRIVATE_URL: str = ""

    @model_validator(mode="after")
    def prefer_private_database_url(self):
        """Use Render's private database URL when the public URL is absent.

        A localhost PostgreSQL URL points back to the web service on Render,
        so it is also replaced when the private URL is available.
        """
        if not self.DATABASE_URL:
            self.DATABASE_URL = "sqlite:///./documind.db"

        database_host = self.DATABASE_URL.lower()
        if self.DATABASE_PRIVATE_URL and (
            self.DATABASE_URL.startswith("sqlite")
            or "@localhost" in database_host
            or "@127.0.0.1" in database_host
        ):
            self.DATABASE_URL = self.DATABASE_PRIVATE_URL
        return self

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def resolve_sqlite_path(cls, value: str) -> str:
        """Anchor relative sqlite:/// paths to backend/app (where documind.db
        actually lives) so the DB opens correctly regardless of whether
        uvicorn was launched from backend/, backend/app/, or the repo root.
        Absolute paths and non-sqlite URLs (e.g. postgresql://...) pass through untouched.
        """
        prefix = "sqlite:///"
        if not value.startswith(prefix):
            return value
        raw_path = value[len(prefix):]
        if raw_path == ":memory:" or Path(raw_path).is_absolute():
            return value
        resolved = (_APP_DIR / raw_path).resolve()
        return f"{prefix}{resolved.as_posix()}"
    
    # JWT
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION_NAME: str = "documents"
    
    # Groq LLM (OpenAI-compatible API)
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    # Vision-capable model for describing uploaded images (photos, charts, scans
    # with little/no machine-readable text) — OCR alone only captures text that
    # visually appears in the image, not what the image actually shows.
    GROQ_VISION_MODEL: str = "qwen/qwen3.6-27b"
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 2
    LLM_TEMPERATURE: float = 0.0
    
    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Document Processing
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 3
    RETRIEVAL_THRESHOLD: float = 0.5
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    UPLOAD_DIR: str = "data/uploads"
    EXTRACT_DIR: str = "data/extracted"
    
    # Supported file types
    SUPPORTED_FORMATS: List[str] = ["pdf", "png", "jpg", "jpeg", "docx", "txt", "md", "csv", "webp", "gif"]

    # LangGraph
    LANGGRAPH_CHECKPOINT_PATH: str = "data/langgraph_checkpoints.db"
    ALPHA_VANTAGE_API_KEY: str = ""
    
    class Config:
        # Load root first, then backend/.env so local backend settings win.
        env_file = (str(_ROOT_ENV_FILE), str(_BACKEND_ENV_FILE))
        case_sensitive = True
        extra = "ignore"


settings = Settings()
