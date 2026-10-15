from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_db
from app.db.sessions import user_for_token

SESSION_COOKIE = "session"


async def current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User | None:
    """Resolve the caller from the session cookie."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    user = await user_for_token(db, token)
    return user


async def require_user(user: User | None = Depends(current_user)) -> User:
    """Authentication: reject a missing caller."""
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthenticated", "message": "Sign in first."},
        )
    return user


async def allow_signed_in(user: User = Depends(require_user)) -> User:
    """Authorization: any signed-in user may use this route."""
    return user
