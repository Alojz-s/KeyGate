from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_security_settings, require_permission
from app.core.database import get_db
from app.core.permissions import SETTINGS_MANAGE, USERS_MANAGE
from app.models import User
from app.schemas.admin import SecuritySettingsResponse, UserListItem

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", dependencies=[require_permission(USERS_MANAGE)])
def list_users(db: Annotated[Session, Depends(get_db)]) -> list[UserListItem]:
    users = db.scalars(select(User).where(User.deleted_at.is_(None)).order_by(User.login))
    return [
        UserListItem(id=u.id, login=u.login, role=u.role.name, is_blocked=u.is_blocked)
        for u in users
    ]


@router.get("/settings/security", dependencies=[require_permission(SETTINGS_MANAGE)])
def security_settings(db: Annotated[Session, Depends(get_db)]) -> SecuritySettingsResponse:
    settings = get_security_settings(db)
    return SecuritySettingsResponse(
        min_password_length=settings.min_password_length,
        date_rule_enabled=settings.date_rule_enabled,
        password_validity_days=settings.password_validity_days,
        idle_timeout_minutes=settings.idle_timeout_minutes,
    )
