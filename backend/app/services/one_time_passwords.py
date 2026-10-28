import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import OneTimePassword, User
from app.services.passwords import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.services.sessions import delete_all_sessions_for_user

# Bez znaków mylących (0 O o 1 l I i) i bez znaków specjalnych.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
LENGTH = 12
VALIDITY = timedelta(hours=24)


def generate_plaintext() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def issue_one_time_password(db: Session, user_id: int) -> str:
    """Zastępuje poprzednie hasła jednorazowe użytkownika nowym; jawną postać zwraca tylko raz."""
    plain = generate_plaintext()
    db.execute(delete(OneTimePassword).where(OneTimePassword.user_id == user_id))
    db.add(
        OneTimePassword(
            user_id=user_id,
            password_hash=hash_password(plain),
            expires_at=datetime.now(UTC) + VALIDITY,
        )
    )
    return plain


def reset_account_with_one_time_password(db: Session, user: User) -> str:
    user.password_hash = None
    user.must_change_password = True
    delete_all_sessions_for_user(db, user.id)
    return issue_one_time_password(db, user.id)


def try_login_with_one_time_password(db: Session, user: User | None, plain: str) -> bool:
    """Zawsze wykonuje jedną weryfikację Argon2, także bez użytkownika lub aktywnego hasła."""
    now = datetime.now(UTC)
    otp = None
    if user is not None:
        otp = db.scalar(
            select(OneTimePassword)
            .where(
                OneTimePassword.user_id == user.id,
                OneTimePassword.used_at.is_(None),
                OneTimePassword.expires_at > now,
            )
            .order_by(OneTimePassword.id.desc())
            .limit(1)
            # Blokada wiersza: równoległe logowania tym samym hasłem nie wykorzystają go dwa razy.
            .with_for_update()
        )
    otp_ok = verify_password(plain, otp.password_hash if otp else DUMMY_PASSWORD_HASH)
    if not otp_ok or otp is None or user is None:
        return False

    otp.used_at = now
    user.must_change_password = True
    return True


def verify_used_one_time_password(db: Session, user_id: int, plain: str) -> bool:
    """Sprawdza hasło jednorazowe, którym użytkownik się zalogował (jako „obecne hasło”)."""
    otp = db.scalar(
        select(OneTimePassword)
        .where(OneTimePassword.user_id == user_id, OneTimePassword.used_at.is_not(None))
        .order_by(OneTimePassword.used_at.desc())
        .limit(1)
    )
    return otp is not None and verify_password(plain, otp.password_hash)
