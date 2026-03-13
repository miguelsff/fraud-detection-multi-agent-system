"""Async SQLAlchemy engine and session configuration."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .orm_models import Base
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.effective_database_url,
    echo=settings.app_env == "development",  # Log SQL in development
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Allow accessing attributes after commit
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database by creating all tables.

    For development only. In production, use Alembic migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
