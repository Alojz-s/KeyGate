from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ApiError, get_security_settings, require_permission
from app.core.database import get_db
from app.core.permissions import SETTINGS_MANAGE, USERS_MANAGE
from app.models import ADMIN_LOGIN, Role, User
from app.schemas.admin import (
    CreatedUserResponse,
    OneTimePasswordResponse,
    RoleItem,
    SecuritySettingsResponse,
    UserCreate,
    UserListItem,
    UserUpdate,
)
from app.services.one_time_passwords import (
    issue_one_time_password,
    reset_account_with_one_time_password,
)
from app.services.sessions import delete_all_sessions_for_user

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_MODIFY = "Nie można modyfikować konta ADMIN"
ADMIN_BLOCK = "Nie można zablokować konta ADMIN"
ADMIN_DELETE = "Nie można usunąć konta ADMIN"


def _user_item(user: User) -> UserListItem:
    return UserListItem(
        id=user.id,
        login=user.login,
        role_id=user.role_id,
        role=user.role.name,
        is_blocked=user.is_blocked,
    )


def _get_role(db: Session, role_id: int) -> Role:
    role = db.get(Role, role_id)
    if role is None:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Nieznana rola", "invalid_role")
    return role


def _get_managed_user(db: Session, user_id: int, admin_message: str) -> User:
    """Zwraca nieusuniętego użytkownika innego niż ADMIN."""
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Nie znaleziono użytkownika", "user_not_found")
    if user.login == ADMIN_LOGIN:
        raise ApiError(status.HTTP_409_CONFLICT, admin_message, "admin_account_protected")
    return user


@router.get("/roles", dependencies=[require_permission(USERS_MANAGE)])
def list_roles(db: Annotated[Session, Depends(get_db)]) -> list[RoleItem]:
    return [RoleItem(id=r.id, name=r.name) for r in db.scalars(select(Role).order_by(Role.id))]


@router.get("/users", dependencies=[require_permission(USERS_MANAGE)])
def list_users(db: Annotated[Session, Depends(get_db)]) -> list[UserListItem]:
    users = db.scalars(select(User).where(User.deleted_at.is_(None)).order_by(User.login))
    return [_user_item(u) for u in users]


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission(USERS_MANAGE)],
)
def create_user(body: UserCreate, db: Annotated[Session, Depends(get_db)]) -> CreatedUserResponse:
    role = _get_role(db, body.role_id)
    # Sprawdzenie obejmuje konta usunięte miękko - ich login pozostaje zajęty.
    if db.scalar(select(User.id).where(User.login == body.login)) is not None:
        raise ApiError(status.HTTP_409_CONFLICT, "Login jest już zajęty", "login_taken")
    user = User(login=body.login, role=role, is_blocked=False, must_change_password=True)
    db.add(user)
    db.flush()
    one_time_password = issue_one_time_password(db, user.id)
    db.commit()
    return CreatedUserResponse(**_user_item(user).model_dump(), one_time_password=one_time_password)


@router.patch("/users/{user_id}", dependencies=[require_permission(USERS_MANAGE)])
def update_user(
    user_id: int, body: UserUpdate, db: Annotated[Session, Depends(get_db)]
) -> UserListItem:
    user = _get_managed_user(db, user_id, ADMIN_MODIFY)
    user.role = _get_role(db, body.role_id)
    db.commit()
    return _user_item(user)


@router.post("/users/{user_id}/block", dependencies=[require_permission(USERS_MANAGE)])
def block_user(user_id: int, db: Annotated[Session, Depends(get_db)]) -> UserListItem:
    user = _get_managed_user(db, user_id, ADMIN_BLOCK)
    user.is_blocked = True
    delete_all_sessions_for_user(db, user.id)
    db.commit()
    return _user_item(user)


@router.post("/users/{user_id}/unblock", dependencies=[require_permission(USERS_MANAGE)])
def unblock_user(user_id: int, db: Annotated[Session, Depends(get_db)]) -> UserListItem:
    user = _get_managed_user(db, user_id, ADMIN_MODIFY)
    user.is_blocked = False
    db.commit()
    return _user_item(user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_permission(USERS_MANAGE)],
)
def delete_user(user_id: int, db: Annotated[Session, Depends(get_db)]) -> None:
    user = _get_managed_user(db, user_id, ADMIN_DELETE)
    user.deleted_at = datetime.now(UTC)
    delete_all_sessions_for_user(db, user.id)
    db.commit()


@router.post("/users/{user_id}/reset-password", dependencies=[require_permission(USERS_MANAGE)])
def reset_password(
    user_id: int, db: Annotated[Session, Depends(get_db)]
) -> OneTimePasswordResponse:
    user = _get_managed_user(db, user_id, ADMIN_MODIFY)
    one_time_password = reset_account_with_one_time_password(db, user)
    db.commit()
    return OneTimePasswordResponse(one_time_password=one_time_password)


@router.get("/settings/security", dependencies=[require_permission(SETTINGS_MANAGE)])
def security_settings(db: Annotated[Session, Depends(get_db)]) -> SecuritySettingsResponse:
    settings = get_security_settings(db)
    return SecuritySettingsResponse(
        min_password_length=settings.min_password_length,
        date_rule_enabled=settings.date_rule_enabled,
        password_validity_days=settings.password_validity_days,
        idle_timeout_minutes=settings.idle_timeout_minutes,
    )
