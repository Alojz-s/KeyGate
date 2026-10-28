from datetime import datetime

from sqlalchemy import CheckConstraint, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

SECURITY_SETTINGS_ID = 1


class SecuritySettings(Base):
    __tablename__ = "security_settings"
    __table_args__ = (
        CheckConstraint(f"id = {SECURITY_SETTINGS_ID}", name="singleton"),
        CheckConstraint("min_password_length >= 15", name="min_password_length"),
        CheckConstraint("password_validity_days >= 0", name="password_validity_days"),
        CheckConstraint("idle_timeout_minutes BETWEEN 1 AND 120", name="idle_timeout_minutes"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=False, default=SECURITY_SETTINGS_ID
    )
    min_password_length: Mapped[int] = mapped_column(server_default="15")
    date_rule_enabled: Mapped[bool] = mapped_column(server_default=false())
    # 0 = ważność hasła wyłączona.
    password_validity_days: Mapped[int] = mapped_column(server_default="0")
    idle_timeout_minutes: Mapped[int] = mapped_column(server_default="15")
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
