import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SESSION_COOKIE, require_user
from app.db.models import User
from app.db.session import get_db
from app.db.sessions import close_session, open_session
from app.db.users import by_email, insert_user, touch
from app.schemas import AuthIn, UserOut
from app.shared.config import get_settings
from app.shared.passwords import hash_password, verify_password

router = APIRouter(prefix="/api")
log = logging.getLogger(__name__)


def _email(value: str) -> str:
    text = value.strip().lower()
    if "@" not in text or text.startswith("@") or text.endswith("@"):
        raise HTTPException(status_code=400, detail={"code": "invalid_email", "message": "Enter a valid email."})
    return text


def _password(value: str) -> str:
    if not value:
        raise HTTPException(status_code=400, detail={"code": "invalid_password", "message": "Enter a password."})
    return value


def _write_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_sec,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )


def _clear_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )


async def _start(response: Response, db: AsyncSession, user: User) -> UserOut:
    await touch(db, user)
    token = await open_session(db, user)
    await db.commit()
    _write_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/register", response_model=UserOut)
async def register(body: AuthIn, response: Response, db: AsyncSession = Depends(get_db)) -> UserOut:
    email = _email(body.email)
    password = _password(body.password)
    if await by_email(db, email) is not None:
        raise HTTPException(status_code=409, detail={"code": "email_taken", "message": "That email is already registered."})
    user = await insert_user(db, email, hash_password(password))
    try:
        created = await _start(response, db, user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail={"code": "email_taken", "message": "That email is already registered."})
    log.info("user %s registered", user.id)
    return created


@router.post("/login", response_model=UserOut)
async def login(body: AuthIn, response: Response, db: AsyncSession = Depends(get_db)) -> UserOut:
    email = _email(body.email)
    password = _password(body.password)
    user = await by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        log.info("login rejected")
        raise HTTPException(status_code=401, detail={"code": "invalid_login", "message": "Invalid email or password."})
    logged = await _start(response, db, user)
    log.info("user %s logged in", user.id)
    return logged


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(require_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await close_session(db, token)
        await db.commit()
    _clear_cookie(response)
