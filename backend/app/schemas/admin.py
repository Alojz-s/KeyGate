from typing import Annotated

from pydantic import BaseModel, StringConstraints

Login = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


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
    min_password_length: int
    date_rule_enabled: bool
    password_validity_days: int
    idle_timeout_minutes: int
