from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


# Connect args for SQLite to allow multiple threads with async engine
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session per request.
    Rolls back automatically on unhandled exceptions and ensures clean closure.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """
    Creates all database tables defined on Base metadata.
    Invoked at application startup and during database initialization.
    Safely migrates missing columns on existing SQLite databases.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _migrate_sqlite_columns(connection):
            from sqlalchemy import text
            try:
                res = connection.execute(text("PRAGMA table_info(audit_logs)"))
                existing_cols = {row[1] for row in res.fetchall()}
                if "entry_hash" not in existing_cols:
                    connection.execute(text("ALTER TABLE audit_logs ADD COLUMN entry_hash VARCHAR(64)"))
                if "prev_hash" not in existing_cols:
                    connection.execute(text("ALTER TABLE audit_logs ADD COLUMN prev_hash VARCHAR(64)"))

                res_agents = connection.execute(text("PRAGMA table_info(agent_registry)"))
                agent_cols = {row[1] for row in res_agents.fetchall()}
                if "department" not in agent_cols:
                    connection.execute(text("ALTER TABLE agent_registry ADD COLUMN department VARCHAR(100) DEFAULT 'Retail Commerce'"))
                if "model_provider" not in agent_cols:
                    connection.execute(text("ALTER TABLE agent_registry ADD COLUMN model_provider VARCHAR(100) DEFAULT 'Google Gemini'"))
                if "model_version" not in agent_cols:
                    connection.execute(text("ALTER TABLE agent_registry ADD COLUMN model_version VARCHAR(100) DEFAULT 'gemini-1.5-pro'"))
                if "owner_tenant" not in agent_cols:
                    connection.execute(text("ALTER TABLE agent_registry ADD COLUMN owner_tenant VARCHAR(100) DEFAULT 'KON Retail Org'"))
            except Exception:
                pass

        if "sqlite" in settings.DATABASE_URL:
            await conn.run_sync(_migrate_sqlite_columns)
