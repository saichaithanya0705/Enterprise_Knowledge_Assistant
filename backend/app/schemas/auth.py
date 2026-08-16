"""Pydantic schemas for authentication and account management."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class _EmailNormalizedModel(BaseModel):
    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return str(value).strip().lower()


class RegisterRequest(_EmailNormalizedModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(_EmailNormalizedModel):
    email: EmailStr
    password: str = Field(..., max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_new_password: str = Field(..., min_length=8, max_length=128)


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)


class PasswordRequirementsRequest(BaseModel):
    password: str = Field(..., max_length=128)


class PasswordRequirementsOut(BaseModel):
    min_length: bool
    max_length: bool
    uppercase: bool
    lowercase: bool
    number: bool
    special: bool
    overall_valid: bool
