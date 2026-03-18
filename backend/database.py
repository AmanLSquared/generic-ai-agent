import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dashboard_builder.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def migrate_db():
    """Safely add new columns to existing databases (SQLite ALTER TABLE is idempotent via try/except)."""
    from sqlalchemy import text
    new_columns = [
        ("dashboards", "asana_scope_type", "TEXT"),
        ("dashboards", "asana_scope_gid", "TEXT"),
        ("dashboards", "asana_scope_name", "TEXT"),
    ]
    async with engine.begin() as conn:
        for table, col, col_type in new_columns:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
            except Exception:
                pass  # Column already exists
