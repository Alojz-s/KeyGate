from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE
from app.core.database import get_db
from app.main import app
from app.models import ADMIN_LOGIN, Role, User, UserSession
from app.services.sessions import create_session
from scripts.seed import seed
from tests.test_auth import ADMIN_PASSWORD, LOGIN_FAILED, PASSWORD
from tests.test_one_time_passwords import ONE_TIME_PASSWORD_PATTERN

pytestmark = pytest.mark.db

USER_ENDPOINTS = [
    ("GET", "/api/admin/roles", None),
    ("GET", "/api/admin/users", None),
    ("POST", "/api/admin/users", {"login": "nowy", "role_id": 1}),
    ("PATCH", "/api/admin/users/{id}", {"role_id": 1}),
    ("POST", "/api/admin/users/{id}/block", None),
    ("POST", "/api/admin/users/{id}/unblock", None),
    ("DELETE", "/api/admin/users/{id}", None),
    ("POST", "/api/admin/users/{id}/reset-password", None),
]


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    seed(db_session, ADMIN_PASSWORD, PASSWORD)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _role(db_session: Session, name: str) -> Role:
    return db_session.scalars(select(Role).filter_by(name=name)).one()


def _user(db_session: Session, login: str) -> User:
    return db_session.scalars(select(User).filter_by(login=login)).one()


def _sign_in_as(client: TestClient, db_session: Session, role: str) -> None:
    user = User(login=f"test-{role}", role=_role(db_session, role))
    db_session.add(user)
    db_session.flush()
    client.cookies.set(SESSION_COOKIE, create_session(db_session, user.id))
    db_session.flush()


def _session_count(db_session: Session, user_id: int) -> int:
    return db_session.scalar(
        select(func.count()).select_from(UserSession).where(UserSession.user_id == user_id)
    )


@pytest.fixture
def admin_client(client: TestClient, db_session: Session) -> TestClient:
    _sign_in_as(client, db_session, "Administrator")
    return client


@pytest.mark.parametrize("role", ["Audytor", "Redaktor", "Czytelnik"])
@pytest.mark.parametrize(("method", "path", "body"), USER_ENDPOINTS)
def test_user_management_is_forbidden_without_permission(
    client: TestClient, db_session: Session, role: str, method: str, path: str, body: dict | None
) -> None:
    _sign_in_as(client, db_session, role)
    target = _user(db_session, "czytelnik")

    response = client.request(method, path.format(id=target.id), json=body)

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert target.is_blocked is False
    assert target.deleted_at is None


@pytest.mark.parametrize(
    ("method", "suffix", "detail"),
    [
        ("PATCH", "", "Nie można modyfikować konta ADMIN"),
        ("POST", "/block", "Nie można zablokować konta ADMIN"),
        ("POST", "/unblock", "Nie można modyfikować konta ADMIN"),
        ("DELETE", "", "Nie można usunąć konta ADMIN"),
        ("POST", "/reset-password", "Nie można modyfikować konta ADMIN"),
    ],
)
def test_admin_account_is_protected(
    admin_client: TestClient, db_session: Session, method: str, suffix: str, detail: str
) -> None:
    admin = _user(db_session, ADMIN_LOGIN)
    body = {"role_id": _role(db_session, "Czytelnik").id} if method == "PATCH" else None

    response = admin_client.request(method, f"/api/admin/users/{admin.id}{suffix}", json=body)

    assert response.status_code == 409
    assert response.json() == {"detail": detail, "code": "admin_account_protected"}
    db_session.refresh(admin)
    assert admin.role.name == "Administrator"
    assert admin.is_blocked is False
    assert admin.deleted_at is None
    assert admin.password_hash is not None


def test_created_user_logs_in_with_one_time_password(
    admin_client: TestClient, db_session: Session
) -> None:
    role_id = _role(db_session, "Redaktor").id

    response = admin_client.post("/api/admin/users", json={"login": "nowak", "role_id": role_id})

    assert response.status_code == 201
    body = response.json()
    assert body["login"] == "nowak"
    assert body["role"] == "Redaktor"
    assert ONE_TIME_PASSWORD_PATTERN.fullmatch(body["one_time_password"])
    user = _user(db_session, "nowak")
    assert user.password_hash is None
    assert user.must_change_password is True

    response = admin_client.post(
        "/api/auth/login", json={"login": "nowak", "password": body["one_time_password"]}
    )
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


def test_update_changes_role(admin_client: TestClient, db_session: Session) -> None:
    target = _user(db_session, "czytelnik")
    role_id = _role(db_session, "Redaktor").id

    response = admin_client.patch(f"/api/admin/users/{target.id}", json={"role_id": role_id})

    assert response.status_code == 200
    assert response.json()["role"] == "Redaktor"
    response = admin_client.patch(f"/api/admin/users/{target.id}", json={"role_id": 999999})
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_role"


def test_block_closes_sessions_and_rejects_login(
    admin_client: TestClient, db_session: Session
) -> None:
    target = _user(db_session, "redaktor")
    create_session(db_session, target.id)
    db_session.flush()

    response = admin_client.post(f"/api/admin/users/{target.id}/block")

    assert response.status_code == 200
    assert response.json()["is_blocked"] is True
    assert _session_count(db_session, target.id) == 0
    response = admin_client.post(
        "/api/auth/login", json={"login": "redaktor", "password": PASSWORD}
    )
    assert response.status_code == 401
    assert response.json() == LOGIN_FAILED

    assert admin_client.post(f"/api/admin/users/{target.id}/unblock").status_code == 200
    response = admin_client.post(
        "/api/auth/login", json={"login": "redaktor", "password": PASSWORD}
    )
    assert response.status_code == 200


def test_delete_hides_user_and_keeps_login_taken(
    admin_client: TestClient, db_session: Session
) -> None:
    target = _user(db_session, "czytelnik")
    create_session(db_session, target.id)
    db_session.flush()

    response = admin_client.delete(f"/api/admin/users/{target.id}")

    assert response.status_code == 204
    assert _session_count(db_session, target.id) == 0
    logins = [u["login"] for u in admin_client.get("/api/admin/users").json()]
    assert "czytelnik" not in logins
    assert admin_client.delete(f"/api/admin/users/{target.id}").status_code == 404
    response = admin_client.post(
        "/api/admin/users", json={"login": "czytelnik", "role_id": target.role_id}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "login_taken"


def test_reset_invalidates_password_and_closes_sessions(
    admin_client: TestClient, db_session: Session
) -> None:
    target = _user(db_session, "redaktor")
    create_session(db_session, target.id)
    db_session.flush()

    response = admin_client.post(f"/api/admin/users/{target.id}/reset-password")

    assert response.status_code == 200
    assert ONE_TIME_PASSWORD_PATTERN.fullmatch(response.json()["one_time_password"])
    assert _session_count(db_session, target.id) == 0
    response = admin_client.post(
        "/api/auth/login", json={"login": "redaktor", "password": PASSWORD}
    )
    assert response.status_code == 401
    assert response.json() == LOGIN_FAILED
