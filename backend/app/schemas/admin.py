from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints
from pydantic_core import PydanticCustomError

from app.services.password_policy import MAX_PASSWORD_LENGTH

Login = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]

# Dolne granice i zakres bezczynności muszą zgadzać się z ograniczeniami CHECK w security_settings.
# Minimum powyżej MAX_PASSWORD_LENGTH zablokowałoby każde hasło.
MIN_PASSWORD_LENGTH_FLOOR = 15
MAX_PASSWORD_VALIDITY_DAYS = 3650
MIN_IDLE_TIMEOUT_MINUTES = 1
MAX_IDLE_TIMEOUT_MINUTES = 120


def _between(low: int, high: int, code: str, message: str) -> AfterValidator:
    def check(value: int) -> int:
        if not low <= value <= high:
            raise PydanticCustomError(code, message)
        return value

    return AfterValidator(check)


class UserListItem(BaseModel):
    id: int
    login: str
    role_id: int
    role: str
    is_blocked: bool


class UserCreate(BaseModel):
    login: Login
    role_id: int


class UserUpdate(BaseModel):
    role_id: int


class OneTimePasswordResponse(BaseModel):
    one_time_password: str


class CreatedUserResponse(UserListItem):
    one_time_password: str


class RoleItem(BaseModel):
    id: int
    name: str


class SecuritySettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    min_password_length: int
    date_rule_enabled: bool
    password_validity_days: int
    idle_timeout_minutes: int


class SecuritySettingsUpdate(BaseModel):
    min_password_length: Annotated[
        int,
        _between(
            MIN_PASSWORD_LENGTH_FLOOR,
            MAX_PASSWORD_LENGTH,
            "invalid_min_password_length",
            f"Minimalna długość hasła musi wynosić od {MIN_PASSWORD_LENGTH_FLOOR} "
            f"do {MAX_PASSWORD_LENGTH} znaków.",
        ),
    ]
    date_rule_enabled: bool
    password_validity_days: Annotated[
        int,
        _between(
            0,
            MAX_PASSWORD_VALIDITY_DAYS,
            "invalid_password_validity_days",
            f"Ważność hasła musi wynosić od 0 do {MAX_PASSWORD_VALIDITY_DAYS} dni (0 = wyłączona).",
        ),
    ]
    idle_timeout_minutes: Annotated[
        int,
        _between(
            MIN_IDLE_TIMEOUT_MINUTES,
            MAX_IDLE_TIMEOUT_MINUTES,
            "invalid_idle_timeout",
            f"Czas bezczynności musi być między {MIN_IDLE_TIMEOUT_MINUTES} "
            f"a {MAX_IDLE_TIMEOUT_MINUTES} minutami.",
        ),
    ]
