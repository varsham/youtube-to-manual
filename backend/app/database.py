from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    from app import models  # noqa: ensure models are registered
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Additive migration: add columns introduced after initial schema.
    # Each runs in its own transaction so a "column already exists" failure
    # (the common case, since create_all above already includes it) only
    # aborts that one statement instead of poisoning - and silently
    # rolling back - the create_all transaction on Postgres.
    for col_ddl in ["ALTER TABLE jobs ADD COLUMN log_messages JSON"]:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(col_ddl))
        except Exception:
            pass  # Column already exists
