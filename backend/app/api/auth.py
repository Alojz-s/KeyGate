import secrets
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, CurrentUser, get_security_settings
from app.core.database import get_db
from app.models import User
from app.schemas.auth import LoginRequest, MeResponse, PasswordPolicyResponse
from app.services.password_policy import MAX_PASSWORD_LENGTH, describe_policy
from app.services.passwords import hash_password, verify_password
from app.services.sessions import create_session, delete_session

LOGIN_FAILED = "Login lub hasło niepoprawne"

# Weryfikowany, gdy konto nie istnieje lub nie ma hasła - czas odpowiedzi nie zdradza loginu.
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))

router = APIRouter(prefix="/auth", tags=["auth"])


def _me(db: Session, user: User) -> MeResponse:
    return MeResponse(
        id=user.id,
        login=user.login,
        role=user.role.name,
        permissions=sorted(p.name for p in user.role.permissions),
        must_change_password=user.must_change_password,
        idle_timeout_minutes=get_security_settings(db).idle_timeout_minutes,
    )


@router.post("/login")
def login(
    body: LoginRequest, response: Response, db: Annotated[Session, Depends(get_db)]
) -> MeResponse:
    user = db.scalar(select(User).where(User.login == body.login))
    password_hash = user.password_hash if user and user.password_hash else _DUMMY_PASSWORD_HASH
    password_ok = verify_password(body.password, password_hash)
    if user is None or not password_ok or user.is_blocked or user.deleted_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, LOGIN_FAILED)

    token = create_session(db, user.id)
    db.commit()
    response.set_cookie(SESSION_COOKIE, token, path="/", httponly=True, samesite="strict")
    return _me(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    if token:
        delete_session(db, token)
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")


@router.get("/me")
def me(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> MeResponse:
    return _me(db, user)


@router.get("/password-policy")
def password_policy(db: Annotated[Session, Depends(get_db)]) -> PasswordPolicyResponse:
    settings = get_security_settings(db)
    return PasswordPolicyResponse(
        min_password_length=settings.min_password_length,
        max_password_length=MAX_PASSWORD_LENGTH,
        date_rule_enabled=settings.date_rule_enabled,
        requirements=describe_policy(settings),
    )
