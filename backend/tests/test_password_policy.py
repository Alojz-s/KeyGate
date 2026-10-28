from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models import PasswordHistory, Role, SecuritySettings, User
from app.services.password_policy import validate_password
from app.services.passwords import hash_password

pytestmark = pytest.mark.db

# Indeks 0 - hasło bieżące, 1-5 - historia od najnowszego.
OLD_PASSWORDS = [f"stare-haslo-numer-{i}" for i in range(6)]


def _codes(password: str, db: Session, date_rule: bool, user_id: int | None = None) -> set[str]:
    settings = SecuritySettings(min_password_length=15, date_rule_enabled=date_rule)
    violations = validate_password(password, db=db, settings=settings, user_id=user_id)
    return {v.code for v in violations}


@pytest.mark.parametrize(
    ("password", "date_rule", "expected"),
    [
        ("kot-pies-chomik", True, set()),
        ("kot-pies-chomi", True, {"too_short"}),
        ("x" * 64, True, set()),
        ("x" * 65, True, {"too_long"}),
        ("qwertyuiopasdfgh", False, {"common_password"}),
        ("QWERTYuiopASDFGH", False, {"common_password"}),
        ("Filemon2024!", True, {"too_short", "contains_year"}),
        ("kot_1999_lato", True, {"too_short", "contains_year"}),
        ("kot05.01.2024pies", True, {"contains_year"}),
        ("abc119501xyz", True, {"too_short"}),
        ("haslo2031abc", True, {"too_short"}),
        ("15.01.2024", True, {"too_short", "is_date", "contains_year"}),
        ("2024-01-15", True, {"too_short", "is_date", "contains_year"}),
        ("15/01/2024", True, {"too_short", "is_date", "contains_year"}),
        ("15012024", True, {"too_short", "is_date"}),
        ("20240115", True, {"too_short", "is_date"}),
        ("32.13.2024", True, {"too_short", "contains_year"}),
        ("15 stycznia 2024", True, {"is_date", "contains_year"}),
        ("15 styczeń 2024", True, {"is_date", "contains_year"}),
        ("3 października 1999", True, {"is_date", "contains_year"}),
        ("Filemon2024!", False, {"too_short"}),
        ("kot05.01.2024pies", False, set()),
        ("15 stycznia 2024", False, set()),
    ],
)
def test_validate_password(
    db_session: Session, password: str, date_rule: bool, expected: set[str]
) -> None:
    assert _codes(password, db_session, date_rule) == expected


@pytest.fixture(scope="module")
def old_password_hashes() -> list[str]:
    return [hash_password(p) for p in OLD_PASSWORDS]


@pytest.mark.parametrize(
    ("index", "reused"), [(0, True), (1, True), (4, True), (5, False)], ids=str
)
def test_reused_password(
    db_session: Session, old_password_hashes: list[str], index: int, reused: bool
) -> None:
    current, *history = old_password_hashes
    user = User(login="historia", password_hash=current, role=Role(name="Testowa"))
    db_session.add(user)
    db_session.flush()
    now = datetime.now(UTC)
    db_session.add_all(
        PasswordHistory(user_id=user.id, password_hash=h, created_at=now - timedelta(days=i))
        for i, h in enumerate(history, start=1)
    )
    db_session.flush()

    codes = _codes(OLD_PASSWORDS[index], db_session, date_rule=False, user_id=user.id)

    assert ("reused_password" in codes) is reused
