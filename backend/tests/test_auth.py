from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE
from app.core.database import get_db
from app.main import app
from app.models import User, UserSession
from scripts.seed import seed

pytestmark = pytest.mark.db

PASSWORD = "haslo-uzytkownikow-testowych"
LOGIN_FAILED = {"detail": "Login lub hasło niepoprawne"}


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    seed(db_session, "haslo-startowe-admina-testy", PASSWORD)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _login(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"login": "redaktor", "password": PASSWORD})
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    return response.cookies[SESSION_COOKIE]


def test_login_sets_session_cookie_and_me_returns_user(
    client: TestClient, db_session: Session
) -> None:
    token = _login(client)

    assert db_session.scalars(select(UserSession.token_hash)).one() != token

    response = client.get("/api/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["login"] == "redaktor"
    assert body["role"] == "Redaktor"
    assert body["permissions"] == ["articles.read", "articles.write"]
    assert body["must_change_password"] is False
    assert body["idle_timeout_minutes"] == 15


@pytest.mark.parametrize(
    ("login", "password", "blocked"),
    [
        ("nieistniejacy", PASSWORD, False),
        ("redaktor", "zle-haslo-ale-wystarczajaco-dlugie", False),
        ("redaktor", PASSWORD, True),
    ],
    ids=["unknown-login", "wrong-password", "blocked"],
)
def test_login_failure_has_uniform_response(
    client: TestClient, db_session: Session, login: str, password: str, blocked: bool
) -> None:
    db_session.scalars(select(User).where(User.login == "redaktor")).one().is_blocked = blocked
    db_session.flush()

    response = client.post("/api/auth/login", json={"login": login, "password": password})

    assert response.status_code == 401
    assert response.json() == LOGIN_FAILED
    assert SESSION_COOKIE not in response.cookies


def test_idle_session_expires(client: TestClient, db_session: Session) -> None:
    _login(client)
    session = db_session.scalars(select(UserSession)).one()
    session.last_activity_at = datetime.now(UTC) - timedelta(minutes=15, seconds=1)
    db_session.flush()

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "session_expired"


def test_logout_invalidates_session(client: TestClient) -> None:
    token = _login(client)

    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.set(SESSION_COOKIE, token)
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"
