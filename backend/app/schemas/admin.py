from pydantic import BaseModel


class UserListItem(BaseModel):
    id: int
    login: str
    role: str
    is_blocked: bool


class SecuritySettingsResponse(BaseModel):
    min_password_length: int
    date_rule_enabled: bool
    password_validity_days: int
    idle_timeout_minutes: int
