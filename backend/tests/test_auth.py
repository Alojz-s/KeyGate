from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE
from app.core.database import get_db
from app.main import app
from app.models import SECURITY_SETTINGS_ID, PasswordHistory, SecuritySettings, User, UserSession
from scripts.seed import seed

pytestmark = pytest.mark.db

PASSWORD = "haslo-uzytkownikow-testowych"
ADMIN_PASSWORD = "haslo-startowe-admina-testy"
NEW_PASSWORD = "zupelnie-nowe-haslo-po-zmianie"
LOGIN_FAILED = {"detail": "Login lub hasło niepoprawne"}


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    seed(db_session, ADMIN_PASSWORD, PASSWORD)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _login(client: TestClient, login: str = "redaktor", password: str = PASSWORD) -> str:
    response = client.post("/api/auth/login", json={"login": login, "password": password})
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


def test_forced_password_change_restricts_session(client: TestClient, db_session: Session) -> None:
    _login(client, "ADMIN", ADMIN_PASSWORD)
    admin = db_session.scalars(select(User).where(User.login == "ADMIN")).one()
    old_hash = admin.password_hash

    assert client.get("/api/auth/me").json()["must_change_password"] is True
    response = client.get("/api/auth/password-policy")
    assert response.status_code == 403
    assert response.json()["code"] == "password_change_required"

    response = client.post(
        "/api/auth/change-password",
        json={
            "old_password": ADMIN_PASSWORD,
            "new_password": NEW_PASSWORD,
            "new_password_confirm": NEW_PASSWORD,
        },
    )

    assert response.status_code == 204
    assert client.get("/api/auth/me").json()["must_change_password"] is False
    assert client.get("/api/auth/password-policy").status_code == 200
    history = db_session.scalars(
        select(PasswordHistory.password_hash).where(PasswordHistory.user_id == admin.id)
    ).all()
    assert history == [old_hash]
    response = client.post("/api/auth/login", json={"login": "ADMIN", "password": ADMIN_PASSWORD})
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("old_password", "new_password", "confirm", "status", "detail", "violations"),
    [
        ("zle-stare-haslo", NEW_PASSWORD, NEW_PASSWORD, 400, "Obecne hasło jest niepoprawne", []),
        (PASSWORD, NEW_PASSWORD, "inne", 400, "Powtórzone hasło nie jest identyczne", []),
        (
            PASSWORD,
            "za-krotkie",
            "za-krotkie",
            422,
            "Nowe hasło nie spełnia polityki haseł",
            ["too_short"],
        ),
    ],
    ids=["wrong-old-password", "mismatch", "policy"],
)
def test_change_password_errors(
    client: TestClient,
    old_password: str,
    new_password: str,
    confirm: str,
    status: int,
    detail: str,
    violations: list[str],
) -> None:
    _login(client)

    response = client.post(
        "/api/auth/change-password",
        json={
            "old_password": old_password,
            "new_password": new_password,
            "new_password_confirm": confirm,
        },
    )

    assert response.status_code == status
    assert response.json()["detail"] == detail
    assert [v["code"] for v in response.json().get("violations", [])] == violations


def test_login_with_expired_password_requires_change(
    client: TestClient, db_session: Session
) -> None:
    db_session.get(SecuritySettings, SECURITY_SETTINGS_ID).password_validity_days = 30
    redaktor = db_session.scalars(select(User).where(User.login == "redaktor")).one()
    redaktor.password_changed_at = datetime.now(UTC) - timedelta(days=31)
    db_session.flush()

    _login(client)

    assert redaktor.must_change_password is True
    assert client.get("/api/auth/me").json()["must_change_password"] is True
    assert client.get("/api/auth/password-policy").status_code == 403
