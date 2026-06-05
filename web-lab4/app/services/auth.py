import secrets
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import (
    hash_password, verify_password, hash_token,
    create_access_token, create_refresh_token,
    decode_refresh_token
)
from app.repositories.user import UserRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.schemas.auth import RegisterRequest, LoginRequest
from app.models.user import User


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    def register(self, data: RegisterRequest) -> User:
        """Регистрация нового пользователя"""
        existing = self.user_repo.get_by_email(data.email)
        if existing:
            raise ValueError("User already exists")

        password_hash, salt = hash_password(data.password)

        user = self.user_repo.create(
            email=data.email,
            password_hash=password_hash,
            salt=salt
        )
        return user

    def login(self, data: LoginRequest) -> tuple[str, str, User]:
        """Вход пользователя. Возвращает (access_token, refresh_token, user)"""
        user = self.user_repo.get_by_email(data.email)
        if not user or not user.password_hash:
            raise ValueError("Invalid credentials")

        if not verify_password(data.password, user.password_hash, user.salt):
            raise ValueError("Invalid credentials")

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        refresh_payload = decode_refresh_token(refresh_token)
        expires_at = datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        self.token_repo.create(user.id, hash_token(refresh_token), expires_at)

        return access_token, refresh_token, user

    def refresh_tokens(self, refresh_token: str) -> tuple[str, str, User]:
        """Обновление пары токенов. Возвращает (new_access, new_refresh, user)"""
        payload = decode_refresh_token(refresh_token)
        if not payload:
            raise ValueError("Invalid refresh token")

        user_id = payload["sub"]
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        token_hash = hash_token(refresh_token)
        stored_token = self.token_repo.get_by_hash(token_hash)
        if not stored_token:
            raise ValueError("Refresh token not found or revoked")

        # Отзываем старый токен
        self.token_repo.revoke(stored_token)

        # Генерируем новую пару
        new_access_token = create_access_token(user.id)
        new_refresh_token = create_refresh_token(user.id)

        new_payload = decode_refresh_token(new_refresh_token)
        expires_at = datetime.fromtimestamp(new_payload["exp"], tz=timezone.utc)
        self.token_repo.create(user.id, hash_token(new_refresh_token), expires_at)

        return new_access_token, new_refresh_token, user

    def logout(self, refresh_token: str):
        """Завершение текущей сессии"""
        token_hash = hash_token(refresh_token)
        stored_token = self.token_repo.get_by_hash(token_hash)
        if stored_token:
            self.token_repo.revoke(stored_token)

    def logout_all(self, user_id: str):
        """Завершение всех сессий пользователя"""
        self.token_repo.revoke_all_for_user(user_id)

    def forgot_password(self, email: str) -> str:
        """Генерирует токен сброса пароля. В production его нужно отправлять на email."""
        user = self.user_repo.get_by_email(email)
        if not user:
            # Не раскрываем существование пользователя
            return "If the email exists, a reset link has been sent"

        raw_token = secrets.token_urlsafe(32)
        user.reset_token_hash = hash_token(raw_token)
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        self.db.commit()

        # В production здесь отправка email. Для тестирования возвращаем токен.
        return raw_token

    def reset_password(self, raw_token: str, new_password: str):
        """Сбрасывает пароль по токену"""
        token_hash = hash_token(raw_token)
        user = self.db.query(User).filter(
            User.reset_token_hash == token_hash,
            User.reset_token_expires > datetime.now(timezone.utc)
        ).first()

        if not user:
            raise ValueError("Invalid or expired token")

        password_hash, salt = hash_password(new_password)
        user.password_hash = password_hash
        user.salt = salt
        user.reset_token_hash = None
        user.reset_token_expires = None
        self.db.commit()