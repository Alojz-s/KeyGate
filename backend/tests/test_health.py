from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.database import get_db
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_ok(client: TestClient) -> None:
    app.dependency_overrides[get_db] = lambda: MagicMock()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_database_error(client: TestClient) -> None:
    db = MagicMock()
    db.execute.side_effect = OperationalError("SELECT 1", {}, Exception("connection refused"))
    app.dependency_overrides[get_db] = lambda: db

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {"status": "ok", "database": "error"}


@pytest.mark.db
def test_health_real_database(client: TestClient) -> None:
    response = client.get("/api/health")

    if response.json()["database"] != "ok":
        pytest.skip("Baza PostgreSQL niedostępna (uruchom: docker compose up -d)")
    assert response.status_code == 200
