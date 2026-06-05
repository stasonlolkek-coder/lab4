from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    """DTO для регистрации нового пользователя."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "StrongPass123!"
                }
            ]
        }
    )

    email: EmailStr = Field(
        ...,
        description="Email пользователя. Должен быть уникальным.",
        examples=["user@example.com"]
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Пароль. Минимум 8 символов.",
        examples=["StrongPass123!"]
    )


class LoginRequest(BaseModel):
    """DTO для входа в систему."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "StrongPass123!"
                }
            ]
        }
    )

    email: EmailStr = Field(..., description="Email пользователя", examples=["user@example.com"])
    password: str = Field(..., description="Пароль пользователя", examples=["StrongPass123!"])


class UserResponse(BaseModel):
    """Публичный профиль пользователя. Чувствительные поля исключены."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Уникальный идентификатор пользователя (UUID)", examples=["550e8400-e29b-41d4-a716-446655440000"])
    email: EmailStr = Field(..., description="Email пользователя", examples=["user@example.com"])
    created_at: datetime = Field(..., description="Дата регистрации в формате ISO 8601", examples=["2026-06-05T10:00:00Z"])


class ForgotPasswordRequest(BaseModel):
    """DTO для запроса сброса пароля."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"email": "user@example.com"}]
        }
    )

    email: EmailStr = Field(..., description="Email, на который будет отправлена ссылка для сброса", examples=["user@example.com"])


class ResetPasswordRequest(BaseModel):
    """DTO для установки нового пароля по токену."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "token": "abc123...",
                    "new_password": "NewStrongPass456!"
                }
            ]
        }
    )

    token: str = Field(..., description="Токен сброса пароля, полученный по email")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Новый пароль. Минимум 8 символов.",
        examples=["NewStrongPass456!"]
    )


class MessageResponse(BaseModel):
    """Универсальный DTO для текстовых сообщений."""

    message: str = Field(..., description="Текст сообщения", examples=["Operation completed successfully"])