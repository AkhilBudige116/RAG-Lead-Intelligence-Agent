import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool, QueuePool
from app.core.config import settings
from app.core.logging import logger

raw_db_url = settings.DATABASE_URL or ""

# Enforce production database requirements
if settings.is_production and (not raw_db_url or raw_db_url.startswith("sqlite")):
    raise RuntimeError(
        "CRITICAL CONFIGURATION ERROR: SQLite is not supported in production serverless environments. "
        "Please set DATABASE_URL to a valid Supabase PostgreSQL connection string "
        "(e.g. postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres)."
    )

# Normalize postgres:// to postgresql:// for SQLAlchemy 2.0+ compatibility
normalized_db_url = raw_db_url
if normalized_db_url.startswith("postgres://"):
    normalized_db_url = normalized_db_url.replace("postgres://", "postgresql://", 1)

# Configure engine arguments based on driver and serverless execution mode
is_sqlite = normalized_db_url.startswith("sqlite")
engine_kwargs = {
    "pool_pre_ping": True,
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL / Supabase
    if settings.IS_SERVERLESS or settings.is_production:
        # Use NullPool for serverless functions (AWS Lambda / Vercel) to prevent connection leaks
        engine_kwargs["poolclass"] = NullPool
        logger.info("Configured SQLAlchemy NullPool for serverless PostgreSQL connection.")
    else:
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10

engine = create_engine(normalized_db_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

