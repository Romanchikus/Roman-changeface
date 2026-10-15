import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.shared.config import get_settings

_engines: dict[int, AsyncEngine] = {}
_factories: dict[int, async_sessionmaker[AsyncSession]] = {}


def sync_database_url(url: str) -> str:
    if url.startswith("sqlite+aiosqlite://"):
        return "sqlite+pysqlite://" + url.removeprefix("sqlite+aiosqlite://")
    if url.startswith("sqlite://"):
        return "sqlite+pysqlite://" + url.removeprefix("sqlite://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def async_database_url(url: str) -> str:
    if url.startswith("sqlite+pysqlite://"):
        return "sqlite+aiosqlite://" + url.removeprefix("sqlite+pysqlite://")
    if url.startswith("sqlite://"):
        return "sqlite+aiosqlite://" + url.removeprefix("sqlite://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def get_engine() -> AsyncEngine:
    key = id(asyncio.get_running_loop())
    engine = _engines.get(key)
    if engine is None:
        url = async_database_url(get_settings().database_url)
        kwargs: dict[str, object] = {}
        if url.startswith("sqlite"):
            kwargs["poolclass"] = NullPool
            kwargs["connect_args"] = {"timeout": 30}
        else:
            kwargs["pool_pre_ping"] = True
        engine = create_async_engine(url, **kwargs)
        _engines[key] = engine
        _factories[key] = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    return _factories[id(asyncio.get_running_loop())]


async def dispose_loop_engine() -> None:
    """Dispose the engine for the current loop."""
    key = id(asyncio.get_running_loop())
    engine = _engines.pop(key, None)
    _factories.pop(key, None)
    if engine is not None:
        await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
