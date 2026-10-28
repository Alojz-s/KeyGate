from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import SECURITY_SETTINGS_ID, SecuritySettings, User
from app.services.sessions import find_session, is_idle_expired

SESSION_COOKIE = "keygate_session"


class ApiError(Exception):
    """Błąd API z polem `code` w odpowiedzi: {"detail": ..., "code": ...}."""

    def __init__(self, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code


def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail, "code": exc.code}
    )


def get_security_settings(db: Session) -> SecuritySettings:
    settings = db.get(SecuritySettings, SECURITY_SETTINGS_ID)
    if settings is None:
        raise RuntimeError("Brak ustawień bezpieczeństwa w bazie (uruchom: python scripts/seed.py)")
    return settings


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    not_authenticated = ApiError(
        status.HTTP_401_UNAUTHORIZED, "Wymagane zalogowanie", "not_authenticated"
    )
    session = find_session(db, token) if token else None
    if session is None:
        raise not_authenticated

    now = datetime.now(UTC)
    if is_idle_expired(session, get_security_settings(db).idle_timeout_minutes, now):
        db.delete(session)
        db.commit()
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED,
            "Sesja wygasła z powodu bezczynności",
            "session_expired",
        )

    user = db.get(User, session.user_id)
    if user is None or user.is_blocked or user.deleted_at is not None:
        raise not_authenticated

    session.last_activity_at = now
    db.commit()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
