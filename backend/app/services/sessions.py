import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import UserSession


def _hash_token(token: str) -> str:
    # Token ma 256 bitów losowości, więc szybki SHA-256 wystarcza (w przeciwieństwie do haseł).
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            user_id=user_id, token_hash=_hash_token(token), last_activity_at=datetime.now(UTC)
        )
    )
    return token


def find_session(db: Session, token: str) -> UserSession | None:
    return db.scalar(select(UserSession).where(UserSession.token_hash == _hash_token(token)))


def delete_session(db: Session, token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.token_hash == _hash_token(token)))


def delete_all_sessions_for_user(db: Session, user_id: int) -> None:
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))


def is_idle_expired(session: UserSession, idle_timeout_minutes: int, now: datetime) -> bool:
    return now - session.last_activity_at > timedelta(minutes=idle_timeout_minutes)
