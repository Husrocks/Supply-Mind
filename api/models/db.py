"""
SupplyMind — Database Base Configuration
Defines the engine, sessions, and core models registry base.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)

# Core Async Engine setup
# Uses database_url (conditionally adjusted for SQLite to avoid invalid argument errors)
if settings.database_url.startswith("sqlite"):
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True
    )
else:
    engine = create_async_engine(
        settings.database_url,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True
    )

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    """Declarative Base registry class for database schemas."""
    pass

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependable for async database session scoping."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
