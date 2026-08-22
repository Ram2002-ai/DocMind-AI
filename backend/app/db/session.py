"""Database connection and session management"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import settings

# Create database engine. SQLite is the local default and needs this option
# because FastAPI can serve a request from a thread different to the creator.
engine_options = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **engine_options)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
