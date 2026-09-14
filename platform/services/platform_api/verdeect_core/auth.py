import secrets
import time
from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session
from verdeect_common.security import digest
from .models import User, WebSession, LoginTicket

COOKIE_NAME = "verdeect_platform_session"
COOKIE_PATH = "/_platform/api"
SESSION_TTL = 2 * 60 * 60


def get_session(request: Request, db: Session) -> tuple[WebSession, User]:
    raw = request.cookies.get(COOKIE_NAME, "")
    if len(raw) < 32:
        raise HTTPException(401, "Требуется вход в платформу")
    session = db.get(WebSession, digest(raw))
    if not session or session.expires_at <= int(time.time()):
        raise HTTPException(401, "Сессия истекла")
    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, "Учётная запись отключена")
    return session, user


def require_origin(request: Request, origin: str):
    if request.headers.get("origin") != origin:
        raise HTTPException(403, "Недопустимый Origin")


def require_csrf(request: Request, session: WebSession, origin: str):
    require_origin(request, origin)
    supplied = request.headers.get("x-csrf-token", "")
    if not supplied or not secrets.compare_digest(supplied, session.csrf):
        raise HTTPException(403, "Проверка CSRF не пройдена")


def create_session(db: Session, user_id: str, response: Response, secure: bool, previous: str | None = None):
    if previous:
        old = db.get(WebSession, digest(previous))
        if old:
            db.delete(old)
    token = secrets.token_urlsafe(32)
    session = WebSession(token_hash=digest(token), user_id=user_id,
        csrf=secrets.token_urlsafe(32), expires_at=int(time.time()) + SESSION_TTL)
    db.add(session)
    db.commit()
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_TTL, httponly=True,
        secure=secure, samesite="lax", path=COOKIE_PATH)
    return session


def mint_dev_ticket(db: Session, user_id: str) -> str:
    if not db.get(User, user_id):
        raise ValueError("User does not exist")
    token = secrets.token_urlsafe(32)
    db.add(LoginTicket(token_hash=digest(token), user_id=user_id,
        expires_at=int(time.time()) + 600, used=False))
    db.commit()
    return token
