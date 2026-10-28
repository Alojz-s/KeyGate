"""Idempotentne dane początkowe: role, uprawnienia, ustawienia, użytkownicy i artykuły.

Uruchamianie: cd backend && python scripts/seed.py
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import SecretStr  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import OperationalError, ProgrammingError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.permissions import ROLE_PERMISSION_MATRIX  # noqa: E402
from app.models import (  # noqa: E402
    SECURITY_SETTINGS_ID,
    Article,
    Permission,
    Role,
    SecuritySettings,
    User,
)
from app.services.passwords import hash_password  # noqa: E402

ADMIN_LOGIN = "ADMIN"
MIN_SEED_PASSWORD_LENGTH = 15

TEST_USERS = {
    "redaktor": "Redaktor",
    "czytelnik": "Czytelnik",
}

ARTICLES = [
    (
        "Witamy w portalu KeyGate",
        "KeyGate to wewnętrzny portal firmy. Znajdziesz tu aktualności, procedury "
        "i komunikaty dla pracowników.",
    ),
    (
        "Zasady bezpiecznych haseł",
        "Używaj długich haseł – najlepiej kilku przypadkowych słów. Nie używaj tego samego "
        "hasła w różnych serwisach i nikomu go nie przekazuj.",
    ),
    (
        "Praca zdalna – przypomnienie",
        "Podczas pracy zdalnej blokuj ekran, gdy odchodzisz od komputera, i korzystaj "
        "wyłącznie z firmowego VPN.",
    ),
]


def seed(db: Session, admin_password: str, user_password: str) -> None:
    permissions = _ensure_permissions(db)
    roles = _ensure_roles(db, permissions)
    _ensure_security_settings(db)
    _ensure_user(db, ADMIN_LOGIN, roles["Administrator"], admin_password, must_change=True)
    for login, role_name in TEST_USERS.items():
        _ensure_user(db, login, roles[role_name], user_password, must_change=False)
    _ensure_articles(db)
    db.commit()


def _ensure_permissions(db: Session) -> dict[str, Permission]:
    names = sorted({name for names in ROLE_PERMISSION_MATRIX.values() for name in names})
    existing = {p.name: p for p in db.scalars(select(Permission).where(Permission.name.in_(names)))}
    for name in names:
        if name not in existing:
            existing[name] = Permission(name=name)
            db.add(existing[name])
    return existing


def _ensure_roles(db: Session, permissions: dict[str, Permission]) -> dict[str, Role]:
    existing = {
        r.name: r for r in db.scalars(select(Role).where(Role.name.in_(ROLE_PERMISSION_MATRIX)))
    }
    for name, permission_names in ROLE_PERMISSION_MATRIX.items():
        role = existing.get(name)
        if role is None:
            role = existing[name] = Role(name=name)
            db.add(role)
        role.permissions = [permissions[p] for p in permission_names]
    return existing


def _ensure_security_settings(db: Session) -> None:
    if db.get(SecuritySettings, SECURITY_SETTINGS_ID) is None:
        db.add(
            SecuritySettings(
                id=SECURITY_SETTINGS_ID,
                min_password_length=15,
                date_rule_enabled=False,
                password_validity_days=0,
                idle_timeout_minutes=15,
            )
        )


def _ensure_user(db: Session, login: str, role: Role, password: str, must_change: bool) -> None:
    # Istniejącego konta nie nadpisujemy - ponowny seed nie może cofnąć zmiany hasła.
    if db.scalar(select(User).where(User.login == login)) is not None:
        return
    db.add(
        User(
            login=login,
            password_hash=hash_password(password),
            role=role,
            must_change_password=must_change,
            password_changed_at=datetime.now(UTC),
        )
    )


def _ensure_articles(db: Session) -> None:
    titles = [title for title, _ in ARTICLES]
    existing = set(db.scalars(select(Article.title).where(Article.title.in_(titles))))
    for title, content in ARTICLES:
        if title not in existing:
            db.add(Article(title=title, content=content))


def _read_password(value: SecretStr | None, env_name: str) -> str:
    if value is None or not value.get_secret_value():
        sys.exit(f"Błąd: ustaw {env_name} w pliku .env (wzór: .env.example).")
    password = value.get_secret_value()
    if len(password) < MIN_SEED_PASSWORD_LENGTH:
        sys.exit(f"Błąd: {env_name} musi mieć co najmniej {MIN_SEED_PASSWORD_LENGTH} znaków.")
    return password


def main() -> None:
    # Na Windowsie wyjście do potoku (np. Git Bash) domyślnie używa cp1250 zamiast UTF-8.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")

    settings = get_settings()
    admin_password = _read_password(settings.admin_initial_password, "ADMIN_INITIAL_PASSWORD")
    user_password = _read_password(settings.seed_user_password, "SEED_USER_PASSWORD")

    try:
        with SessionLocal() as db:
            seed(db, admin_password, user_password)
    except OperationalError:
        sys.exit("Błąd: nie można połączyć się z bazą danych (uruchom: docker compose up -d).")
    except ProgrammingError:
        sys.exit("Błąd: brak tabel w bazie danych (uruchom: alembic upgrade head).")
    print("Seed zakończony: role, uprawnienia, ustawienia, użytkownicy i artykuły są w bazie.")


if __name__ == "__main__":
    main()
