import asyncio
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.session import session_scope
from app.db.users import by_email, insert_user

POSTGRES_URL = os.environ.get(
    "POSTGRES_TEST_URL",
    "postgresql+psycopg://changeface:changeface@127.0.0.1:5433/changeface",
)


def test_failed_insert_rolls_back(client):
    email = "rollback@example.com"

    async def fail() -> None:
        async with session_scope() as session:
            await insert_user(session, email, "x")
            raise RuntimeError("fail the insert")

    with pytest.raises(RuntimeError):
        asyncio.run(fail())

    async def load():
        async with session_scope() as session:
            return await by_email(session, email)

    assert asyncio.run(load()) is None
    assert client.get("/api/health").status_code == 200


def test_postgres_query_and_rollback():
    email = f"rollback-{uuid.uuid4().hex}@example.com"

    async def run() -> str | None:
        engine = create_async_engine(POSTGRES_URL)
        try:
            async with engine.connect() as conn:
                ready = await conn.scalar(text("SELECT to_regclass('public.users')"))
            if ready is None:
                return "PostgreSQL has no users table"
            async with engine.connect() as conn:
                transaction = await conn.begin()
                await conn.execute(
                    text(
                        "INSERT INTO users (email, password_hash, created_at, last_activity_at) "
                        "VALUES (:email, 'x', NOW(), NOW())"
                    ),
                    {"email": email},
                )
                await transaction.rollback()
                found = await conn.scalar(
                    text("SELECT COUNT(*) FROM users WHERE email = :email"),
                    {"email": email},
                )
            if found != 0:
                return "row survived rollback"
            return None
        except Exception as exc:
            if "connect" in str(exc).lower() or "refused" in str(exc).lower():
                return "PostgreSQL is not running"
            raise
        finally:
            await engine.dispose()

    skipped = asyncio.run(run())
    if skipped == "row survived rollback":
        raise AssertionError(skipped)
    if skipped:
        pytest.skip(skipped)
