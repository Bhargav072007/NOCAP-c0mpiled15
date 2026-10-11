"""
Database connection and session management.

Supports two modes controlled by the DATABASE_URL environment variable:
  - PostgreSQL (production): postgresql+psycopg://...
  - SQLite (local dev):      sqlite:///./nocap_local.db

Usage:
    from cloud.database import engine, SessionLocal, Base

    # Obtain a session in a FastAPI route:
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# Falls back to a local SQLite file so the app runs without AWS credentials.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "sqlite:///./nocap_local.db",
)

# connect_args is required for SQLite to allow multi-threaded access in
# FastAPI; it is ignored by the PostgreSQL driver.
connect_args: dict = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """All ORM models inherit from this class."""
    pass
