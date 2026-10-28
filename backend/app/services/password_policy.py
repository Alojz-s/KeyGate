import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ROOT_DIR
from app.models import PasswordHistory, SecuritySettings, User
from app.services.passwords import verify_password

MAX_PASSWORD_LENGTH = 64
PASSWORD_HISTORY_SIZE = 5
BANNED_PASSWORDS_FILE = ROOT_DIR / "backend" / "data" / "banned_passwords.txt"

_MONTHS = {
    name: number
    for number, names in enumerate(
        [
            ("styczeń", "stycznia"),
            ("luty", "lutego"),
            ("marzec", "marca"),
            ("kwiecień", "kwietnia"),
            ("maj", "maja"),
            ("czerwiec", "czerwca"),
            ("lipiec", "lipca"),
            ("sierpień", "sierpnia"),
            ("wrzesień", "września"),
            ("październik", "października"),
            ("listopad", "listopada"),
            ("grudzień", "grudnia"),
        ],
        start=1,
    )
    for name in names
}

_DATE_PATTERNS = [
    re.compile(r"(?P<d>[0-9]{2})\.(?P<m>[0-9]{2})\.(?P<y>[0-9]{4})"),
    re.compile(r"(?P<y>[0-9]{4})-(?P<m>[0-9]{2})-(?P<d>[0-9]{2})"),
    re.compile(r"(?P<d>[0-9]{2})/(?P<m>[0-9]{2})/(?P<y>[0-9]{4})"),
    re.compile(r"(?P<d>[0-9]{2})(?P<m>[0-9]{2})(?P<y>[0-9]{4})"),
    re.compile(r"(?P<y>[0-9]{4})(?P<m>[0-9]{2})(?P<d>[0-9]{2})"),
    re.compile(r"(?P<d>[0-9]{1,2})\s+(?P<m>[^\W\d_]+)\s+(?P<y>[0-9]{4})"),
]
_YEAR = re.compile(r"(?<![0-9])(?:19[5-9][0-9]|20[0-2][0-9]|2030)(?![0-9])")


@dataclass(frozen=True)
class Violation:
    code: str
    message: str


def validate_password(
    plain: str, *, db: Session, settings: SecuritySettings, user_id: int | None = None
) -> list[Violation]:
    violations = []
    if len(plain) < settings.min_password_length:
        violations.append(
            Violation(
                "too_short",
                f"Hasło jest za krótkie (minimalna długość: {settings.min_password_length}).",
            )
        )
    if len(plain) > MAX_PASSWORD_LENGTH:
        violations.append(
            Violation(
                "too_long", f"Hasło jest za długie (maksymalna długość: {MAX_PASSWORD_LENGTH})."
            )
        )
    # Bez rozróżniania wielkości liter: „QWERTY…” jest tak samo popularne jak „qwerty…”.
    if plain.casefold() in _banned_passwords():
        violations.append(
            Violation("common_password", "Hasło jest zbyt popularne (na liście haseł zakazanych).")
        )
    if settings.date_rule_enabled:
        if _is_date(plain):
            violations.append(Violation("is_date", "Hasło nie może być datą."))
        if _YEAR.search(plain):
            violations.append(
                Violation("contains_year", "Hasło nie może zawierać roku z zakresu 1950–2030.")
            )
    if user_id is not None and any(
        verify_password(plain, password_hash)
        for password_hash in _recent_password_hashes(db, user_id)
    ):
        violations.append(
            Violation(
                "reused_password",
                f"Hasło musi różnić się od {PASSWORD_HISTORY_SIZE} ostatnio używanych.",
            )
        )
    return violations


def describe_policy(settings: SecuritySettings) -> list[str]:
    requirements = [
        f"Długość od {settings.min_password_length} do {MAX_PASSWORD_LENGTH} znaków",
        "Nie może być popularnym hasłem z listy haseł zakazanych",
        f"Musi różnić się od {PASSWORD_HISTORY_SIZE} ostatnio używanych haseł",
    ]
    if settings.date_rule_enabled:
        requirements.append("Nie może być datą ani zawierać roku z zakresu 1950–2030")
    return requirements


@lru_cache
def _banned_passwords() -> frozenset[str]:
    lines = (line.strip() for line in BANNED_PASSWORDS_FILE.read_text("utf-8").splitlines())
    return frozenset(line.casefold() for line in lines if line and not line.startswith("#"))


def _is_date(plain: str) -> bool:
    for pattern in _DATE_PATTERNS:
        match = pattern.fullmatch(plain.strip())
        if match is None:
            continue
        month = match["m"]
        month_number = int(month) if month.isdigit() else _MONTHS.get(month.lower(), 0)
        try:
            date(int(match["y"]), month_number, int(match["d"]))
        except ValueError:
            continue
        return True
    return False


def _recent_password_hashes(db: Session, user_id: int) -> list[str]:
    # password_history przechowuje tylko hasła zastąpione; bieżące jest w users.password_hash
    # (NULL po resecie) - razem dają PASSWORD_HISTORY_SIZE ostatnich haseł.
    current = db.scalar(select(User.password_hash).where(User.id == user_id))
    hashes = [current] if current else []
    hashes += db.scalars(
        select(PasswordHistory.password_hash)
        .where(PasswordHistory.user_id == user_id)
        .order_by(PasswordHistory.created_at.desc(), PasswordHistory.id.desc())
        .limit(PASSWORD_HISTORY_SIZE - len(hashes))
    )
    return hashes
