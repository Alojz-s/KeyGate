from pydantic import BaseModel


class LoginRequest(BaseModel):
    login: str
    password: str


class MeResponse(BaseModel):
    id: int
    login: str
    role: str
    permissions: list[str]
    must_change_password: bool
    idle_timeout_minutes: int


class PasswordPolicyResponse(BaseModel):
    min_password_length: int
    max_password_length: int
    date_rule_enabled: bool
    requirements: list[str]
