from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import Article, Permission, Role, SecuritySettings, User
from app.services.passwords import verify_password
from scripts.seed import ADMIN_LOGIN, ROLE_PERMISSIONS, seed

pytestmark = pytest.mark.db

ADMIN_PASSWORD = "haslo-startowe-admina-testy"
USER_PASSWORD = "haslo-uzytkownikow-testowych"


def _count(db: Session, model: type[Base]) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def _user(db: Session, login: str) -> User:
    return db.scalars(select(User).where(User.login == login)).one()


def test_seed_is_idempotent(db_session: Session) -> None:
    models = [User, Role, Permission, Article, SecuritySettings]

    seed(db_session, ADMIN_PASSWORD, USER_PASSWORD)
    counts = {model: _count(db_session, model) for model in models}
    seed(db_session, ADMIN_PASSWORD, USER_PASSWORD)

    assert {model: _count(db_session, model) for model in models} == counts
    assert counts == {User: 3, Role: 4, Permission: 4, Article: 3, SecuritySettings: 1}


def test_seed_assigns_permissions_from_matrix(db_session: Session) -> None:
    seed(db_session, ADMIN_PASSWORD, USER_PASSWORD)

    for role in db_session.scalars(select(Role)):
        assert {p.name for p in role.permissions} == set(ROLE_PERMISSIONS[role.name])


def test_seed_users(db_session: Session) -> None:
    seed(db_session, ADMIN_PASSWORD, USER_PASSWORD)

    admin = _user(db_session, ADMIN_LOGIN)
    assert admin.role.name == "Administrator"
    assert admin.must_change_password is True
    assert admin.password_hash is not None
    assert admin.password_hash.startswith("$argon2id$")
    assert verify_password(ADMIN_PASSWORD, admin.password_hash)

    for login, role_name in [("redaktor", "Redaktor"), ("czytelnik", "Czytelnik")]:
        user = _user(db_session, login)
        assert user.role.name == role_name
        assert user.must_change_password is False
        assert user.password_hash is not None
        assert verify_password(USER_PASSWORD, user.password_hash)


def test_seed_does_not_overwrite_existing_password(db_session: Session) -> None:
    seed(db_session, ADMIN_PASSWORD, USER_PASSWORD)
    seed(db_session, "inne-haslo-startowe-admina", USER_PASSWORD)

    admin_hash = _user(db_session, ADMIN_LOGIN).password_hash
    assert admin_hash is not None
    assert verify_password(ADMIN_PASSWORD, admin_hash)


def test_login_stays_taken_after_soft_delete(db_session: Session) -> None:
    seed(db_session, ADMIN_PASSWORD, USER_PASSWORD)
    role = db_session.scalars(select(Role).where(Role.name == "Czytelnik")).one()
    db_session.add(User(login="usuniety", role=role, deleted_at=datetime.now(UTC)))
    db_session.flush()

    db_session.add(User(login="usuniety", role=role))
    with pytest.raises(IntegrityError):
        db_session.flush()
