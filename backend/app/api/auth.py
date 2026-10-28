import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    SESSION_COOKIE,
    ApiError,
    CurrentUser,
    get_security_settings,
    password_change_required,
    reject_restricted_session,
)
from app.core.database import get_db
from app.models import PasswordHistory, User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MeResponse,
    PasswordPolicyErrorResponse,
    PasswordPolicyResponse,
    PolicyViolation,
)
from app.services.password_policy import MAX_PASSWORD_LENGTH, describe_policy, validate_password
from app.services.passwords import hash_password, verify_password
from app.services.sessions import create_session, delete_session

LOGIN_FAILED = "Login lub hasło niepoprawne"

# Weryfikowany, gdy konto nie istnieje lub nie ma hasła - czas odpowiedzi nie zdradza loginu.
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))

router = APIRouter(prefix="/auth", tags=["auth"])


def _me(db: Session, user: User) -> MeResponse:
    settings = get_security_settings(db)
    return MeResponse(
        id=user.id,
        login=user.login,
        role=user.role.name,
        permissions=sorted(p.name for p in user.role.permissions),
        must_change_password=password_change_required(user, settings),
        idle_timeout_minutes=settings.idle_timeout_minutes,
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

    if password_change_required(user, get_security_settings(db)):
        user.must_change_password = True
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


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={422: {"model": PasswordPolicyErrorResponse}},
)
def change_password(
    body: ChangePasswordRequest, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> Response:
    if body.new_password != body.new_password_confirm:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, "Powtórzone hasło nie jest identyczne", "password_mismatch"
        )
    if user.password_hash is None or not verify_password(body.old_password, user.password_hash):
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, "Obecne hasło jest niepoprawne", "invalid_old_password"
        )
    violations = validate_password(
        body.new_password, db=db, settings=get_security_settings(db), user_id=user.id
    )
    if violations:
        error = PasswordPolicyErrorResponse(
            detail="Nowe hasło nie spełnia polityki haseł",
            violations=[PolicyViolation(code=v.code, message=v.message) for v in violations],
        )
        return JSONResponse(error.model_dump(), status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)

    db.add(PasswordHistory(user_id=user.id, password_hash=user.password_hash))
    user.password_hash = hash_password(body.new_password)
    user.password_changed_at = datetime.now(UTC)
    user.must_change_password = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/password-policy", dependencies=[Depends(reject_restricted_session)])
def password_policy(db: Annotated[Session, Depends(get_db)]) -> PasswordPolicyResponse:
    settings = get_security_settings(db)
    return PasswordPolicyResponse(
        min_password_length=settings.min_password_length,
        max_password_length=MAX_PASSWORD_LENGTH,
        date_rule_enabled=settings.date_rule_enabled,
        requirements=describe_policy(settings),
    )
