from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, utcnow


async def by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def insert_user(session: AsyncSession, email: str, password_hash: str) -> User:
    now = utcnow()
    user = User(email=email, password_hash=password_hash, created_at=now, last_activity_at=now)
    session.add(user)
    await session.flush()
    return user


async def touch(session: AsyncSession, user: User) -> User:
    """Update the last activity time for a user."""
    user.last_activity_at = utcnow()
    await session.flush()
    return user
