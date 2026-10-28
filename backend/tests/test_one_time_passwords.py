import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app
from app.models import OneTimePassword, User
from app.services.one_time_passwords import (
    generate_plaintext,
    reset_account_with_one_time_password,
)
from scripts.seed import seed
from tests.test_auth import ADMIN_PASSWORD, LOGIN_FAILED, NEW_PASSWORD, PASSWORD

ONE_TIME_PASSWORD_PATTERN = re.compile(r"[A-HJ-NP-Za-hj-km-np-z2-9]{12}")


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    seed(db_session, ADMIN_PASSWORD, PASSWORD)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _reset_redaktor(db_session: Session) -> str:
    redaktor = db_session.scalars(select(User).where(User.login == "redaktor")).one()
    plain = reset_account_with_one_time_password(db_session, redaktor)
    db_session.commit()
    return plain


def _login(client: TestClient, password: str) -> int:
    response = client.post("/api/auth/login", json={"login": "redaktor", "password": password})
    return response.status_code


def test_generated_password_has_12_chars_from_alphabet() -> None:
    for _ in range(500):
        assert ONE_TIME_PASSWORD_PATTERN.fullmatch(generate_plaintext())


@pytest.mark.db
def test_expired_one_time_password_is_rejected(client: TestClient, db_session: Session) -> None:
    plain = _reset_redaktor(db_session)
    otp = db_session.scalars(select(OneTimePassword)).one()
    assert otp.expires_at - datetime.now(UTC) <= timedelta(hours=24)
    otp.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()

    response = client.post("/api/auth/login", json={"login": "redaktor", "password": plain})

    assert response.status_code == 401
    assert response.json() == LOGIN_FAILED


@pytest.mark.db
def test_one_time_password_works_only_once(client: TestClient, db_session: Session) -> None:
    plain = _reset_redaktor(db_session)
    assert _login(client, plain) == 200
    client.post("/api/auth/logout")

    response = client.post("/api/auth/login", json={"login": "redaktor", "password": plain})

    assert response.status_code == 401
    assert response.json() == LOGIN_FAILED


@pytest.mark.db
def test_one_time_password_login_forces_password_change(
    client: TestClient, db_session: Session
) -> None:
    plain = _reset_redaktor(db_session)

    assert _login(client, plain) == 200

    assert client.get("/api/auth/me").json()["must_change_password"] is True
    response = client.get("/api/articles")
    assert response.status_code == 403
    assert response.json()["code"] == "password_change_required"
    response = client.post(
        "/api/auth/change-password",
        json={
            "old_password": plain,
            "new_password": NEW_PASSWORD,
            "new_password_confirm": NEW_PASSWORD,
        },
    )
    assert response.status_code == 204
    assert client.get("/api/articles").status_code == 200


@pytest.mark.db
def test_reset_invalidates_password_and_sessions(client: TestClient, db_session: Session) -> None:
    assert _login(client, PASSWORD) == 200

    _reset_redaktor(db_session)

    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"
    response = client.post("/api/auth/login", json={"login": "redaktor", "password": PASSWORD})
    assert response.status_code == 401
    assert response.json() == LOGIN_FAILED
