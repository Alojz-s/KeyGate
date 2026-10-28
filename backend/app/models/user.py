from datetime import datetime

from sqlalchemy import ForeignKey, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.role import Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Unikalny także wśród kont usuniętych miękko (deleted_at) - login pozostaje zajęty.
    login: Mapped[str] = mapped_column(String(64), unique=True)
    # NULL, gdy konto ma tylko hasło jednorazowe (nowe konto, reset przez administratora).
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"))
    is_blocked: Mapped[bool] = mapped_column(server_default=false())
    must_change_password: Mapped[bool] = mapped_column(server_default=false())
    password_changed_at: Mapped[datetime | None]
    deleted_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    role: Mapped[Role] = relationship()
