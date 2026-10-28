import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import ROOT_DIR, get_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_NAME = "keygate_test"

if not (ROOT_DIR / ".env").exists():
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+psycopg://keygate:keygate@localhost:5432/keygate"
    )

# Musi się wykonać przed importem app.core.database: aplikacja, Alembic i fixture'y
# łączą się wyłącznie z bazą testową, nigdy z deweloperską.
TEST_DATABASE_URL = make_url(get_settings().database_url).set(database=TEST_DATABASE_NAME)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL.render_as_string(hide_password=False)
get_settings.cache_clear()


def _create_test_database_if_missing() -> None:
    server_engine = create_engine(
        TEST_DATABASE_URL.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": get_settings().database_connect_timeout},
    )
    try:
        with server_engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": TEST_DATABASE_NAME},
            )
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))
    finally:
        server_engine.dispose()


@pytest.fixture(scope="session")
def db_engine() -> Engine:
    try:
        _create_test_database_if_missing()
    except OperationalError:
        pytest.skip("Baza PostgreSQL niedostępna (uruchom: docker compose up -d)")

    alembic_config = Config()
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(alembic_config, "head")

    from app.core.database import engine

    return engine


@pytest.fixture(autouse=True)
def _prepare_database_for_db_tests(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("db"):
        request.getfixturevalue("db_engine")


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    with db_engine.connect() as connection:
        transaction = connection.begin()
        # commit() w testowanym kodzie zamyka tylko savepoint; całość cofa rollback poniżej.
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
