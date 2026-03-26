"""Async SQLAlchemy engine and session factory for user_db."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.user_db_url,
    pool_size=3,
    max_overflow=2,
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Yield an async database session, closing it when done."""
    async with async_session() as session:
        yield session
