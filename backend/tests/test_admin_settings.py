from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, get_security_settings
from app.core.database import get_db
from app.main import app
from app.services.password_policy import validate_password
from app.services.sessions import create_session, find_session
from scripts.seed import seed
from tests.test_admin_users import _sign_in_as, _user
from tests.test_auth import ADMIN_PASSWORD, PASSWORD

pytestmark = pytest.mark.db

DEFAULTS = {
    "min_password_length": 15,
    "date_rule_enabled": False,
    "password_validity_days": 0,
    "idle_timeout_minutes": 15,
}


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    seed(db_session, ADMIN_PASSWORD, PASSWORD)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(client: TestClient, db_session: Session) -> TestClient:
    _sign_in_as(client, db_session, "Administrator")
    return client


def _put(client: TestClient, **changes: object) -> dict:
    response = client.put("/api/admin/settings", json=DEFAULTS | changes)
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize("role", ["Audytor", "Redaktor", "Czytelnik"])
@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_settings_are_forbidden_without_permission(
    client: TestClient, db_session: Session, role: str, method: str
) -> None:
    _sign_in_as(client, db_session, role)

    response = client.request(
        method, "/api/admin/settings", json=DEFAULTS | {"idle_timeout_minutes": 5}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert get_security_settings(db_session).idle_timeout_minutes == 15


def test_raised_min_length_applies_to_next_password_change(admin_client: TestClient) -> None:
    assert _put(admin_client, min_password_length=16)["min_password_length"] == 16
    assert admin_client.get("/api/admin/settings").json()["min_password_length"] == 16

    admin_client.post("/api/auth/login", json={"login": "redaktor", "password": PASSWORD})
    response = admin_client.post(
        "/api/auth/change-password",
        json={
            "old_password": PASSWORD,
            "new_password": "kot-pies-chomik",
            "new_password_confirm": "kot-pies-chomik",
        },
    )

    assert response.status_code == 422
    assert [v["code"] for v in response.json()["violations"]] == ["too_short"]


@pytest.mark.parametrize(("enabled", "expected"), [(True, {"contains_year"}), (False, set())])
def test_date_rule_toggle(
    admin_client: TestClient, db_session: Session, enabled: bool, expected: set[str]
) -> None:
    _put(admin_client, date_rule_enabled=enabled)

    settings = get_security_settings(db_session)
    violations = validate_password("WiosennySpacer2024", db=db_session, settings=settings)

    assert {v.code for v in violations} == expected


def test_lowered_idle_timeout_expires_open_session(
    admin_client: TestClient, db_session: Session
) -> None:
    token = create_session(db_session, _user(db_session, "redaktor").id)
    db_session.flush()
    find_session(db_session, token).last_activity_at = datetime.now(UTC) - timedelta(minutes=2)
    db_session.flush()

    _put(admin_client, idle_timeout_minutes=1)
    admin_client.cookies.set(SESSION_COOKIE, token)
    response = admin_client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "session_expired"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("min_password_length", 14, "invalid_min_password_length"),
        ("min_password_length", 65, "invalid_min_password_length"),
        ("password_validity_days", -1, "invalid_password_validity_days"),
        ("idle_timeout_minutes", 0, "invalid_idle_timeout"),
        ("idle_timeout_minutes", 121, "invalid_idle_timeout"),
    ],
)
def test_invalid_settings_are_rejected(
    admin_client: TestClient, db_session: Session, field: str, value: int, code: str
) -> None:
    response = admin_client.put("/api/admin/settings", json=DEFAULTS | {field: value})

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Nieprawidłowe dane w żądaniu"
    assert [v["code"] for v in body["violations"]] == [code]
    assert getattr(get_security_settings(db_session), field) == DEFAULTS[field]
