import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuthSession, User, utcnow
from app.shared.config import get_settings


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def open_session(session: AsyncSession, user: User) -> str:
    token = secrets.token_urlsafe(32)
    row = AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        created_at=utcnow(),
        expires_at=utcnow() + timedelta(seconds=get_settings().session_ttl_sec),
    )
    session.add(row)
    await session.flush()
    return token


async def user_for_token(session: AsyncSession, token: str) -> User | None:
    result = await session.execute(
        select(User)
        .join(AuthSession, AuthSession.user_id == User.id)
        .where(
            AuthSession.token_hash == hash_token(token),
            AuthSession.expires_at > utcnow(),
        )
    )
    return result.scalar_one_or_none()


async def close_session(session: AsyncSession, token: str) -> None:
    await session.execute(
        delete(AuthSession).where(AuthSession.token_hash == hash_token(token))
    )
